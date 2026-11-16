"""Compare saved original PV and explicit state guards; not an exporter fix."""
import hashlib,json,os,re,subprocess,sys,tarfile,tempfile
from pathlib import Path
from common import run,pv_results,pv_verdict,dump
ROOT=Path(__file__).resolve().parent
IMAGE='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
TOOLS={'/usr/local/bin/proverif':'f6b5e9606e639350085167f150e6bca7adfcdac0b34614b890e72f7f9e0c1c28','/usr/local/bin/tamarin-prover':'b942e7f58d15023bc1a7210c0bedbc0d36db921f0a54888827bca7989730f70a','/usr/local/bin/maude':'13b89491dcfeef5a0befba10db503de1937fc46279320242423fc38f1fd830a0','/opt/eval/eval.py':'29ec8cca3a7ef913d5ce8ae7e9d73cc965f9a3a6971ad8d440cee6809860eb40'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inside():
 out=Path('/work');rows=[]
 checks={k:{'expected':v,'actual':sha(k)} for k,v in TOOLS.items()};dump(out/'tool_checks.json',checks)
 assert all(v['actual']==v['expected'] for v in checks.values())
 for item in json.loads((ROOT/'manifest.json').read_text()):
  d=out/item['case']/item['lemma'];d.mkdir(parents=True,exist_ok=True)
  result={'case':item['case'],'lemma':item['lemma'],'saved_native':item['native'],'saved_original_pv':item['original_pv']}
  for kind in ['original','guarded']:
   src=ROOT/'models'/item['case']/item['lemma']/(kind+'.pv')
   assert sha(src)==item[kind+'_hash']
   meta=run(d,kind,['/usr/local/bin/proverif',str(src)],60)
   raw=pv_results((d/(kind+'.stdout.txt')).read_text(),meta['rc'])
   result[kind]={'rc':meta['rc'],'timeout':meta['timeout'],'raw':raw,'verdict':pv_verdict(raw[0],item['lemma']) if len(raw)==1 else 'unknown'}
  result['baseline_reproduced']=result['original']['verdict']==item['original_pv']
  result['guarded_agrees_with_saved_native']=result['guarded']['verdict']==item['native']
  rows.append(result)
 dump(out/'summary.json',rows)
 dump(out/'inside_status.json',{'complete':True,'baseline_reproduced':sum(x['baseline_reproduced'] for x in rows),'guarded_agrees':sum(x['guarded_agrees_with_saved_native'] for x in rows)})
def main():
 base=ROOT/'runs';base.mkdir(exist_ok=True);out=Path(tempfile.mkdtemp(prefix='guard_compare_',dir=base));name=out.name.replace('_','-')
 snapshot=out/'inputs';snapshot.mkdir()
 import shutil
 for f in ['guard_compare.py','common.py','manifest.json']:shutil.copy2(ROOT/f,snapshot/f)
 shutil.copytree(ROOT/'models',snapshot/'models')
 cmd=['docker','run','--rm','--pull','never','--network','none','--cpus=1','--memory=2g','--memory-swap=2g','--pids-limit=128','--cap-drop=ALL','--security-opt=no-new-privileges','--read-only','--user',str(os.getuid())+':'+str(os.getgid()),'--name',name,'--env','PYTHONDONTWRITEBYTECODE=1','--env','HOME=/work','--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--volume',str(snapshot)+':/kit:ro','--volume',str(out)+':/work','--workdir','/work',IMAGE,'python3','-B','/kit/guard_compare.py','--inside']
 try:
  meta=run(out,'container',cmd,2100)
  dump(out/'launcher_status.json',{'complete':(out/'inside_status.json').exists(),'container_rc':meta['rc'],'image':IMAGE})
 finally:
  run(out,'cleanup',['docker','rm','-f',name],15)
  dump(out/'evidence_hashes.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})
  archive=out.with_suffix('.tar.gz')
  with tarfile.open(archive,'w:gz') as t:t.add(out,arcname=out.name)
  hashfile=Path(str(archive)+'.sha256.json');dump(hashfile,{archive.name:sha(archive)})
  print('ARCHIVE='+str(archive));print('HASH='+str(hashfile))
if __name__=='__main__':
 if '--inside' in sys.argv:inside()
 else:main()
