from pathlib import Path
import hashlib,json,difflib,zipfile,subprocess
P=Path(__file__).resolve().parent;A=P/'audit_0_1_2';O=Path('/redacted-home/workspace/cimc')
r=json.loads((A/'results.json').read_text())
assert len(r['records'])==39
assert all(x['rc']==(1 if x['label']=='capture_cli_rejection' else 0) for x in r['records'])
assert all(r[k] for k in ('original_unchanged','old_proof_unchanged','old_outputs_and_stored_evidence_unchanged','seed_models_unchanged_except_version','alpha_positive_control_text_renaming_exact'))
for f,h in json.loads((A/'original_before.json').read_text()).items():
    assert hashlib.sha256((O/f).read_bytes()).hexdigest()==h,f
assert len(json.loads((A/'pv_expected_comparison.json').read_text()))==21
assert 'Ran 22 tests' in (A/'fulltests.log').read_text()
diff=[]
for p in sorted((P/'cimc').glob('*.py'))+sorted((P/'tests').glob('*.py'))+[P/'README.md']:
    rel=p.relative_to(P);old=(O/rel).read_text() if (O/rel).exists() else ''
    if old!=p.read_text():diff+=difflib.unified_diff(old.splitlines(True),p.read_text().splitlines(True),fromfile='a/'+str(rel),tofile='b/'+str(rel))
(A/'fix.diff').write_text(''.join(diff))
versions={}
for args in (['proverif','-help'],['tamarin-prover','--version']):
    v=subprocess.run(args,cwd=P,capture_output=True,text=True)
    versions[args[0]]=v.stdout+v.stderr
(A/'tool_versions.json').write_text(json.dumps(versions,indent=2))
files=sorted(p for p in P.rglob('*') if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts and p.name not in ('cimc_fixed_0.1.2.zip','SHA256SUMS'))
manifest={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
(A/'fixed_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
files=sorted(set(files)|{A/'fixed_manifest.json'})
zpath=P/'cimc_fixed_0.1.2.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
    for f in files:z.write(f,Path('cimc_fixed')/f.relative_to(P))
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
(P/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(P)) for f in [zpath,A/'fix.diff',A/'results.json',P/'manuscript_correction_en.md'])+'\n')
print(json.dumps(dict(archive_files=len(files),archive_bytes=zpath.stat().st_size,original_rechecked=True,commands=39,guards=9,AL=37,unittest=22,expected_PV=21,mode='conservative rejection, not constructor capture-avoidance'),indent=2))
