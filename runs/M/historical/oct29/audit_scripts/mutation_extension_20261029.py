#!/usr/bin/env python3
"""Prospective bounded extension; raw outcomes, not eight-class accuracy."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_extension_20261029 import execute, pv_results, ROOT
from cimc.core import Model
from cimc.backends import proverif, tamarin
from cimc.checks import run as checks
from cimc.diagnose import tree_hash, TREE_VERSION, diagnose
from cimc.evidence import Chain, Record

OUT = ROOT/'audit_20261028/mutation_extension_20261029'


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    freeze = dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  tree_version=TREE_VERSION, tree_sha256=tree_hash(),
                  checks_sha256=hashlib.sha256((ROOT/'cimc/cimc/checks.py').read_bytes()).hexdigest(),
                  scope='Two fixed signer seeds; ten one-sided operators. Not the planned O1-O10 study; no eight-class accuracy claim.',
                  interpretation='Stale IR checks are intentionally retained for output-text mutations. Survivors are not assumed equivalent.')
    (OUT/'freeze_before_generation.json').write_text(json.dumps(freeze, indent=2)+'\n')
    manifest=[]
    for seed in ('lmots','lms_s2'):
        m=Model(ROOT/'cimc/cims'/f'{seed}.toml')
        pv=proverif(m,'U',m.bound,'0.1.0',f'{seed}.toml')
        tm=tamarin(m,'base','0.1.0',f'{seed}.toml')
        # Identical source properties on both paths. Keep the baseline query
        # order; only the process following "let Responder" is mutated.
        head,body=pv.split('let Responder()',1)
        sign='event Sign(I, '
        ops=[('control',pv,tm),
             ('event_accept_argument',head+'let Responder()'+body.replace('event Accept(v_I, n0','event Accept(v_I, n3'),tm),
             ('event_sign_argument',head+'let Responder()'+body.replace(sign+'n0',sign+'n3'),tm),
             ('remove_reveal_event',head+'let Responder()'+body.replace('event RevealSeed(I); ',''),tm),
             ('replicate_signer',head+'let Responder()'+body.replace('( in(c, y: bitstring) [precise];','( !in(c, y: bitstring) [precise];'),tm),
             ('disable_signer',head+'let Responder()'+body.replace('event Sign(I,','if n0 = n1 then event Sign(I,'),tm),
             ('disable_accept',head+'let Responder()'+body.replace('event Accept(v_I,','if n0 = n1 then event Accept(v_I,'),tm),
             ('unguarded_reveal',head+'let Responder()'+body.replace('(in(c, =I); event RevealSeed(I);','(event RevealSeed(I);'),tm),
             ('wrong_public_key',head+'let Responder()'+body.replace('insert Pk(I,','insert Pk(sd,' ).replace('insert Root(I,','insert Root(sd,'),tm),
             ('private_to_public',pv.replace(': bitstring [private].',': bitstring.'),tm),
             ('reveal_wrong_secret',head+'let Responder()'+body.replace('event RevealSeed(I); out(c, sd)','event RevealSeed(I); out(c, I)'),tm)]
        for op,p,t in ops:
            assert op=='control' or p!=pv, (seed,op)
            d=OUT/f'{seed}__{op}';d.mkdir(exist_ok=True)
            (d/'model.pv').write_text(p);(d/'model.spthy').write_text(t)
            manifest.append(dict(seed=seed,operator=op,directory=d.name,pv_sha256=sha(p),tm_sha256=sha(t),
                                 source_cim_sha256=hashlib.sha256((ROOT/'cimc/cims'/f'{seed}.toml').read_bytes()).hexdigest(),
                                 queries=[x['name'] for x in m.properties if not x.get('misuse_exception')],
                                 kinds=[x['kind'] for x in m.properties if not x.get('misuse_exception')],
                                 checks=checks(m),expected='control' if op=='control' else 'one-sided model change; verdict discrepancy not guaranteed'))
    # A separate counterexample to the old checker contract. It removes
    # identity publication on BOTH paths; only PV's leak guard needs it.
    m=Model(ROOT/'cimc/cims/lmots.toml');m.publish_val=None
    for c in m.thread_cases:c.outputs=[]
    m.properties=[dict(name='reveal_reachable',kind='phi3',events=['RevealSeed(I)'])]
    d=OUT/'unpublished_identity';d.mkdir(exist_ok=True)
    p=proverif(m,'U',1,'0.1.0','unpublished_identity');t=tamarin(m,'base','0.1.0','unpublished_identity')
    (d/'model.pv').write_text(p);(d/'model.spthy').write_text(t)
    manifest.append(dict(seed='counterexample',operator='unpublished_identity',directory=d.name,
                         pv_sha256=sha(p),tm_sha256=sha(t),queries=['reveal_reachable'],kinds=['phi3'],
                         checks=checks(m),expected='old checks pass but reachability differs; tests missing LeakGuard condition'))
    (OUT/'manifest_before_runs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows=[]
    for item in manifest:
        d=OUT/item['directory']
        a=execute(['proverif',str(d/'model.pv')],d/'PV.out',15)
        aa=pv_results((d/'PV.out').read_text())
        b=execute(['tamarin-prover','--prove','--derivcheck-timeout=0',str(d/'model.spthy'),
                   '+RTS','-N1','-M500m','-RTS'],d/'TM.out',15)
        import re
        bb={l:(q,v) for l,q,v in re.findall(r'^\s*(\w+) \((all-traces|exists-trace)\): (verified|falsified)',(d/'TM.out').read_text(),re.M)}
        results=[]
        for i,(q,k) in enumerate(zip(item['queries'],item['kinds'])):
            pv_v=aa[i]['verdict'] if i<len(aa) else 'NO_RESULT'
            tm_v=bb.get(q,('','NO_RESULT'))[1]
            po={'is true':'H','is false':'W'}.get(pv_v,'N')
            to=({'verified':'W','falsified':'H'} if k=='phi3' else {'verified':'H','falsified':'W'}).get(tm_v,'N')
            recs=[Record('X_PV_U2',q,po,'cannot' if po=='N' else None,pv_v),Record('X_T_base',q,to,None,tm_v)]
            findings=diagnose(dict(kind=k),recs,{x:(s,z) for x,s,z in item['checks']},Chain(True,2))
            results.append(dict(query=q,kind=k,pv=pv_v,tm=tm_v,normalized_pv=po,normalized_tm=to,
                                discrepancy=po!='N' and to!='N' and po!=to,findings=findings))
        row=dict(item,pv_run=a,tm_run=b,results=results)
        rows.append(row)
        (OUT/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(item['directory'],[(x['query'],x['normalized_pv'],x['normalized_tm']) for x in results],flush=True)


if __name__=='__main__':main()
