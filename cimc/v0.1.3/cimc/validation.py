"""Conservative supported-domain guards, shared by both printers.

No claim is made to support constructor decomposition. A variable inside an
equality subterm must already be bound at that point in the PV pattern.

Version 0.1.3 adds one guard on string literals. The back ends print the
numeral k as the ProVerif constant n<k> and as the Tamarin constant 'n<k>',
and a literal 'name' as c_name and as 'name'. A literal of the form n<k>
would therefore be one constant with the numeral k in Tamarin and a second
constant in ProVerif. Such literals are refused, as are literals that are no
plain identifiers.
"""
import re
from . import __version__
from .core import CimError, consts, free_vars, parse_atom

# Includes worker/public/private channels, dispatch/state binders, misuse
# binders, generated process/fact names, and common language keywords.
RESERVED = frozenset('c st x y s s0 Thread Responder St Thr Snap In Out Fr '
    'Clone Rollback Misuse Start bitstring channel process let in out new '
    'if then else get insert event query free const fun table type not '
    'true false All Ex rule lemma restriction theory begin end'.split())

def reserved(name):
    return (name in RESERVED or re.fullmatch(r'n\d+', name) is not None
            or name.startswith(('v_', 'c_', 'Thr_', 'Start_', 'Leak_')))

def report(m):
    names = set(m.fresh) | set(m.state_vars) | set(m.functions) | set(m.event_decl)
    names |= {n for n,_ in m.persist_vals}
    # Default role Thread is a backend label, not a user term/binder.
    if m.role != 'Thread': names.add(m.role)
    vals = [m.init] + ([m.publish_val] if m.publish_val is not None else [])
    vals += [v for _,v in m.persist_vals]
    if not m.fresh:
        return [('Hygiene','FAIL','initialization requires a fresh identity'),
                ('Binding','FAIL','no initial identity'),
                ('PatternSupported','FAIL','empty fresh list unsupported')]
    for c in m.thread_cases + m.resp_cases:
        names.update(c.binding)
        vals += [v for v in (c.state_in,c.state_out,c.inp) if v is not None]
        vals += c.outputs + [v for _,v in c.checks]
        vals += [a for _,args in c.events for a in args]
    vals += [a for _,args in m.leak_events for a in args]
    for v in vals: names.update(free_vars(v))
    for p in m.properties:
        for a in m._prop_atoms(p): names.update(parse_atom(a)[1])
    bad = sorted(n for n in names if reserved(n) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',n))
    literals = set()
    for v in vals: consts(v, literals)
    bad_literals = sorted(c for c in literals if isinstance(c, str)
                          and (re.fullmatch(r'n\d+', c) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', c)))
    bad += ["literal '%s'" % c for c in bad_literals]
    binding=[];pattern=[]
    def closed(v,known,where):
        missing=set(free_vars(v))-known
        if missing: binding.append(f'{where}: unbound {sorted(missing)}')
    def pat(v,known,where,prebound):
        if v[0]=='pair':
            pat(v[1],known,where,prebound);pat(v[2],known,where,prebound)
        elif v[0]=='var' and v[1] not in known:
            known.add(v[1])
        else: closed(v,prebound,where+' equality subterm (before pattern)')
    initial=set(m.fresh)
    for v in [m.init]+([m.publish_val] if m.publish_val is not None else [])+[v for _,v in m.persist_vals]:
        closed(v,initial,'initialization')
    for c in m.thread_cases + m.resp_cases:
        known=set(m.fresh) if c in m.thread_cases else set()
        if c.inp is not None:
            # PV 2.05 rejects top-level equality let =term = y. Do not
            # silently change this syntax or its semantics in this guard fix.
            if c.inp[0]!='pair' and not (c.inp[0]=='var' and c.inp[1] not in known):
                pattern.append(c.label+': scalar equality pattern unsupported')
            pat(c.inp,known,c.label,set(known))
        for v in [z for z in (c.state_in,c.state_out) if z is not None]+c.outputs+[v for _,v in c.checks]+[a for _,args in c.events for a in args]:
            closed(v,known,c.label+' body')
        if c in m.resp_cases and c.checks:
            closed(('var',m.fresh[0]),known,c.label+' table identity')
    for _,args in m.leak_events:
        for a in args:closed(a,initial,'leak event')
    if not m.fresh: binding.append('initialization requires a fresh identity')
    return [('Hygiene','FAIL' if bad else 'OK','unsupported reserved/invalid identifiers: '+', '.join(bad) if bad else 'no backend-reserved identifier collision'),
            ('Binding','FAIL' if binding else 'OK','; '.join(binding) or 'equality subterms and bodies closed at point of use'),
            ('PatternSupported','FAIL' if pattern else 'OK','; '.join(pattern) or 'supported PV input pattern shape')]

def require_supported(m):
    failures=[f'{k}: {d}' for k,s,d in report(m) if s=='FAIL']
    if failures: raise CimError(f'unsupported CIM ({__version__}): '+'; '.join(failures))
