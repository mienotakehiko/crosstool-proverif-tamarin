#!/usr/bin/env python3
"""Stream the user's archive and compare to the authoritative final-job map."""
import collections
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT=Path(__file__).resolve().parent.parent
archive=ROOT/'U1_U7_all_saved_original_out.tar.gz'
expected=(ROOT/'U1_U7_all_saved_original_out.sha256').read_text().split()[0]
h=hashlib.sha256()
with archive.open('rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
assert h.hexdigest()==expected
latest=json.loads((ROOT/'audit_20261028/derived/latest_records.json').read_text())
rows=[]; errors=[]; counts=collections.Counter(); phases=collections.defaultdict(collections.Counter)
with tarfile.open(archive,'r|gz') as tar:
    seen=set()
    for member in tar:
        p=Path(member.name)
        assert member.isfile() and not p.is_absolute() and '..' not in p.parts
        job=p.stem
        assert job in latest and job not in seen
        seen.add(job)
        rec=latest[job]; found=None; steps=None; heap=False
        for raw in tar.extractfile(member):
            line=raw.decode('utf-8',errors='replace')
            m=re.search(r'^\s*'+re.escape(rec['lemma'])+r' \((?:all-traces|exists-trace)\): (verified|falsified|analysis cannot be finished)(.*)',line)
            if m:
                found=m[1]
                s=re.search(r'\((\d+) steps\)',m[2]);steps=int(s[1]) if s else None
            heap=heap or 'Heap exhausted' in line
        value=found or ('HEAP' if heap else 'unresolved')
        want=rec['verdict']
        ok=(found==want if want in ('verified','falsified') else
            found=='analysis cannot be finished' if want=='ERROR' else
            heap if want=='HEAP' else found is None)
        if found in ('verified','falsified'):
            ok=ok and steps==rec.get('steps')
        if not ok:errors.append(job)
        counts[value]+=1;phases[job.split('_')[0]][value]+=1
        rows.append(dict(job=job,recorded=want,raw=value,steps=steps,matched=ok))
assert seen==set(latest)
assert not errors,errors
result=dict(archive_sha256=expected,method='Streaming comparison to final-job records; no summary is not independent proof of timeout/OOM.',
            counts=dict(counts),by_phase={k:dict(v) for k,v in phases.items()},mismatches=errors,unmatched=[],rows=rows)
(ROOT/'audit_20261028/derived/all_saved_stdout_audit_20261029.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(sha256_match=True,unique_jobs=len(rows),counts=dict(counts),mismatches=errors),indent=2))
