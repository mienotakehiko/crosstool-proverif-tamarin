"""Collect allowlisted build identity only, never environment or credentials."""
import pathlib,json,subprocess,tempfile,tarfile,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
IMAGE='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
def main():
 out=pathlib.Path(tempfile.mkdtemp(prefix='metadata_',dir=ROOT))
 commands=[['docker','image','inspect','--format','{{json .Id}} {{json .RepoDigests}} {{json .Created}} {{json .Architecture}} {{json .Os}}',IMAGE],['docker','run','--rm','--pull','never','--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--cpus=1','--memory=256m','--memory-swap=256m','--pids-limit=32','--entrypoint','python3',IMAGE,'-B','-c',"import pathlib,hashlib,json; paths=['/usr/local/bin/tamarin-prover','/usr/local/bin/proverif','/usr/local/bin/maude','/opt/eval/eval.py']; print(json.dumps({'sha256':{p:hashlib.file_digest(open(p,'rb'),'sha256').hexdigest() for p in paths},'commits':{k:(pathlib.Path('/opt/eval')/k).read_text().strip() for k in ['TAMARIN_COMMIT','PROVERIF_COMMIT']}}))"]]
 for i,cmd in enumerate(commands):
  (out/f'{i}.command.json').write_text(json.dumps(cmd))
  with (out/f'{i}.stdout.txt').open('w') as stdout,(out/f'{i}.stderr.txt').open('w') as stderr:
   try:rc=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=60).returncode
   except (OSError,subprocess.TimeoutExpired) as e:stderr.write(repr(e));rc=127
  (out/f'{i}.rc.txt').write_text(str(rc))
 archive=out.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz') as t:t.add(out,arcname=out.name)
 digest=hashlib.sha256(archive.read_bytes()).hexdigest();pathlib.Path(str(archive)+'.sha256.json').write_text(json.dumps({archive.name:digest}))
 print('ARCHIVE='+str(archive));print('HASH='+str(archive)+'.sha256.json')
if __name__=='__main__':main()
