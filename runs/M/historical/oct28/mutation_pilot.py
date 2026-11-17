#!/usr/bin/env python3
"""Small real-tool mutation pilot; not the planned broad mutation study."""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
KIT=ROOT.parent/'cimc'
sys.path.insert(0,str(KIT))
from cimc.diagnose import TREE_VERSION, tree_hash, diagnose
from cimc.evidence import Chain, Record

OUT=ROOT/'mutation_pilot'
OUT.mkdir(exist_ok=True)
freeze=dict(version=TREE_VERSION,sha256=tree_hash(),
            recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            scope='prospective small pilot only; earlier unit tests are not blinded mutation evidence')
(OUT/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
pv=(KIT/'out/lmots/LMOTS_PV_U1.pv').read_text()
tm=(KIT/'out/lmots/LMOTS_T_base.spthy').read_text()
cases=[('control','none',pv,tm),
       ('event_argument','one-sided event mismatch',pv.replace('event Accept(v_I, n0)','event Accept(v_I, n1)'),tm),
       ('missing_reveal_event','one-sided observation mismatch',pv.replace('event RevealSeed(I); ',''),tm),
       ('replicated_signer','one-sided state linearity mismatch',pv.replace('( in(c, y: bitstring) [precise];','( !in(c, y: bitstring) [precise];'),tm)]
manifest=[]
for name,operator,p,t in cases:
    d=OUT/name;d.mkdir(exist_ok=True)
    (d/'model.pv').write_text(p);(d/'model.spthy').write_text(t)
    manifest.append(dict(case=name,operator=operator,pv_sha256=hashlib.sha256(p.encode()).hexdigest(),
                         tm_sha256=hashlib.sha256(t.encode()).hexdigest(),
                         expected='no mismatch' if name=='control' else 'ENC-map',
                         scope='LMOTS fixed w=2,p=2, U1 versus unchanged T'))
(OUT/'manifest_before_runs.json').write_text(json.dumps(manifest,indent=2)+'\n')
results=[]
for entry in manifest:
    name=entry['case'];d=OUT/name
    runs={}
    for tool,args in [('PV',['proverif',str(d/'model.pv')]),
                      ('TM',['tamarin-prover','--prove=LS1_unforge','--derivcheck-timeout=0',str(d/'model.spthy'),'+RTS','-M700m','-RTS'])]:
        try:
            r=subprocess.run(args,capture_output=True,text=True,timeout=45,env=dict(os.environ,LC_ALL='C.UTF-8'))
            text=r.stdout+r.stderr;rc=r.returncode
        except subprocess.TimeoutExpired as e:
            text=(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout or '';rc=124
        (d/(tool+'.out')).write_text(text)
        if tool=='PV':
            hits=re.findall(r'^RESULT (.*) (is true|is false|cannot be proved)\.$',text,re.M)
            verdict={'is true':'H','is false':'W','cannot be proved':'N'}.get(hits[1][1],'N') if len(hits)>=2 else 'N'
        else:
            m=re.search(r'LS1_unforge \(all-traces\): (verified|falsified)',text)
            verdict={'verified':'H','falsified':'W'}.get(m[1],'N') if m else 'N'
        runs[tool]=dict(rc=rc,outcome=verdict)
    recs=[Record('X_PV_U1','p',runs['PV']['outcome'],'cannot' if runs['PV']['outcome']=='N' else None,'pilot'),
          Record('X_T_base','p',runs['TM']['outcome'],'TIMEOUT' if runs['TM']['outcome']=='N' else None,'pilot')]
    findings=diagnose({'kind':'phi1'},recs,{'Sig':('OK','')},Chain(True,1))
    # These intentionally stale checks test D3, not checker sensitivity.
    detected=any(f['cause']=='ENC-map' for f in findings)
    results.append(dict(entry,runs=runs,findings=findings,detected=detected,
                        matches_expected=not detected if name=='control' else detected,
                        caveat='D3 pilot with intentionally stale side-condition metadata; not end-to-end checker validation'))
    print(name,runs,'ENC-map',detected,flush=True)
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('PILOT',sum(x['matches_expected'] for x in results),'/',len(results))
