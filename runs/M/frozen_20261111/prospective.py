#!/usr/bin/env python3
"""Frozen, bounded prospective re-evaluation. All writes confined to this folder."""
import os, sys, json, re, hashlib, datetime, time, subprocess, signal, resource, shutil
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
OLD = ROOT/'audit_20261028/mutation_extension_20261029'
OPS = ['event_accept_argument','event_sign_argument','remove_reveal_event','replicate_signer','disable_signer','disable_accept','unguarded_reveal','wrong_public_key','private_to_public','reveal_wrong_secret']
SEEDS = ['lmots','lms_s2']
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def write(p, s):
    p = Path(p)
    assert p.resolve().is_relative_to(OUT)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s)
def dump(p, x): write(p, json.dumps(x, ensure_ascii=False, indent=2)+'\n')
def inventory():
    paths = set()
    for base in [ROOT/'audit_20261028', ROOT/'cimc']:
        paths.update(p for p in base.rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}
def canonical(s):
    s = re.sub(r'\(\*.*?\*\)', '', s, flags=re.S)
    return re.sub(r'\s+', '', s)

def queries(seed):
    lms = seed == 'lms_s2'
    vars = 'I:bitstring, q:bitstring, a:bitstring' if lms else 'I:bitstring, a:bitstring'
    args = 'I, q, a' if lms else 'I, a'
    tv = 'I q a' if lms else 'I a'
    ta = "I, q, a" if lms else 'I, a'
    probe = 'prf(n0, n0, c_m)' if lms else 'prf(n0, c_m)'
    tprobe = "prf('n0', 'n0', 'm')" if lms else "prf('n0', 'm')"
    return [
      dict(name='acceptreach', group='reach', kind='reach', pv=f'query {vars}; event(Accept({args})) ==> false.', tm=f'Ex {tv} #i. Accept({ta})@i'),
      dict(name='signreach', group='reach', kind='reach', pv=f'query {vars}; event(Sign({args})) ==> false.', tm=f'Ex {tv} #i. Sign({ta})@i'),
      dict(name='revealreach', group='reach', kind='reach', pv='query I:bitstring; event(RevealSeed(I)) ==> false.', tm='Ex I #i. RevealSeed(I)@i'),
      dict(name='seedreach', group='audit', kind='reach', pv='query I:bitstring, s:bitstring; event(AuditSeed(I,s)) && attacker(s) ==> false.', tm='Ex I s #i #j. AuditSeed(I,s)@i & K(s)@j'),
      dict(name='seed_without_reveal', group='audit', kind='safety', pv='query I:bitstring, s:bitstring; event(AuditSeed(I,s)) && attacker(s) ==> event(RevealSeed(I)).', tm='All I s #i #j. AuditSeed(I,s)@i & K(s)@j ==> (Ex #r. RevealSeed(I)@r)'),
      dict(name='reveal_guarded', group='audit', kind='safety', pv='query I:bitstring; event(RevealSeed(I)) ==> event(AuditGuard(I)).', tm='All I #i. RevealSeed(I)@i ==> (Ex #g. AuditGuard(I)@g & #g < #i)'),
      dict(name='prf_public_probe', group='audit', kind='reach', pv=f'query attacker({probe}).', tm=f'Ex #i. K({tprobe})@i')]

def freeze():
    assert not (OUT/'freeze.json').exists(), 'Freeze exists: do not overwrite'
    before=inventory(); dump(OUT/'protected_before.json', before)
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(ROOT/'cimc'))
    from cimc.core import Model
    from cimc.backends import proverif, tamarin
    from cimc.diagnose import TREE_VERSION, tree_hash
    oldmanifest=json.loads((OLD/'manifest_before_runs.json').read_text())
    generated=[]; files={}; qmap={}
    for seed in SEEDS:
        m=Model(ROOT/'cimc/cims'/f'{seed}.toml')
        base=proverif(m,'U',m.bound,'0.1.0',f'{seed}.toml')
        assert base==(OLD/f'{seed}__control/model.pv').read_text()
        assert tamarin(m,'base','0.1.0',f'{seed}.toml')==(OLD/f'{seed}__control/model.spthy').read_text()
        qs=queries(seed)
        oldhead=base.split('let Responder()',1)[0]
        oldqueries=re.findall(r'\(\* (\w+) \*\)\s*(query .*?\.)',oldhead,re.S)
        props=[p for p in m.properties if not p.get('misuse_exception')]
        assert len(oldqueries)==len(props)
        for (name,pv),prop in zip(oldqueries,props):
            assert name==prop['name']
            qs.append(dict(name=name,group='existing',kind='reach' if prop['kind']=='phi3' else 'safety',pv=pv,tm=None))
        qmap[seed]=qs
        for op in ['control']+OPS:
            src=OLD/f'{seed}__{op}/model.pv'; original=src.read_text()
            record=next(x for x in oldmanifest if x['seed']==seed and x['operator']==op)
            assert digest(src)==record['pv_sha256']
            decl,body=original.split('let Responder()',1)
            decl=re.sub(r'\(\* (\w+) \*\)\s*query .*?\.\s*','',decl,flags=re.S)
            body='let Responder()'+body
            # Identical passive measurement transform, after mutation. No input/output is added.
            assert body.count('new sd: bitstring;')==1
            body=body.replace('new sd: bitstring;','new sd: bitstring; event AuditSeed(I,sd);')
            body=body.replace('in(c, =I);','in(c, =I); event AuditGuard(I);')
            decl+='\nevent AuditSeed(bitstring, bitstring).\nevent AuditGuard(bitstring).\n'
            entry=dict(seed=seed,operator=op,source=str(src.relative_to(ROOT)),source_sha256=digest(src),
                       original_canonical_sha256=sha(canonical(original).encode()),groups={})
            for group in ['reach','audit','existing']:
                selected=[q for q in qs if q['group']==group]
                rel=f'pv/{seed}__{op}/{group}.pv'
                text=decl+'\n'.join('(* '+q['name']+' *)\n'+q['pv'] for q in selected)+'\n\n'+body
                write(OUT/rel,text); files[rel]=digest(OUT/rel)
                entry['groups'][group]=dict(file=rel,queries=[q['name'] for q in selected])
            generated.append(entry)
        # Same original TM rules, plus passive audit actions and matching new lemmas.
        tm=(OLD/f'{seed}__control/model.spthy').read_text()
        tm=tm.replace('Start_Signer(~I)', 'Start_Signer(~I), AuditSeed(~I, ~sd)')
        # TM original leak has no In guard. AuditGuard is an abstract matching request:
        # use explicit In(I), already constructible from Init Out(I,...).
        tm=tm.replace('[ !Thr_Signer(I, sd) ]\n  --[ RevealSeed(I) ]->', '[ !Thr_Signer(I, sd), In(I) ]\n  --[ AuditGuard(I) ]->\n  [ PendingReveal(I, sd) ]\n\nrule Audit_Reveal:\n  [ PendingReveal(I, sd) ]\n  --[ RevealSeed(I) ]->')
        assert 'PendingReveal' in tm
        for q in qs:
            if q['tm']:
                lemma=f'lemma prospective_{q["name"]}'+(': exists-trace' if q['kind']=='reach' else ':')+'\n  "'+q['tm']+'"\n\n'
                tm=tm.rsplit('end',1)[0]+lemma+'end\n'
        rel=f'tm/{seed}.spthy'; write(OUT/rel,tm); files[rel]=digest(OUT/rel)
    mutants=[x for x in generated if x['operator']!='control']
    hashes=[x['original_canonical_sha256'] for x in mutants]
    assert len(set(hashes))==20
    tools={}
    for tool in ['proverif','tamarin-prover','maude']:
        p=Path(shutil.which(tool)).resolve();tools[tool]=dict(path=str(p),sha256=digest(p))
    policy=dict(design='prospective new-query re-evaluation of 20 existing PV-only mutants; NOT 100 new mutants',
      target_100_complete=False,shortfall_to_100=80,condition_variants=1,
      count_policy='20 distinct original canonical content hashes; no renamed variants; distinct hashes do not prove statistical independence or semantic inequivalence',
      pv_budget_s=15,tm_budget_s=30,rss_group_stop_mib=650,pv_address_space_mib=800,tm_heap_mib=400,
      pv_group_order=['reach','audit','existing'],tm_subset=[q['name'] for q in queries('lmots')],
      run_order='all 66 PV groups sequentially; then 14 TM per-lemma runs sequentially',
      verdict_policy='PV true/false normalized per kind; cannot/no RESULT/timeout/error are undetermined. TM verified/falsified normalized per quantifier. Only definite opposing control/mutant outcomes kill; no equivalence inferred from survivors.',
      partial_policy='Accept completed individual RESULT before resource stop; missing result undetermined; nonzero non-resource exit invalidates results.',
      tm_policy='Two newly instrumented baseline TM models, seven new matching queries each, 30s per lemma. No mutant TM models. No cached TM reference used as independent rerun. AuditGuard adds explicit matching public-I request and pending step; not byte-identical TM.',
      instrumentation='AuditSeed after new sd, AuditGuard immediately after actual leak in(c,=I). Passive events only in PV. Reveals with removed guard do not receive AuditGuard. Instrumented input-causality detection is separate from uninstrumented observational semantics.',
      prf_probe='Public chosen-input constructor availability, NOT seed secrecy or protocol forgery.',
      accuracy='No gold causal labels and no independent oracle: eight-class accuracy NOT evaluated. Operator provenance is not gold causal diagnosis. No diagnosis tree invocation.',
      expectations={'remove_reveal_event':['revealreach','seed_without_reveal'],'unguarded_reveal':['reveal_guarded'],'private_to_public':['prf_public_probe'],'reveal_wrong_secret':['seedreach']})
    manifest=dict(timestamp=now(),tree_version=TREE_VERSION,tree_sha256=tree_hash(),tools=tools,policy=policy,queries=qmap,models=generated,files=files,runner_sha256=digest(__file__),protected_inventory_sha256=digest(OUT/'protected_before.json'))
    dump(OUT/'freeze.json',manifest)
    write(OUT/'freeze.sha256',digest(OUT/'freeze.json')+'  freeze.json\n')
    print('FROZEN',manifest['timestamp'],len(mutants),'unique',len(set(hashes)),flush=True)

def members(pid):
    total=0
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            stat=(p/'stat').read_text().rsplit(')',1)[1].split()
            if int(stat[2])!=pid: continue
            total+=int(next(x.split()[1] for x in (p/'status').read_text().splitlines() if x.startswith('VmRSS:')))
        except (OSError,ValueError,StopIteration): pass
    return total
def run(args,rel,seconds,pv=False):
    d=OUT/rel; d.mkdir(parents=True,exist_ok=True)
    def limits():
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        if pv: resource.setrlimit(resource.RLIMIT_AS,(800*1024**2,800*1024**2))
    start=time.monotonic(); reason=None; peak=0; samples=[]
    env=dict(os.environ,HOME=str(OUT/'home'),TMPDIR=str(OUT/'tmp'),XDG_CACHE_HOME=str(OUT/'cache'),LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    with (d/'raw.out').open('w') as f:
        p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,cwd=d,env=env,start_new_session=True,preexec_fn=limits)
        while p.poll() is None:
            elapsed=time.monotonic()-start; rss=members(p.pid);peak=max(peak,rss)
            if not samples or elapsed-samples[-1][0]>=1: samples.append([round(elapsed,3),rss])
            if elapsed>seconds or rss>650*1024:
                reason='TIMEOUT' if elapsed>seconds else 'RSS_LIMIT'
                try: os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                break
            time.sleep(.1)
        rc=p.wait()
    result=dict(command=args,started_utc=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=time.monotonic()-start)).isoformat(),elapsed_s=round(time.monotonic()-start,3),rc=rc,stop_reason=reason,time_limit_s=seconds,peak_group_rss_kib=peak,rss_samples=samples,raw_file=str((d/'raw.out').relative_to(OUT)),raw_sha256=digest(d/'raw.out'))
    dump(d/'run.json',result); return result,(d/'raw.out').read_text(errors='replace')

def execute():
    m=json.loads((OUT/'freeze.json').read_text()); assert digest(OUT/'freeze.json')==(OUT/'freeze.sha256').read_text().split()[0]
    assert digest(__file__)==m['runner_sha256']
    for rel,h in m['files'].items(): assert digest(OUT/rel)==h
    assert not (OUT/'execution_started.json').exists(), 'Never overwrite runs'
    for d in ['home','tmp','cache']: (OUT/d).mkdir(exist_ok=True)
    dump(OUT/'execution_started.json',dict(timestamp=now(),freeze_sha256=digest(OUT/'freeze.json')))
    rows=[]
    for item in m['models']:
        for group,g in item['groups'].items():
            r,text=run([m['tools']['proverif']['path'],str(OUT/g['file'])],f'raw/pv/{item["seed"]}__{item["operator"]}/{group}',15,True)
            matches=re.findall(r'^RESULT (.*?) (is true|is false|cannot be proved)\.$',text,re.M)
            rr=[]
            for i,name in enumerate(g['queries']):
                q=next(q for q in m['queries'][item['seed']] if q['name']==name)
                v=matches[i][1] if i<len(matches) else 'NO_RESULT'
                # Ordered matching only if PV reports no more results than input queries.
                valid=(r['rc']==0 or r['stop_reason'] is not None) and len(matches)<=len(g['queries'])
                positive='is false' if q['kind']=='reach' else 'is true'
                status=('YES' if v==positive else 'NO') if valid and v in ['is true','is false'] else 'UNDETERMINED'
                rr.append(dict(query=name,kind=q['kind'],raw_verdict=v,normalized=status,result_text=matches[i][0] if i<len(matches) else None))
            rows.append(dict(tool='PV',seed=item['seed'],operator=item['operator'],group=group,run=r,results=rr))
            dump(OUT/'results.json',rows)
            print('PV',item['seed'],item['operator'],group,r['rc'],[(x['query'],x['normalized']) for x in rr],flush=True)
    for seed in SEEDS:
        for name in m['policy']['tm_subset']:
            q=next(x for x in m['queries'][seed] if x['name']==name)
            args=[m['tools']['tamarin-prover']['path'],'--prove=prospective_'+name,'--derivcheck-timeout=0',str(OUT/f'tm/{seed}.spthy'),'+RTS','-N1','-M400m','-RTS']
            r,text=run(args,f'raw/tm/{seed}/{name}',30)
            found=re.findall(r'^\s*prospective_'+name+r' \((all-traces|exists-trace)\): (verified|falsified)',text,re.M)
            v=found[-1][1] if found else 'NO_RESULT'
            valid=r['rc']==0 or r['stop_reason'] is not None
            status=('YES' if v=='verified' else 'NO') if valid and v in ['verified','falsified'] else 'UNDETERMINED'
            rows.append(dict(tool='TM',seed=seed,operator='instrumented_baseline',run=r,results=[dict(query=name,kind=q['kind'],raw_verdict=v,normalized=status)]))
            dump(OUT/'results.json',rows)
            print('TM',seed,name,r['rc'],status,flush=True)
    dump(OUT/'execution_finished.json',dict(timestamp=now(),runs=len(rows)))

if __name__=='__main__':
    {'freeze':freeze,'run':execute}[sys.argv[1]]()
