#!/usr/bin/env python3
"""Use a single hash-identical unchanged Tamarin reference, not 11 reruns."""
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from research_extension_20261029 import ROOT
from cimc.evidence import Record,Chain
from cimc.diagnose import diagnose

folder=ROOT/'audit_20261028/mutation_extension_20261029'
rows=json.loads((folder/'results.json').read_text())
ref=ROOT/'audit_20261028/extension_20261029_rss/lms_s2'
expected=hashlib.sha256((ref/'generated.spthy').read_bytes()).hexdigest()
text=(ref/'tamarin.out').read_text()
verdicts={l:(q,v) for l,q,v in re.findall(r'^\s*(\w+) \((all-traces|exists-trace)\): (verified|falsified)',text,re.M)}
assert len(verdicts)==5
for row in rows:
    if row['seed']!='lms_s2':continue
    assert row['tm_sha256']==expected
    row['reference_completion']=dict(source='../extension_20261029_rss/lms_s2/tamarin.out',
        model_sha256=expected,stdout_sha256=hashlib.sha256(text.encode()).hexdigest(),
        note='Shared unchanged source, executed once at 30s. Original 15s attempts remain saved; not independent replicates.')
    for x in row['results']:
        v=verdicts[x['query']][1]
        x['tm']=v
        x['normalized_tm']=({'verified':'W','falsified':'H'} if x['kind']=='phi3' else {'verified':'H','falsified':'W'})[v]
        x['discrepancy']=x['normalized_pv']!='N' and x['normalized_pv']!=x['normalized_tm']
        records=[Record('X_PV_U2',x['query'],x['normalized_pv'],None,x['pv']),Record('X_T_base',x['query'],x['normalized_tm'],None,v)]
        x['findings']=diagnose(dict(kind=x['kind']),records,{k:(s,d) for k,s,d in row['checks']},Chain(True,2))
(folder/'results_completed_reference.json').write_text(json.dumps(rows,indent=2)+'\n')
mutants=[x for x in rows if x['seed'] in ('lmots','lms_s2') and x['operator']!='control']
controls=[x for x in rows if x['operator']=='control']
summary=dict(mutants=len(mutants),with_discrepancy=sum(any(z['discrepancy'] for z in x['results']) for x in mutants),
             controls=len(controls),control_discrepancies=sum(any(z['discrepancy'] for z in x['results']) for x in controls),
             unclassified_survivors=[x['directory'] for x in mutants if not any(z['discrepancy'] for z in x['results'])],
             caveat='10 selected one-sided operators, two fixed signer seeds; stale checks retained. Not O1-O10 coverage, not eight-class accuracy, not end-to-end output validator.')
(folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
