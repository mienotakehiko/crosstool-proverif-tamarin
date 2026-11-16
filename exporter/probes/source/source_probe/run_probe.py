"""Run only a new bounded original-exporter suite; no build, pull, or network."""
import json,os,pathlib,subprocess,sys,tempfile,tarfile,hashlib,shutil
from common import run,dump,sha,tm_verdict,pv_results,pv_reach
ROOT=pathlib.Path(__file__).resolve().parent
IMAGE='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
TOOLS={'/usr/local/bin/tamarin-prover':'b942e7f58d15023bc1a7210c0bedbc0d36db921f0a54888827bca7989730f70a','/usr/local/bin/proverif':'f6b5e9606e639350085167f150e6bca7adfcdac0b34614b890e72f7f9e0c1c28','/usr/local/bin/maude':'13b89491dcfeef5a0befba10db503de1937fc46279320242423fc38f1fd830a0','/opt/eval/eval.py':'29ec8cca3a7ef913d5ce8ae7e9d73cc965f9a3a6971ad8d440cee6809860eb40'}
def inside():
 out=pathlib.Path('/work');checks={p:{'actual':sha(p),'expected':h} for p,h in TOOLS.items()};dump(out/'tools.json',checks)
 assert all(x['actual']==x['expected'] for x in checks.values()),'tool_hash_mismatch'
 commits={k:(pathlib.Path('/opt/eval')/k).read_text().strip() for k in ['TAMARIN_COMMIT','PROVERIF_COMMIT']};dump(out/'commits.json',commits)
 assert commits=={'TAMARIN_COMMIT':'c293106913ccf7bb41f49b0dc555a8074e8ea88c','PROVERIF_COMMIT':'1d4cd9458d9ccf648e149ec2ea5147b2c87b67df'}
 rows=[]
 for case in json.loads((ROOT/'cases.json').read_text()):
  src=ROOT/'models'/(case['id']+'.spthy');assert sha(src)==case['source_sha256']
  for lemma in ['good_reachable','bad_reachable']:
   d=out/case['id']/lemma;d.mkdir(parents=True);pv=d/'translated.pv';base=['tamarin-prover','+RTS','-N1','-M768m','-RTS','-d=0']
   nm=run(d,'native',base+['--prove='+lemma,str(src)],60)
   em=run(d,'export',base+['-m=proverif','--lemma='+lemma,'-o='+str(pv),str(src)],60)
   row={'case':case['id'],'lemma':lemma,'expected_native':case[lemma],'native':tm_verdict((d/'native.stdout.txt').read_text(),lemma,nm['rc']),'native_meta':nm,'export_meta':em,'translated':'not_run'}
   if em['rc']==0 and pv.exists() and pv.stat().st_size:
    body=pv.read_text();row['translation_markers']=[m for m in ['Restriction translation failed','Axiom translation failed','Restriction has negated event','Axiom has negated event','WARNING','omitted'] if m in body]
    pm=run(d,'pv',['proverif',str(pv)],60);raw=pv_results((d/'pv.stdout.txt').read_text(),pm['rc']);row.update(pv_meta=pm,pv_raw=raw,translated=pv_reach(raw[0]) if len(raw)==1 else 'unknown')
   row['comparison']='MATCH' if row['native']==row['translated'] and row['native'] in ['reachable','unreachable'] else 'DIFFERENT' if {row['native'],row['translated']}=={'reachable','unreachable'} else 'REVIEW'
   rows.append(row);dump(out/'summary.json',rows)
 dump(out/'inside_complete.json',{'rows':len(rows),'exporter':'original; candidate not applied'})
def main():
 frozen=json.loads((ROOT/'KIT_HASHES.json').read_text())
 assert all(sha(ROOT/p)==h for p,h in frozen.items()),'kit_hash_mismatch'
 out=pathlib.Path(tempfile.mkdtemp(prefix='source_probe_',dir=ROOT));snapshot=out/'inputs';snapshot.mkdir()
 for name in ['run_probe.py','common.py','cases.json']:shutil.copy2(ROOT/name,snapshot/name)
 shutil.copytree(ROOT/'models',snapshot/'models');name=out.name.replace('_','-')
 run(out,'image_id',['docker','image','inspect','--format','{{.Id}}',IMAGE],15)
 cmd=['docker','run','--rm','--pull','never','--network','none','--cpus=1','--memory=2g','--memory-swap=2g','--pids-limit=128','--cap-drop=ALL','--security-opt=no-new-privileges','--read-only','--user',str(os.getuid())+':'+str(os.getgid()),'--name',name,'--env','PYTHONDONTWRITEBYTECODE=1','--env','HOME=/work','--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--volume',str(snapshot)+':/kit:ro','--volume',str(out)+':/work','--workdir','/work',IMAGE,'python3','-B','/kit/run_probe.py','--inside']
 try:run(out,'container',cmd,3000)
 finally:
  run(out,'cleanup',['docker','rm','-f',name],15)
  dump(out/'evidence_hashes.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})
  archive=out.with_suffix('.tar.gz')
  with tarfile.open(archive,'w:gz') as t:t.add(out,arcname=out.name)
  dump(str(archive)+'.sha256.json',{archive.name:sha(archive)})
  print('ARCHIVE='+str(archive));print('HASH='+str(archive)+'.sha256.json');print('COMPLETE='+str((out/'inside_complete.json').exists()))
if __name__=='__main__':inside() if '--inside' in sys.argv else main()
