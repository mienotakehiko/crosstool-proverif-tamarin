#!/usr/bin/env python3
"""Recheck the five YubiKey tasks with the archived Morio launcher on WSL."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess as sp
import sys
import tarfile
import tempfile

KIT = Path(__file__).resolve().parent
REF = json.loads((KIT/'references.json').read_text())
TASKS = {int(k): v for k, v in REF['tasks'].items()}
HOME_DIR = Path.home()
OLD = HOME_DIR/'cryptography-experiments/rev013-evidence-8UgiWm/morio-paired-local300'
BIN = HOME_DIR/'rev015-sec8.vJXRNNGe/b3-src/build/candidate/tamarin-prover'
MODEL = '/opt/eval/'+TASKS[433]['B2']['input_file']


def require(yes, msg):
    if not yes:
        raise ValueError(msg)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')
    tmp.replace(path)


def runout(cmd, **kwargs):
    return sp.check_output(cmd, text=True, **kwargs).strip()


def settings(a):
    if a.artifact:
        root = a.artifact.resolve()/'eval'
    else:
        task = a.state.resolve()/'full-b2/task-433'
        done = json.loads((task/'done.json').read_text())
        root = task/done['attempt']/'work/eval'
    driver = root/'scripts/run-eval-local.sh'
    for file, field in [(driver,'driver'), (root/'eval.csv','csv'), (a.binary,'b3')]:
        require(file.is_file(), 'Missing file '+str(file))
        require(digest(file)==REF[field], 'SHA-256 differs from the earlier record '+str(file))
    require(os.access(a.binary,os.X_OK), 'The B3 binary is not executable '+str(a.binary))
    for file in (KIT/'proxy/docker', KIT/'diag/proverif'):
        require(os.access(file, os.X_OK), 'chmod +x is required '+str(file))
    docker = shutil.which('docker')
    require(docker, 'docker not found in WSL')
    docker = str(Path(docker).absolute())
    image = REF['image']
    info = json.loads(runout([docker, 'image','inspect',image]))[0]
    require((info['Id'],info['Os'],info['Architecture'])==(image,'linux','amd64'),'Docker image ID or architecture differs')
    env_path = next(v[5:] for v in info['Config']['Env'] if v.startswith('PATH='))
    binary = str(a.binary.resolve())
    require(',' not in binary and ',' not in str(a.out.resolve()) and ',' not in str(KIT),'Remove commas from the working paths')
    mounted = ['--mount','type=bind,src='+binary+',dst=/opt/rev013/exporter,readonly']
    files = dict(REF['original_image_files'])
    files[MODEL] = REF['model_hash']
    evidence = {}
    for label, mounts in [('b2',[]),('b3',mounted)]:
        want = dict(files)
        if label == 'b3':
            want['/opt/rev013/exporter'] = REF['b3']
        cmd = [docker,'run','--rm','--network','none',*mounts,'--entrypoint','sha256sum',image,*want]
        actual = {n.strip(): h for h,n in (line.split(None,1) for line in runout(cmd).splitlines())}
        require(actual==want, 'Hash mismatch inside the container '+label)
        evidence[label] = actual
    source = driver.read_text()
    # Same output-option discovery as the previous rev013 run. Default paths are
    # also isolated by giving each launcher invocation its own working directory.
    opt = re.search(r'(?m)^[ \t]*([^#\n()]*--[\w-]+[^#\n()]*)\)[ \t]*(?:\n[ \t]*)?(?:OUT(?:PUT)?_?DIR|RESULTS?_?DIR)\s*=\s*["\']?\$(?:2|\{2\})', source)
    output_option = re.search(r'--[\w-]+',opt[1]).group() if opt else None
    provenance = dict(image=image, driver=REF['driver'], csv=REF['csv'], timeout=300,
                      memory_MB=8192, files=evidence, driver_inputs=str(root),
                      binary=binary, driver_output_option=output_option,
                      kit={n:digest(KIT/n) for n in ('run.py','diag/proverif','proxy/docker','references.json')})
    return root, docker, env_path, provenance


def category(row):
    flags = [('translate_error','export_error'),('proverif_timeout','timeout'),('proverif_oom','oom')]
    for field,_ in flags:
        require(type(row[field]) is bool,'Invalid flag '+field)
    faults = [label for k,label in flags if row[k]]
    err = row['proverif_error']
    if err:
        faults.append('syntax_error' if re.search(r'\bsyntax error\b',str(err),re.I) else 'pv_error')
    v = row['proverif_result']
    if type(v) is bool:
        require(not faults,'A Boolean result and an error occur together')
        return str(v).lower()
    return '+'.join(faults) or ('unresolved' if v is None else 'reported:'+str(v))


def measured(work, i):
    expected = TASKS[i]['B2']
    rows = []
    for p in work.rglob('*'):
        if not p.is_file() or p.suffix not in ('.json','.jsonl') or any(sub in p.parents for sub in (work/'eval/scripts',work/'eval/docker')):
            continue
        raw = p.read_text().strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = [json.loads(line) for line in raw.splitlines() if line.strip()]
        for item in data if isinstance(data,list) else [data]:
            if not isinstance(item,dict):
                continue
            row = item.get('result') if isinstance(item.get('result'),dict) and 'proverif_result' not in item else item
            if 'proverif_result' not in row:
                continue
            model = str(row.get('input_file', row.get('file',row.get('model',''))))
            if model.startswith('/opt/eval/'):
                model=model[len('/opt/eval/'):]
            if model.startswith('./'):
                model=model[2:]
            require(model==expected['input_file'] and row.get('lemma')==expected['lemma']
                    and int(row.get('index',i))==i and row.get('verifiers_run',['proverif'])==['proverif']
                    and row.get('trace_quantifier',expected['trace_quantifier'])==expected['trace_quantifier'],
                    'Unexpected key of a measured row '+str(p))
            category(row)
            rows.append((row,p))
    require(len(rows)==1, 'The evaluator wrote '+str(len(rows))+' new results. Check the output under work and console.log')
    return rows[0]


def one(a, ctx, i, phase):
    root,docker,image_path,prov = ctx
    folder = a.out/str(i)/phase
    folder.mkdir(parents=True,exist_ok=True)
    done = folder/'done.json'
    if done.exists():
        return json.loads(done.read_text())
    trial = Path(tempfile.mkdtemp(dir=folder,prefix='trial-'))
    audit = trial/'audit'
    audit.mkdir()
    audit.chmod(0o1777)
    work = trial/'work'
    shutil.copytree(root/'scripts',work/'eval/scripts',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(root/'eval.csv',work/'eval/eval.csv')
    if (root/'docker').is_dir():
        (work/'eval/docker').symlink_to((root/'docker').resolve(),target_is_directory=True)
    opt = prov['driver_output_option']
    cmd = ['bash','eval/scripts/run-eval-local.sh','eval/eval.csv','--start',str(i),'--end',str(i),
           '--proverif','--timeout','300','--memory','8192','--image',REF['driver_image']]
    if opt:
        cmd += [opt,str(work/'new-results')]
    write(trial/'command.json',cmd)
    env = dict(os.environ, PATH=str(KIT/'proxy')+os.pathsep+os.environ['PATH'], Y5_DOCKER=docker,
               Y5_REQUESTED=REF['driver_image'], Y5_IMAGE=REF['image'],Y5_AUDIT=str(audit),
               Y5_BIN=prov['binary'], Y5_DIAG=str(KIT/'diag'), Y5_PHASE=phase,Y5_IMAGE_PATH=image_path)
    print(f'{phase} {i} {TASKS[i]["B2"]["lemma"]}  {trial}',flush=True)
    with (trial/'console.log').open('wb') as out:
        rc = sp.run(cmd,cwd=work,env=env,stdout=out,stderr=sp.STDOUT).returncode
    (trial/'driver.rc').write_text(str(rc)+'\n')
    # The original routing script uses mktemp (0600) under the container UID.
    # Only the read mode of this new trial's diagnostic files is adjusted.
    unreadable = [p.name for p in audit.iterdir() if not p.is_symlink() and p.is_file() and not os.access(p,os.R_OK)]
    if unreadable:
        sp.run([docker,'run','--rm','--network','none','--user','0:0','--mount',
                'type=bind,src='+str(audit)+',dst=/y5audit','--entrypoint','chmod',REF['image'],
                'a+r',*('/y5audit/'+n for n in unreadable)],check=True)
    require((audit/'docker.jsonl').is_file(), 'Cannot confirm the Docker call '+str(trial))
    calls = list(audit.glob('exporter.*'))
    require(len(calls)==1, 'Cannot identify a single exporter call '+str(audit))
    argv = calls[0].read_text().splitlines()
    lemma = TASKS[i]['B2']['lemma']
    require(('--lemma='+lemma) in argv or any(argv[k:k+2]==['--lemma',lemma] for k in range(len(argv))), 'Wrong lemma '+str(calls[0]))
    result = dict(trial=trial.name, index=i, lemma=lemma, driver_rc=rc)
    if phase=='parse':
        marker = audit/'parse.rc'
        require(marker.exists() and (audit/'parser-inputs.txt').is_file()
                and len((audit/'parser-inputs.txt').read_text().splitlines())==1 and (audit/'translated.pv').stat().st_size>0,
                'No completion record of the syntax check '+str(trial))
        code = int(marker.read_text())
        log = (audit/'parse.log').read_text(errors='replace')
        syntax = bool(re.search(r'\bsyntax error\b',log,re.I))
        status = 'ACCEPTED' if code==0 and not syntax else 'SYNTAX_ERROR' if syntax else 'REVIEW'
        result.update(parse=status, parse_rc=code, generated_sha256=digest(audit/'translated.pv'))
    else:
        require(rc==0, 'Exit code of the official driver '+str(rc)+' '+str(trial))
        row,p = measured(work,i)
        shutil.copyfile(p,trial/('official-result'+p.suffix))
        result.update(row=row, category=category(row), source=str(p.relative_to(work)))
    write(done,result)
    return result


def summary(out):
    fields = ('index','lemma','B0','B2','B3_parse','parse_rc','B3_full','timeout','oom','translate_error',
              'proverif_result','proverif_error','restriction_missing','multiple_queries','seconds','parsed_pv_sha256')
    table = []
    parsed = completed = compared = paired = accepted = 0
    for i,refs in TASKS.items():
        diag_file = out/str(i)/'parse/done.json'
        full_file = out/str(i)/'full/done.json'
        diag = json.loads(diag_file.read_text()) if diag_file.exists() else {}
        full = json.loads(full_file.read_text()) if full_file.exists() else {}
        row = full.get('row', {})
        parsed += bool(diag)
        completed += bool(full)
        paired += bool(diag and full)
        accepted += diag.get('parse')=='ACCEPTED'
        compared += bool(full) and category(refs['B0'])==full['category']
        table.append([i,refs['B2']['lemma'],category(refs['B0']),category(refs['B2']),diag.get('parse','PENDING'),
                      diag.get('parse_rc'),full.get('category','PENDING'),row.get('proverif_timeout'),
                      row.get('proverif_oom'),row.get('translate_error'),
                      json.dumps(row['proverif_result']) if row else None,row.get('proverif_error'),
                      row.get('restriction_missing'),row.get('multiple_queries'),row.get('proverif_time'),
                      diag.get('generated_sha256')])
    tmp=out/'summary.pending'
    with tmp.open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(fields);w.writerows(table)
    tmp.replace(out/'summary.tsv')
    for r in table:
        print(f'{r[0]} {r[1]}  B0={r[2]}  B2={r[3]}  B3_parse={r[4]}  B3_full={r[6]}')
    print(f'syntax check {parsed}/5 (accepted {accepted}), ordinary run {completed}/5, same class as B0 {compared}/{completed}')
    return paired


def pack(out):
    count=summary(out)
    d=Path(tempfile.mkdtemp(prefix='yubikey5-send-',dir=out.parent))
    f=d/('yubikey5-results.tar.gz' if count==5 else 'yubikey5-partial.tar.gz')
    with tarfile.open(f,'w:gz') as t:
        for p in sorted(out.rglob('*')):
            rel=p.relative_to(out)
            if 'work' not in rel.parts and not p.is_symlink() and p.is_file() and p.name not in ('active.lock','submission-dir.txt'):
                t.add(p,arcname=str(Path('results')/rel),recursive=False)
        for name in ('run.py','proxy/docker','diag/proverif','references.json','README_ja.md'):
            t.add(KIT/name,arcname='kit/'+name,recursive=False)
    (d/(f.name+'.sha256')).write_text(digest(f)+'  '+f.name+'\n')
    (out/'submission-dir.txt').write_text(str(d)+'\n')
    print('Folder to submit '+str(d))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['check','parse','full','status','pack'])
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--state',type=Path,default=OLD)
    p.add_argument('--binary',type=Path,default=BIN)
    p.add_argument('--artifact',type=Path,help='Original Morio artifact root containing eval/ (optional)')
    p.add_argument('--id',type=int,choices=list(TASKS))
    a=p.parse_args()
    a.out=a.out.resolve(); a.binary=a.binary.resolve()
    require(a.out.is_dir(),'Create the output directory with mktemp -d')
    config=a.out/'conditions.json'
    with (a.out/'active.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.action=='status':
            require(config.is_file(),'conditions.json is missing. Check the output directory')
            summary(a.out);return
        if a.action=='pack':
            require(config.is_file(),'conditions.json is missing');pack(a.out);return
        ctx=settings(a)
        if config.exists():
            require(json.loads(config.read_text())==ctx[3],'The recorded conditions have changed. Use a new output directory')
        else:
            write(config,ctx[3])
        if a.action=='check':
            print('Ready. The official driver, the CSV, B3 and the hashes inside the container are confirmed');return
        for i in ([a.id] if a.id else TASKS):
            if a.action=='full':
                require((a.out/str(i)/'parse/done.json').is_file(),'Run parse first')
            r=one(a,ctx,i,a.action)
            print(i,r.get('parse',r.get('category')),flush=True)
        summary(a.out)


if __name__=='__main__':
    try:
        main()
    except (OSError,ValueError,KeyError,StopIteration,sp.CalledProcessError) as exc:
        sys.exit('Stopped '+str(exc))
