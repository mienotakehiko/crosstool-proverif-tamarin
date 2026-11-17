"""Bounded proof-obligation tests and a local-export semantic control.

These checks are not a proof of the generated process semantics.
"""
from pathlib import Path
import sys, json, hashlib, re, datetime
from collections import deque

ROOT=Path('/redacted-home/workspace')
OUT=ROOT/'followup_20261029/research'
sys.path.insert(0,str(ROOT/'audit_20261028'))
from research_extension_20261029 import execute
from cimc.core import Model
from cimc.backends import tamarin

def abstract():
    initial=((0,0),frozenset({'a'}),())
    seen={initial};queue=deque([initial])
    while queue:
        states,knowledge,trace=queue.popleft()
        for i,q in enumerate(states):
            if q<2 and ('a' if q==0 else 'b') in knowledge:
                nxt=list(states);nxt[i]+=1
                new=(tuple(nxt),knowledge|{'b'},trace+((i,q),))
                if new not in seen:seen.add(new);queue.append(new)
    return {s[2] for s in seen},len(seen)

def concrete():
    # Per thread: (state, stage); available/reserved/post-event/output-1.
    # Post-event phases retain the successor locally until both outputs.
    initial=(((0,'available'),(0,'available')),frozenset({'a'}),())
    seen={initial};queue=deque([initial]);abandoned=0
    while queue:
        workers,knowledge,trace=queue.popleft()
        for i,(q,stage) in enumerate(workers):
            choices=[]
            if stage=='available' and q<2:choices=[(q,'reserved',knowledge,trace)]
            elif stage=='reserved':
                # A failed guard abandons the reserved state silently.
                choices=[(q,'abandoned',knowledge,trace)]
                if ('a' if q==0 else 'b') in knowledge:
                    choices.append((q+1,'post_event',knowledge,trace+((i,q),)))
            elif stage=='post_event':choices=[(q,'output_1',knowledge|{'b'},trace)]
            elif stage=='output_1':choices=[(q,'available',knowledge|{'c'},trace)]
            for nq,ns,nk,nt in choices:
                nw=list(workers);nw[i]=(nq,ns);new=(tuple(nw),nk,nt)
                if new not in seen:seen.add(new);queue.append(new)
    abandoned=sum(any(st=='abandoned' for _,st in s[0]) for s in seen)
    return {s[2] for s in seen},len(seen),abandoned

def main():
    OUT.mkdir(exist_ok=True)
    a,an=abstract();b,bn,ab=concrete()
    proof=dict(scope='Two fixed threads, two acyclic updates each, finite public messages, one event and two delayed outputs per block; reservation and guard-failure abandonment. No fresh names, responders, leaks, Clone or Rollback.',
               abstract_states=an,concrete_states=bn,states_with_abandonment=ab,
               abstract_event_traces=len(a),concrete_event_traces=len(b),
               abstract_only=[list(x) for x in a-b],concrete_only=[list(x) for x in b-a],
               trace_sets_equal=a==b,interpretation='Finite abstraction regression only, not generated-code verification or a complete theorem.')
    assert a==b
    (OUT/'bounded_reservation_check.json').write_text(json.dumps(proof,indent=2)+'\n')
    rows=[]
    old=ROOT/'audit_20261028/extension_20261029_namespaced'
    for seed in ('lmots','lms_s2'):
        source=old/seed/f'{seed}.toml';m=Model(source)
        d=OUT/seed;d.mkdir(exist_ok=True)
        p=d/'omega.spthy';p.write_text(tamarin(m,'omega','0.1.1',source.name))
        frozen=dict(cim_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),model_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Native persistent-state control for the prior local exporter; not pinned CCS translator',time=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (d/'manifest_before_run.json').write_text(json.dumps(frozen,indent=2)+'\n')
        result=execute(['tamarin-prover','--prove','--derivcheck-timeout=0',str(p),'+RTS','-N1','-M600m','-RTS'],d/'omega.out',30)
        verdicts=[dict(lemma=l,quantifier=q,verdict=v) for l,q,v in re.findall(r'^\s*(\w+) \((all-traces|exists-trace)\): (verified|falsified)',(d/'omega.out').read_text(),re.M)]
        rows.append(dict(seed=seed,manifest=frozen,run=result,verdicts=verdicts))
        print(seed,result['rc'],verdicts,flush=True)
    (OUT/'persistent_control.json').write_text(json.dumps(rows,indent=2)+'\n')
    probes=[]
    for seed in ('lmots','lms_s2'):
        for op in ('control','remove_reveal_event'):
            src=ROOT/'audit_20261028/mutation_extension_20261029'/f'{seed}__{op}'/'model.pv'
            text=src.read_text().replace('let Responder()', 'query I:bitstring; event(RevealSeed(I)) ==> false.\n\nlet Responder()',1)
            d=OUT/f'{seed}__{op}__reveal_probe';d.mkdir(exist_ok=True)
            f=d/'model.pv';f.write_text(text)
            result=execute(['proverif',str(f)],d/'PV.out',20)
            matches=re.findall(r'^RESULT (.*) (is true|is false|cannot be proved)\.$',(d/'PV.out').read_text(),re.M)
            selected=[dict(query=q,verdict=v) for q,v in matches if q.startswith('not event(RevealSeed')]
            probes.append(dict(seed=seed,operator=op,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),probe_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),run=result,probe_results=selected))
            print('PROBE',seed,op,selected,flush=True)
    (OUT/'survivor_probe.json').write_text(json.dumps(dict(scope='Post-hoc reachability sensitivity check, outside LeakUse theorem fragment; not a prospective diagnostic-accuracy study; original frozen 12/20 result unchanged.',runs=probes),indent=2)+'\n')
    print('BOUNDED_SIMULATION',json.dumps(proof),flush=True)

if __name__=='__main__':main()
