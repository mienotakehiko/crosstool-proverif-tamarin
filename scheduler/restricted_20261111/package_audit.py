"""Validate and package only the independent proof workspace."""
from pathlib import Path
import csv, json, hashlib, zipfile, subprocess, platform
P=Path(__file__).resolve().parent
r=json.loads((P/'results.json').read_text())
assert r['tests_run']==21 and r['failures']==r['errors']==0
assert r['upstream_unchanged']
for s,h in json.loads((P/'source_manifest.json').read_text()).items():
    assert hashlib.sha256(Path(s).read_bytes()).hexdigest()==h,s
rows=list(csv.DictReader((P/'mapping.csv').open()))
assert len(rows)==22 and len({x['id'] for x in rows})==22
assert all(all(v for v in row.values()) for row in rows)
expected={'restricted_lin.pv':0,'restricted_U.pv':0,'unbound_guard.pv':0,
          'undefined_guard.pv':2,'scalar_pattern.pv':2,'capture.pv':0,
          'overlap.pv':0,'restricted_base.spthy':0,'capture.spthy':0,'overlap.spthy':0}
for c in r['commands']:
    f=next(Path(x).name for x in c['command'] if x.endswith(('.pv','.spthy')))
    assert c['rc']==expected[f],(f,c)
assert 'not event(EvA(I_1)) is true' in (P/'capture.pv.log').read_text()
assert 'capture (exists-trace): verified' in (P/'capture.spthy.log').read_text()
assert 'overlap (exists-trace): falsified' in (P/'overlap.spthy.log').read_text()
log=(P/'check_latex.log').read_text()
assert 'Output written on' in log and 'Overfull' not in log
assert (P/'check_latex.pdf').stat().st_size>1000
versions={'python':platform.python_version()}
for cmd in (['proverif','-help'],['tamarin-prover','--version']):
    x=subprocess.run(cmd,cwd=P,capture_output=True,text=True)
    versions[cmd[0]]=x.stdout+x.stderr
(P/'versions.json').write_text(json.dumps(versions,indent=2)+'\n')
audit={'source_hashes_rechecked':True,'mapping_rows':22,'python_tests':21,
       'native_commands':len(r['commands']),'expected_model_errors':2,
       'latex_compile':'success, two pages, no overfull boxes',
       'not_claimed':['native language semantic adequacy','complete PV/TM trace equivalence','general property transfer'],
       'write_scope':'this proof directory only; no upstream edit'}
(P/'final_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
archive=P/'restricted_correspondence_proof_20261111.zip'
excluded={archive.name,'check_latex.pdf','check_latex.aux','check_latex.log','check_latex.out','SHA256SUMS'}
paths=sorted(f for f in P.rglob('*') if f.is_file() and f.name not in excluded)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for f in paths:z.write(f,f.relative_to(P))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(paths)
(P/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name for f in [archive,P/'proof_notes_en.md',P/'appendix_restricted_scheduler.tex',P/'mapping.csv',P/'README_ja.md',P/'results.json'])+'\n')
print(json.dumps(audit,indent=2));print('Archive files:',len(paths),'bytes:',archive.stat().st_size)
