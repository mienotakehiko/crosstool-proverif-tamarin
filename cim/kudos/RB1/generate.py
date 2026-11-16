#!/usr/bin/env python3
"""Small JSON -> two bounded symbolic model routes; no verdict-dependent emission."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = ['parent', 'input_a', 'input_b', 'm1', 'm2']
CONSTS = ['client', 'server', 'zero', 'empty']

def f(name, *args):
    return (name, *args)

def plan(c):
    """Term/state plan, independent of hypothesis_collision field."""
    p, a, b = 'parent', 'input_a', 'input_b'
    tmp = f('kdf', p, f('xn', a, 'empty'))
    new = f('kdf', p, f('xn', a, b))
    z, one = 'zero', f('succ', 'zero')
    if c['family'] == 'H1':
        k = f('key', new, 'server')
        iv1 = f('civ', tmp) if c['first'] == 'Na' else f('civ', new)
        n1 = f('nce', 'server' if c['first'] == 'own' else 'client', z, iv1)
        q2 = z if c['client_reset'] else one
        ssn2 = one if c['first'] == 'own' else z
        n2 = f('nce', 'server' if c['second'] == 'own' else 'client',
               ssn2 if c['second'] == 'own' else q2, f('civ', new))
        return [(k, n1, 'm1'), (k, n2, 'm2')], (new, q2)
    # TEMP context: input2 is empty. Re-derivation recomputes, not a fresh name.
    oldctx = tmp
    parent2 = oldctx if c['new_parent'] else p
    a2 = b if c['fresh_inputs'] else a
    ctx2 = f('kdf', parent2, f('xn', a2, 'empty')) if c['restart'] else oldctx
    counter2 = one if (c['retain_counter'] or not c['restart']) else z
    return [(f('key', oldctx, 'server'), f('nce', 'server', z, f('civ', oldctx)), 'm1'),
            (f('key', ctx2, 'server'), f('nce', 'server', counter2, f('civ', ctx2)), 'm2')], (ctx2, counter2)

def term(t, route):
    if isinstance(t, tuple):
        return t[0] + '(' + ','.join(term(x, route) for x in t[1:]) + ')'
    return t if route == 'pv' else ("'" + t + "'" if t in CONSTS else '~' + t)

def state_events(c):
    if c['family']=='H1':
        return [('RequestState',('client','zero')),('RequestState',('client','zero' if c['client_reset'] else f('succ','zero')))]
    old=f('kdf','parent',f('xn','input_a','empty'))
    p=old if c['new_parent'] else 'parent'
    a='input_b' if c['fresh_inputs'] else 'input_a'
    counter=f('succ','zero') if c['retain_counter'] or not c['restart'] else 'zero'
    return [('ContextState',('parent','input_a','zero')),
            ('RederiveState' if c['restart'] else 'ContinueState',(p,a,counter))]

def pv(c, algebra):
    uses, _ = plan(c)
    s = '(* NEW bounded abstract model; no network or recovered trace. *)\n'
    s += '\n'.join(f'fun {n}(' + ','.join(['bitstring']*arity) + '): bitstring.' for n,arity in algebra.items())+'\n'
    s += 'free ' + ','.join(CONSTS) + ': bitstring.\n'
    s += 'event AeadUse(bitstring,bitstring,bitstring).\nevent Normal().\n'
    s += 'event ContextStep(bitstring,bitstring).\n'
    s += 'event RequestState(bitstring,bitstring).\n'
    for name in ['ContextState','RederiveState','ContinueState']:
        s += f'event {name}(bitstring,bitstring,bitstring).\n'
    s += 'query k:bitstring,n:bitstring,x:bitstring,y:bitstring; event(AeadUse(k,n,x)) && event(AeadUse(k,n,y)) ==> x = y.\n'
    s += 'query event(Normal()).\nprocess\n'
    s += ''.join(f'new {n}:bitstring;\n' for n in NAMES)
    for i,use in enumerate(uses):
        name,values=state_events(c)[i]
        s += 'event '+name+'('+','.join(term(t,'pv') for t in values)+');\n'
        s += 'event ContextStep(' + term(use[0],'pv') + ',' + term(use[1],'pv') + ');\n'
        s += 'event AeadUse(' + ','.join(term(t,'pv') for t in use) + ');\n'
    return s + 'event Normal();\n0\n'

def tm(c, algebra):
    uses, state = plan(c)
    u1, u2 = [','.join(term(t,'tm') for t in use) for use in uses]
    # Linear one-shot gate: no repeated initialisation, hence same finite scope as PV.
    s = f'theory {c["id"]}\nbegin\nfunctions: ' + ', '.join(f'{n}/{a}' for n,a in algebra.items())+'\n'
    s += 'restriction OneInit:\n "All #i #j. Init()@i & Init()@j ==> #i = #j"\n'
    s += 'rule Init:\n [ '+', '.join(f'Fr(~{n})' for n in NAMES)+' ] --[ Init() ]-> [ Ready('+','.join('~'+n for n in NAMES)+') ]\n'
    args = ','.join('~'+n for n in NAMES)
    se=[name+'('+','.join(term(t,'tm') for t in values)+')' for name,values in state_events(c)]
    s += f'rule Encrypt1:\n [ Ready({args}) ] --[ {se[0]}, ContextStep({term(uses[0][0],"tm")},{term(uses[0][1],"tm")}), AeadUse({u1}) ]-> [ AfterFirst({args}) ]\n'
    s += f'rule Encrypt2:\n [ AfterFirst({args}) ] --[ {se[1]}, ContextStep({term(uses[1][0],"tm")},{term(uses[1][1],"tm")}), AeadUse({u2}), Normal() ]-> [ ]\n'
    s += 'lemma normal: exists-trace\n "Ex #i. Normal()@i"\n'
    s += 'lemma collision: exists-trace\n "Ex k n x y #i #j. AeadUse(k,n,x)@i & AeadUse(k,n,y)@j & not(x = y)"\n'
    s += 'lemma no_collision: all-traces\n "All k n x y #i #j. AeadUse(k,n,x)@i & AeadUse(k,n,y)@j ==> x = y"\nend\n'
    return s

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def generate(check=False):
    spec = json.loads((ROOT/'spec.json').read_text())
    paths = {}
    for c in spec['cases']:
        for ext, fn in [('pv',pv),('spthy',tm)]:
            p = ROOT/'models'/f'{c["id"]}.{ext}'
            data = fn(c,spec['algebra']).encode()
            if check:
                if not p.exists() or p.read_bytes()!=data:
                    raise SystemExit(f'generated mismatch: {p.name}')
            else:
                p.parent.mkdir(exist_ok=True)
                p.write_bytes(data)
            paths[str(p.relative_to(ROOT))]=hashlib.sha256(data).hexdigest()
    manifest={'schema':1,'spec_sha256':digest(ROOT/'spec.json'), 'generator_sha256':digest(Path(__file__)), 'files':paths}
    mp=ROOT/'generated_manifest.json'
    if check:
        assert json.loads(mp.read_text()) == manifest, 'manifest differs'
    else:
        mp.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'generated_checked' if check else 'generated':len(paths)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true')
    generate(ap.parse_args().check)
