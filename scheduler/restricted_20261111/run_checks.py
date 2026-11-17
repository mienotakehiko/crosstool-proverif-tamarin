"""Replay the restricted scheduler suite using the archived input snapshot."""
from pathlib import Path
from argparse import ArgumentParser
from tempfile import mkdtemp
import sys, os, shutil, hashlib, json, subprocess, copy, unittest
from collections import deque

parser = ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, help='new directory for replay outputs')
parser.add_argument('--with-provers', action='store_true', help='also run historical prover commands')
options = parser.parse_args()
ROOT = Path(__file__).resolve().parent / 'snapshot'
if options.output is None:
    OUT = Path(mkdtemp(prefix='restricted-scheduler-'))
else:
    OUT = options.output.resolve()
    OUT.mkdir(parents=True, exist_ok=False)
print(f'Replay output: {OUT}')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TMPDIR'] = str(OUT)
SOURCES = [ROOT/'cimc/cimc'/x for x in ('core.py','backends.py','checks.py','__init__.py')]
SOURCES += [ROOT/'cimc/tests/test_correspondence_guards.py', ROOT/'cimc/cims/lmots.toml', ROOT/'cimc/cims/lms_s2.toml', ROOT/'tex/paper/appendix_correspondence.tex', ROOT/'tex/paper/sections/5_method.tex', ROOT/'followup_20261029/research_followup.py', ROOT/'followup_20261029/research/bounded_reservation_check.json']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before = {str(p): sha(p) for p in SOURCES}
SNAP = OUT/'snapshot'
for p in SOURCES:
    q = SNAP/p.relative_to(ROOT)
    q.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p,q)
sys.path.insert(0,str(SNAP/'cimc'))
from cimc.core import Model, Case
from cimc.backends import proverif, tamarin
from cimc.checks import run

BASE = '''name = "Restricted"
[signature]
functions = [{name="seal",arity=1,private=true}]
[thread]
fresh = ["I"]
state = ["q"]
init = {q=0}
bound = 2
publish = "tup(I, 'a')"
[[thread.step]]
name="First"
domain={q=[0]}
input="tup('a', I)"
update={q="1"}
events=["EvA(I)"]
outputs=["seal(I)", "tup('a', I)"]
[[thread.step]]
name="Second"
domain={q=[1]}
input="tup('a', seal(I))"
update={q="2"}
events=["EvB(I)"]
outputs=[]
[[property]]
name="exec"
kind="phi3"
events=["EvA(I)","EvB(I)"]
'''
(OUT/'restricted.toml').write_text(BASE)
m=Model(OUT/'restricted.toml')
for enc in ('lin','U'):
    (OUT/f'restricted_{enc}.pv').write_text(proverif(m,enc,2,'0.1.1','restricted.toml'))
(OUT/'restricted_base.spthy').write_text(tamarin(m,'base','0.1.1','restricted.toml'))

# Ground term interpretation for THIS finite audit: names and constants tagged;
# seal is private, pairs publicly constructible/projectable. Closure is finite
# on relevant subterms, which suffices for these ground input patterns.
def term(v):
    if v[0] in ('var','const','num'): return (v[0],v[1])
    if v[0]=='pair': return ('pair',term(v[1]),term(v[2]))
    return ('fun',v[1],tuple(term(a) for a in v[2]))
def subs(t):
    r={t}
    if t[0]=='pair': r |= subs(t[1]) | subs(t[2])
    elif t[0]=='fun':
        for a in t[2]: r |= subs(a)
    return r
def setup(model):
    cs=model.thread_cases
    vals=[term(model.publish_val)] + [term(c.inp) for c in cs if c.inp is not None] + [term(o) for c in cs for o in c.outputs]
    universe=set().union(*(subs(t) for t in vals))
    def close(k):
        k=set(k)|{t for t in universe if t[0] in ('num','const')}
        while True:
            old=set(k)
            for t in list(k):
                if t[0]=='pair': k.update((t[1],t[2]))
            for t in universe:
                if t[0]=='pair' and t[1] in k and t[2] in k:k.add(t)
            if old==k:return frozenset(k)
    return cs, close, close({term(model.publish_val)})
def explore(model, concrete):
    cs,close,k0=setup(model)
    # stage: ready/reserved/dead, or post with (chosen case, output index).
    start=(term(model.init),'ready',-1,0,k0,())
    seen={start}; todo=deque([start]); edges=0
    while todo:
        q,stage,ci,j,k,tr=todo.popleft(); nxt=[]
        choices=[(i,c) for i,c in enumerate(cs) if term(c.state_in)==q]
        def commit(i,c):
            ev=tuple((e[0],tuple(term(a) for a in e[1])) for e in c.events)
            assert len(ev)<=1
            if concrete:return (term(c.state_out),'post',i,0,k,tr+ev)
            return (term(c.state_out),'ready',-1,0,close(k|{term(o) for o in c.outputs}),tr+ev)
        if stage=='ready':
            if concrete:nxt.append((q,'reserved',-1,0,k,tr))
            else:
                for i,c in choices:
                    if c.inp is None or term(c.inp) in k:nxt.append(commit(i,c))
        elif stage=='reserved':
            # Some public numeral can fail all finite ground patterns.
            nxt.append((q,'dead',-1,0,k,tr))
            for i,c in choices:
                if c.inp is None or term(c.inp) in k:nxt.append(commit(i,c))
        elif stage=='post':
            c=cs[ci]
            if j<len(c.outputs):nxt.append((q,'post',ci,j+1,close(k|{term(c.outputs[j])}),tr))
            else:nxt.append((q,'ready',-1,0,k,tr))
        for n in nxt:
            edges+=1
            if n not in seen:seen.add(n);todo.append(n)
    return seen,edges

class Audit(unittest.TestCase):
    def test_existing_report_accepts_fixture(self):
        self.assertNotIn('FAIL',[s for _,s,_ in run(m)])
    def test_ground_trace_equality_and_forward_relation(self):
        a,_=explore(m,False);p,_=explore(m,True);cs,close,_=setup(m)
        self.assertEqual({s[-1] for s in a},{s[-1] for s in p})
        for q,stage,ci,j,k,tr in p:
            debt={term(o) for o in cs[ci].outputs[j:]} if stage=='post' else set()
            self.assertIn((q,'ready',-1,0,close(k|debt),tr),a)
    def test_saturated_completion_for_every_atomic_edge(self):
        a,_=explore(m,False);p,_=explore(m,True)
        # Each atomic reachable state has an exact stable concrete witness.
        self.assertTrue(a <= p)
    def test_eventless_case(self):
        z=copy.deepcopy(m);z.thread_cases[0].events=[]
        self.assertEqual({s[-1] for s in explore(z,False)[0]}, {s[-1] for s in explore(z,True)[0]})
    def test_no_input_case_still_requires_public_dispatch(self):
        z=copy.deepcopy(m);z.thread_cases[0].inp=None
        text=proverif(z,'lin',2,'0.1.1','mutant')
        self.assertIn('in(c, y: bitstring)',text)
        self.assertEqual({s[-1] for s in explore(z,False)[0]}, {s[-1] for s in explore(z,True)[0]})
    def test_overlap_is_not_choice(self):
        z=copy.deepcopy(m);c=copy.deepcopy(z.thread_cases[0]);c.step='Duplicate';c.events=[('EvDup',[('var','I')])];z.thread_cases.append(c)
        self.assertEqual(dict((n,s) for n,s,_ in run(z))['Det'],'FAIL')
        text=proverif(z,'lin',2,'0.1.1','overlap')
        self.assertIn('\n       | ',text)
        # Two successful parallel case branches emit E,F after one input;
        # base has one token so cannot take First AND Duplicate from q=0.
        self.assertEqual(sum(c.state_in==m.init and c.inp==m.thread_cases[0].inp for c in z.thread_cases),2)
        z.event_decl['EvDup']=1
        z.properties=[dict(name='overlap',kind='phi3',events=['EvA(I)','EvDup(I)'])]
        (OUT/'overlap.pv').write_text(proverif(z,'lin',2,'0.1.1','overlap'))
        (OUT/'overlap.spthy').write_text(tamarin(z,'base','0.1.1','overlap'))
    def test_missing_binding_guard(self):
        z=copy.deepcopy(m);z.thread_cases[0].inp=('pair',('const','a'),('fun','seal',[('var','x')]))
        report=run(z)
        self.assertNotIn('FAIL',[s for _,s,_ in report])
        text=proverif(z,'lin',2,'0.1.1','unbound')
        self.assertIn('=seal(x)',text)
        (OUT/'unbound_guard.pv').write_text(text)
        (OUT/'unbound_report.json').write_text(json.dumps(report,indent=2))
    def test_backend_reserved_identifier_capture_guard_missing(self):
        z=copy.deepcopy(m)
        z.thread_cases[0].inp=('pair',('const','a'),('var','x'))
        z.thread_cases[0].events=[('E',[('var','x')])]
        self.assertNotIn('FAIL',[s for _,s,_ in run(z)])
        text=proverif(z,'lin',2,'0.1.1','capture')
        self.assertIn('v_x: bitstring',text)
        # Generated input binder intentionally renamed, but ground equality
        # subterm in the other mutant above is not bound and captures state x.
    def test_genuinely_unbound_constructor_variable_not_rejected_by_report(self):
        z=copy.deepcopy(m);z.thread_cases[0].inp=('pair',('const','a'),('fun','seal',[('var','Z')]))
        self.assertNotIn('FAIL',[s for _,s,_ in run(z)])
        (OUT/'undefined_guard.pv').write_text(proverif(z,'lin',2,'0.1.1','undefined'))
    def test_capture_counterexample_generated_pair(self):
        z=copy.deepcopy(m)
        z.publish_val=('pair',('var','I'),('fun','seal',[('num',1)]))
        z.thread_cases=z.thread_cases[:1]
        z.thread_cases[0].inp=('pair',('const','a'),('fun','seal',[('var','x')]))
        z.properties=[dict(name='capture',kind='phi3',events=['EvA(I)'])]
        self.assertNotIn('FAIL',[s for _,s,_ in run(z)])
        (OUT/'capture.pv').write_text(proverif(z,'lin',2,'0.1.1','capture'))
        (OUT/'capture.spthy').write_text(tamarin(z,'base','0.1.1','capture'))
    def test_unused_empty_thread_fresh_is_not_supported(self):
        z=copy.deepcopy(m);z.fresh=[]
        with self.assertRaises(IndexError): proverif(z,'lin',2,'0.1.1','no_fresh')
        with self.assertRaises(IndexError): tamarin(z,'base','0.1.1','no_fresh')
    def test_abandonment_prevents_reverse_from_arbitrary_related_state(self):
        a,_=explore(m,False);p,_=explore(m,True)
        dead=[s for s in p if s[0]==term(m.init) and s[1]=='dead']
        self.assertTrue(dead)
        self.assertTrue(any(s[-1] for s in a))

suite=unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.discover(str(SNAP/'cimc/tests'),pattern='test_correspondence_guards.py'))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Audit))
with (OUT/'tests.log').open('w') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
if not options.with_provers:
    print(f'Tests: {result.testsRun}; failures: {len(result.failures)}; errors: {len(result.errors)}')
    sys.exit(0 if result.wasSuccessful() and all(sha(Path(s)) == h for s, h in before.items()) else 1)

commands=[]
# Preserve and exercise the scalar-pattern parse counterexample separately.
scalar=copy.deepcopy(m);scalar.thread_cases[0].inp=('const','a')
(OUT/'scalar_pattern.pv').write_text(proverif(scalar,'lin',2,'0.1.1','scalar'))
for f in ('restricted_lin.pv','restricted_U.pv','unbound_guard.pv','undefined_guard.pv','scalar_pattern.pv','capture.pv','overlap.pv'):
    cmd=['proverif',str(OUT/f)]
    try:
        p=subprocess.run(cmd,cwd=OUT,capture_output=True,text=True,timeout=30)
        raw=p.stdout+p.stderr;rc=p.returncode
    except subprocess.TimeoutExpired as e:
        raw=str(e);rc='timeout'
    (OUT/(f+'.log')).write_text(raw)
    commands.append({'command':cmd,'rc':rc,'result_lines':[l for l in raw.splitlines() if l.startswith('RESULT') or 'Error' in l or 'not defined' in l]})
# Native Tamarin execution: subprocess deadline only guards this local prover,
# never a gsk request. Resource limit is internal RTS, output stays here.
cmd=['tamarin-prover','--prove','--derivcheck-timeout=0',str(OUT/'restricted_base.spthy'),'+RTS','-N1','-M450m','-RTS']
try:
    p0=subprocess.run(cmd,cwd=OUT,capture_output=True,text=True,timeout=60)
    raw=p0.stdout+p0.stderr;rc=p0.returncode
except subprocess.TimeoutExpired as e:
    raw=(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else (e.stdout or '')
    raw+='\nTIMEOUT after 60s';rc='timeout'
(OUT/'restricted_base.spthy.log').write_text(raw)
commands.append({'command':cmd,'rc':rc,'result_lines':[l for l in raw.splitlines() if 'exec (' in l or 'WARNING' in l or 'wellformed' in l.lower() or 'TIMEOUT' in l]})
cmd=['tamarin-prover','--prove','--derivcheck-timeout=0',str(OUT/'capture.spthy'),'+RTS','-N1','-M450m','-RTS']
try:
    cp=subprocess.run(cmd,cwd=OUT,capture_output=True,text=True,timeout=60)
    raw=cp.stdout+cp.stderr;rc=cp.returncode
except subprocess.TimeoutExpired as e:
    raw='TIMEOUT after 60s';rc='timeout'
(OUT/'capture.spthy.log').write_text(raw)
commands.append({'command':cmd,'rc':rc,'result_lines':[l for l in raw.splitlines() if 'capture (' in l or 'WARNING' in l or 'wellformed' in l.lower() or 'TIMEOUT' in l]})
cmd=['tamarin-prover','--prove','--derivcheck-timeout=0',str(OUT/'overlap.spthy'),'+RTS','-N1','-M450m','-RTS']
try:
    cp=subprocess.run(cmd,cwd=OUT,capture_output=True,text=True,timeout=60)
    raw=cp.stdout+cp.stderr;rc=cp.returncode
except subprocess.TimeoutExpired:
    raw='TIMEOUT after 60s';rc='timeout'
(OUT/'overlap.spthy.log').write_text(raw)
commands.append({'command':cmd,'rc':rc,'result_lines':[l for l in raw.splitlines() if 'overlap (' in l or 'WARNING' in l or 'wellformed' in l.lower() or 'TIMEOUT' in l]})
a,ae=explore(m,False);p,pe=explore(m,True)
summary={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'scope':'Ground single initialized thread scheduler only; relevant-term closure; no full symbolic-semantics theorem','atomic_states':len(a),'process_states':len(p),'atomic_edges':ae,'process_edges':pe,'atomic_traces':len({s[-1] for s in a}),'process_traces':len({s[-1] for s in p}),'abandoned_states':sum(s[1]=='dead' for s in p),'commands':commands,'upstream_unchanged':all(sha(Path(s))==h for s,h in before.items())}
(OUT/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'source_manifest.json').write_text(json.dumps(before,indent=2)+'\n')
print(json.dumps(summary,indent=2))
if not result.wasSuccessful() or not summary['upstream_unchanged']:sys.exit(1)
