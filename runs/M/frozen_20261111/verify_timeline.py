#!/usr/bin/env python3
"""Read existing experiment; write only a supplemental temporal audit."""
import sys, json, datetime, tarfile
from pathlib import Path
sys.dont_write_bytecode=True
from prospective import OUT, digest, dump, write, now
def dt(s): return datetime.datetime.fromisoformat(s)
m=json.loads((OUT/'freeze.json').read_text())
start=json.loads((OUT/'execution_started.json').read_text())
end=json.loads((OUT/'execution_finished.json').read_text())
rows=json.loads((OUT/'results.json').read_text())
assert digest(OUT/'freeze.json')==(OUT/'freeze.sha256').read_text().split()[0]==start['freeze_sha256']
assert dt(m['timestamp'])<dt(start['timestamp'])<dt(end['timestamp'])
events=[];previous=None
for r in rows:
    run=r['run']; began=dt(run['started_utc']); finished=began+datetime.timedelta(seconds=run['elapsed_s'])
    assert began>=dt(start['timestamp']) and finished<=dt(end['timestamp'])
    # elapsed_s is rounded to milliseconds; reconstructed start also has tiny
    # logging jitter, so permit 2ms rounding tolerance, never process overlap.
    gap=None if previous is None else (began-previous).total_seconds()
    assert gap is None or gap>=-.002
    assert digest(OUT/run['raw_file'])==run['raw_sha256']
    d=OUT/run['raw_file']; stored=json.loads((d.parent/'run.json').read_text())
    assert stored==run
    events.append(dict(tool=r['tool'],seed=r['seed'],operator=r['operator'],query_group=r.get('group',r['results'][0]['query']),started_utc=run['started_utc'],reconstructed_finish_utc=finished.isoformat(),gap_from_previous_s=gap,raw_file=run['raw_file'],raw_sha256=run['raw_sha256'],rc=run['rc'],stop_reason=run['stop_reason']))
    previous=finished
dump(OUT/'timeline_verification.json',dict(checked_at=now(),freeze_utc=m['timestamp'],execution_started_utc=start['timestamp'],execution_finished_utc=end['timestamp'],freeze_sha256=digest(OUT/'freeze.json'),runs=len(rows),all_raw_hashes_and_run_records_match=True,sequential_with_rounding_tolerance_ms=2,external_timestamp_signature=False,events=events))
files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and not p.name.endswith('.tar.gz') and p.name not in ['artifacts.sha256','final_artifacts.sha256']]
write(OUT/'final_artifacts.sha256',''.join(digest(p)+'  '+str(p.relative_to(OUT))+'\n' for p in files))
files.append(OUT/'final_artifacts.sha256')
archive=OUT/'quality_first_final_20261111.tar.gz'
with tarfile.open(archive,'w:gz') as t:
    for p in files:t.add(p,arcname='mutations/'+str(p.relative_to(OUT)),recursive=False)
with tarfile.open(archive,'r:gz') as t: assert len(t.getmembers())==len(files)
print(json.dumps(dict(runs=len(rows),freeze_utc=m['timestamp'],start_utc=start['timestamp'],end_utc=end['timestamp'],all_raw_hashes_verified=True,sequential=True,archive_bytes=archive.stat().st_size),ensure_ascii=False))
