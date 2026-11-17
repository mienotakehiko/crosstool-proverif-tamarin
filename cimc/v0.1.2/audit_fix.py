"""Sequential 0.1.2 audit; writes only this copy, never old evidence.
Run with python -B audit_fix.py. Child processes have explicit memory limits.
"""
from pathlib import Path
import sys, os, subprocess, hashlib, json, re, difflib, resource, copy, zipfile, platform
P=Path(__file__).resolve().parent
ORIG=Path('/redacted-home/workspace/cimc')
PROOF=Path('/redacted-home/workspace/revision_20261111/proof')
A=P/'audit_0_1_2';A.mkdir(exist_ok=True)
(A/'tmp').mkdir(exist_ok=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(A/'tmp'),PYTHONPATH=str(P))
sys.path.insert(0,str(P))
from cimc.core import Model, CimError
from cimc.backends import proverif, tamarin
from cimc.checks import run

def hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
before=hashes(ORIG);oldproof=hashes(PROOF)
(A/'original_before.json').write_text(json.dumps(before,indent=2))
(A/'old_proof_before.json').write_text(json.dumps(oldproof,indent=2))
assert all((P/f).read_bytes()==(ORIG/f).read_bytes() for f in before if f.startswith(('out/','tests/data/')))
records=[]
def child_limit():resource.setrlimit(resource.RLIMIT_AS,(750*1024**2,750*1024**2))
def cmd(label,args,seconds=60):
    try:
        r=subprocess.run(args,cwd=P,env=env,capture_output=True,text=True,timeout=seconds,preexec_fn=child_limit)
        text=r.stdout+r.stderr;rc=r.returncode
    except subprocess.TimeoutExpired as e:
        text=(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else (e.stdout or '')
        text+='\nTIMEOUT';rc='timeout'
    (A/f'{label}.log').write_text(text)
    row=dict(label=label,command=args,rc=rc,log=f'{label}.log',results=[l for l in text.splitlines() if l.startswith('RESULT') or re.search(r'\((?:all-traces|exists-trace)\):',l) or 'tests passed' in l or 'SAME' in l or 'Ran ' in l or 'FAIL' in l or 'ERROR' in l])
    records.append(row);print(label,rc,row['results'],flush=True)
    return rc,text

cmd('existing_9_guards',[sys.executable,'-B','tests/test_correspondence_guards.py'])
cmd('al_37',[sys.executable,'-B','tests/test_al.py'])
cmd('fulltests',[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test*.py'])
cmd('two_seed_stored_al',[sys.executable,'-B','tests/regress_al.py'])
gen=A/'generated';gen.mkdir(exist_ok=True)
comparisons=[]
for seed in ('lmots','lms_s2'):
    d=gen/seed
    cmd('generate_'+seed,[sys.executable,'-B','-m','cimc',str(P/'cims'/f'{seed}.toml'),str(d)])
    # Compare against current 0.1.1 source emission, not historical 0.1.0 out/.
    script='''import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from cimc.core import Model;from cimc.backends import proverif,tamarin;m=Model(Path(sys.argv[1])/'cims'/sys.argv[2]);print(json.dumps({**{f'{m.name}_PV_{e if e in ("lin","rep") else e+str(m.bound)}.pv':proverif(m,e,m.bound,'0.1.1',sys.argv[2]) for e in ('U','Urb','lin','rep')},**{f'{m.name}_T_{v}.spthy':tamarin(m,v,'0.1.1',sys.argv[2]) for v in ('base','cl1','rb1','omega')}}))'''
    rc,raw=cmd('old_emission_'+seed,[sys.executable,'-B','-c',script,str(ORIG),seed+'.toml'])
    expected=json.loads(raw)
    for fn,old in expected.items():
        new=(d/fn).read_text()
        ok=new.replace('cimc 0.1.2','cimc 0.1.1')==old
        comparisons.append(dict(seed=seed,file=fn,unchanged_except_version=ok));assert ok,fn
    for f in sorted(d.glob('*.pv')):cmd('pv_'+f.stem,['proverif',str(f)],30)
    # Parse/wellformedness on all four TM variants, without costly proofs.
    for f in sorted(d.glob('*.spthy')):cmd('tm_parse_'+f.stem,['tamarin-prover',str(f),'+RTS','-N1','-M450m','-RTS'],40)
    # Select only the normal execution lemma; not a full security rerun.
    modelname=Model(P/'cims'/f'{seed}.toml').name
    lemma='exec_accept' if seed=='lmots' else 'exec'
    cmd('tm_execution_'+seed,['tamarin-prover','--prove='+lemma,'--derivcheck-timeout=0',str(d/f'{modelname}_T_base.spthy'),'+RTS','-N1','-M450m','-RTS'],60)

# Original capture fixture reconstructed through the original source via
# frozen script logic, then offered to the fixed direct APIs and CLI.
fixture=(PROOF/'restricted.toml').read_text()
capture=fixture.replace('publish = "tup(I, \'a\')"','publish = "tup(I, seal(1))"')
capture=capture[:capture.index('[[thread.step]]\nname="Second"')] + '''[[property]]
name="capture"
kind="phi3"
events=["EvA(I)"]
'''
capture=capture.replace('input="tup(\'a\', I)"','input="tup(\'a\', seal(x))"')
bad=A/'capture_unsupported.toml';bad.write_text(capture)
z=Model(bad);rejections=[]
for name,fn,args in [('PV_'+e,proverif,(e,2)) for e in ('U','Urb','lin','rep')]+[('TM_'+v,tamarin,(v,)) for v in ('base','cl1','rb1','omega')]:
    try:fn(z,*args,'0.1.2',bad.name)
    except CimError as e:rejections.append(dict(backend=name,diagnostic=str(e)))
    else:raise AssertionError('unsafe model emitted')
assert len(rejections)==8
rejectdir=A/'must_not_exist'
assert not rejectdir.exists()
rc,_=cmd('capture_cli_rejection',[sys.executable,'-B','-m','cimc',str(bad),str(rejectdir)])
assert rc==1 and not rejectdir.exists()
# Re-run the old pair unchanged to establish the old bug remains evidence.
for f in ('capture.pv','capture.spthy'):
    shutil_source=PROOF/f
    (A/('old_'+f)).write_bytes(shutil_source.read_bytes())
    args=['proverif',str(A/('old_'+f))] if f.endswith('.pv') else ['tamarin-prover','--prove','--derivcheck-timeout=0',str(A/('old_'+f)),'+RTS','-N1','-M450m','-RTS']
    cmd('old_capture_'+f.split('.')[-1],args)
# No bogus "fixed verdict" for rejected input. A supported positive control
# binds Payload as a simple tuple leaf; no same-pattern equality reference.
safe=fixture.replace('input="tup(\'a\', I)"','input="tup(Payload, I)"').replace('publish = "tup(I, \'a\')"','publish = "tup(I, seal(I))"')
safe=safe.replace('outputs=["seal(I)",','outputs=["Payload", "seal(I)",')
safe2=safe.replace('Payload','Renamed')
for name,src in [('supported',safe),('alpha_renamed',safe2)]:
    f=A/(name+'.toml');f.write_text(src);model=Model(f)
    assert not any(s=='FAIL' for _,s,_ in run(model))
    for e in ('U','Urb','lin','rep'):
        p=A/f'{name}_{e}.pv';p.write_text(proverif(model,e,2,'0.1.2',f.name));cmd(name+'_'+e,['proverif',str(p)])
    p=A/(name+'.spthy');p.write_text(tamarin(model,'base','0.1.2',f.name))
    cmd(name+'_tm',['tamarin-prover','--prove','--derivcheck-timeout=0',str(p),'+RTS','-N1','-M450m','-RTS'])
assert (A/'supported_lin.pv').read_text().replace('supported.toml','alpha_renamed.toml').replace('v_Payload','v_Renamed')==(A/'alpha_renamed_lin.pv').read_text()
assert (A/'supported.spthy').read_text().replace('supported.toml','alpha_renamed.toml').replace('Payload','Renamed')==(A/'alpha_renamed.spthy').read_text()
# Exact comparison with all stored expected PV verdicts, no missing queries.
pv_got={}
for seed in ('lmots','lms_s2'):
    for f in sorted((gen/seed).glob('*.pv')):
        names=re.findall(r'^\(\* (\w+) \*\)\nquery',f.read_text(),re.M)
        verdicts=re.findall(r'^RESULT (.*) (is true|is false|cannot be proved)\.$',(A/('pv_'+f.stem+'.log')).read_text(),re.M)
        assert len(names)==len(verdicts),(f,names,verdicts)
        for name,(_,v) in zip(names,verdicts):pv_got[f.stem,name]={'is true':'true','is false':'false','cannot be proved':'cannot'}[v]
expected_rows=[]
for seed in ('lmots','lms_s2'):
    for line in (P/'tests'/f'expected_{seed}.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        model,query,expect,_=line.split('\t')
        got=pv_got.get((model,query),'MISSING')
        expected_rows.append(dict(model=model,query=query,expected=expect,got=got,ok=expect==got))
assert len(expected_rows)==21 and all(x['ok'] for x in expected_rows)
(A/'pv_expected_comparison.json').write_text(json.dumps(expected_rows,indent=2))
for row in records:
    expected_rc=1 if row['label']=='capture_cli_rejection' else 0
    assert row['rc']==expected_rc,row
for prefix in ('supported','alpha_renamed'):
    for e in ('U','Urb','lin','rep'):
        assert ' is false.' in (A/f'{prefix}_{e}.log').read_text()
    assert 'exec (exists-trace): verified' in (A/f'{prefix}_tm.log').read_text()
after=hashes(ORIG);assert before==after
assert oldproof==hashes(PROOF)
assert all((P/f).read_bytes()==(ORIG/f).read_bytes() for f in before if f.startswith(('out/','tests/data/')))
(A/'original_after.json').write_text(json.dumps(after,indent=2))
(A/'seed_comparison.json').write_text(json.dumps(comparisons,indent=2))
(A/'rejections.json').write_text(json.dumps(rejections,indent=2))
(A/'results.json').write_text(json.dumps(dict(records=records,original_unchanged=True,old_proof_unchanged=True,old_outputs_and_stored_evidence_unchanged=True,seed_models_unchanged_except_version=all(r['unchanged_except_version'] for r in comparisons),alpha_positive_control_text_renaming_exact=True,python=platform.python_version()),indent=2)+'\n')
changes=[]
for p in sorted((P/'cimc').glob('*.py'))+sorted((P/'tests').glob('*.py')):
    rel=p.relative_to(P);o=ORIG/rel;old=o.read_text() if o.exists() else ''
    if old!=p.read_text():changes+=difflib.unified_diff(old.splitlines(True),p.read_text().splitlines(True),fromfile='a/'+str(rel),tofile='b/'+str(rel))
(A/'fix.diff').write_text(''.join(changes))
print('AUDIT FINISHED',len(records),'commands',flush=True)
