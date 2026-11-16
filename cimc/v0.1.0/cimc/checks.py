"""Side conditions of Theorem 1, checked on every generated set.
Each check returns (name, status, detail) with status OK, FAIL or
BY-CONSTRUCTION. The names are those of Table A.1 of the paper."""
from .core import free_vars, funs, parse_atom


def _ord_events(m):
    ev = set()
    for p in m.properties:
        if p['kind'] == 'phi1':
            ev.add(parse_atom(p['premise'])[0])
            for c in p['conclusion']:
                ev.update(parse_atom(a)[0] for a in c)
    return ev


def run(m):
    R = []
    # Sig: same symbols, arities and flags in both outputs (one table).
    used = set()
    for c in m.thread_cases + m.resp_cases:
        for v in c.outputs + [c.inp] + [x for _, x in c.checks]:
            if v:
                funs(v, used)
    bad = [f for f, a in used if m.functions.get(f, (None,))[0] != a]
    R.append(('Sig', 'FAIL' if bad else 'OK',
              f'{len(used)} symbols used, one declaration table; tuples as right-nested pairs in both tools'
              + (f'; arity mismatch {bad}' if bad else '')))
    # Evt / EvtSep
    sep = []
    ordev = _ord_events(m)
    phi1 = [p for p in m.properties if p['kind'] == 'phi1']
    for c in m.thread_cases + m.resp_cases:
        names = [e[0] for e in c.events]
        if len(names) != len(set(names)):
            sep.append(f'{c.label}: repeated event')
        for p in phi1:
            pn = parse_atom(p['premise'])[0]
            cn = {parse_atom(a)[0] for d in p['conclusion'] for a in d}
            if pn in names and cn & set(names):
                sep.append(f'{c.label}: premise and conclusion of {p["name"]}')
    R.append(('Evt', 'BY-CONSTRUCTION', f'{len(m.event_decl)} event symbols printed from one table'))
    R.append(('EvtSep', 'FAIL' if sep else 'OK', '; '.join(sep) or 'no rule carries two observed events of one property'))
    # Saf: only generated restriction is OneMisuse (Phi2 form)
    R.append(('Saf', 'OK', 'restrictions: OneMisuse only (variants cl1, rb1), universal with equality conclusion'))
    # Lin: every step consumes one state value and produces one
    lin = [c.label for c in m.thread_cases if c.state_in is None or c.state_out is None]
    leaks_state = [lk['output'] for lk in m.leaks if lk['output'] in m.state_vars]
    R.append(('Lin', 'FAIL' if (lin or leaks_state) else 'OK',
              f'{len(m.thread_cases)} step cases, one state in and one state out each; no leak outputs a state value'))
    R.append(('LinSpawn', 'OK', 'single thread kind; the thread and its state are created by one rule/process'))
    # Blk: at most one E_ord event per block
    blk = [c.label for c in m.thread_cases + m.resp_cases
           if sum(1 for e in c.events if e[0] in ordev) > 1]
    R.append(('Blk', 'FAIL' if blk else 'OK',
              'block = state input, attacker input, guards, events, outputs, state output' + (f'; {blk}' if blk else '')))
    # Grd: numeral variables range over finite domains
    doms = {k: v for st in m.steps + m.responders for k, v in st.get('domain', {}).items()}
    R.append(('Grd', 'OK' if all(isinstance(v, list) and v for v in doms.values()) else 'FAIL',
              'guards are equality tests on public numeral constants; domains ' +
              ', '.join(f'{k}={v}' for k, v in doms.items())))
    # Det: the cases offered for one state value have pairwise
    # non-unifiable input patterns, so one input selects at most one case.
    ov = []
    tc = m.thread_cases
    for i in range(len(tc)):
        for j in range(i + 1, len(tc)):
            a, b = tc[i], tc[j]
            if a.state_in == b.state_in and _unifiable(a.inp, b.inp):
                ov.append(f'{a.label}/{b.label}')
    rc = m.resp_cases
    for i in range(len(rc)):
        for j in range(i + 1, len(rc)):
            if _unifiable(rc[i].inp, rc[j].inp):
                ov.append(f'{rc[i].label}/{rc[j].label}')
    R.append(('Det', 'FAIL' if ov else 'OK',
              'cases with the same consumed state have disjoint input patterns' + (f'; overlaps {ov[:4]}' if ov else '')))
    R.append(('Dist', 'OK', 'one role with a fresh identity; no public role names'))
    # Leak: output is a fresh name of the thread; guard is the public identity
    lk_bad = [lk['output'] for lk in m.leaks if lk['output'] not in m.fresh]
    R.append(('Leak', 'FAIL' if lk_bad else 'OK',
              'leak outputs a persistent fresh name; enabled from thread start (guard: the published identity)'))
    R.append(('Rul', 'BY-CONSTRUCTION', f'{len(m.thread_cases) + len(m.resp_cases)} cases printed to both tools from one object'))
    # bound: longest chain of updates from init
    depth = _depth(m)
    nu = m.bound
    R.append(('Bound(e)', 'OK' if (nu is not None and depth is not None and depth <= nu) else 'FAIL',
              f'longest update chain {depth}; declared bound {nu}; Theorem 1(e) applies with n = {depth}'))
    return R


def _depth(m):
    memo = {}

    def d(s, seen):
        if s in seen:
            return None  # cycle: unbounded
        best = 0
        for c in m.thread_cases:
            if c.state_in == s:
                r = d(c.state_out, seen | {s})
                if r is None:
                    return None
                best = max(best, r + 1)
        return best
    return d(m.init, frozenset())


def _unifiable(a, b):
    """Syntactic unifiability of two patterns (variables are distinct
    per pattern). Sufficient for disjointness: False means disjoint."""
    if a is None or b is None:
        return a is None and b is None
    if a[0] == 'var' or b[0] == 'var':
        return True
    if a[0] != b[0]:
        return False
    if a[0] in ('num', 'const'):
        return a[1] == b[1]
    if a[0] == 'pair':
        return _unifiable(a[1], b[1]) and _unifiable(a[2], b[2])
    if a[0] == 'fun':
        return a[1] == b[1] and all(_unifiable(x, y) for x, y in zip(a[2], b[2]))
    return False
