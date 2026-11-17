"""Evidence model shared by diagnose.py and al_assign.py.

Every verdict is normalized to an outcome on the traces of one model:
  H  no trace of the kind the property describes (a proof for Phi1/Phi2,
     unreachability for Phi3);
  W  such a trace exists (an attack for Phi1/Phi2, reachability for Phi3);
  N  no outcome; the record keeps the reason (cannot, TIMEOUT, HEAP, ...).

Each generated model M is placed between two reference systems of the
inclusion chain of Theorem 1, lo(M) and hi(M), with
  Tr(lo(M)) <= Tr(M) <= Tr(hi(M)).
Then H on M gives H on every S <= lo(M), and W on M gives W on every
S >= hi(M). This is the whole of Table 4 (transfer of verdicts).
"""
import json
import re
import tomllib

SYSTEMS = ['Tle', 'T', 'Trb', 'Tcl', 'Tom']
# strict order of the chain (Theorem 1(c)); Tle <= T always
_EDGES = {('Tle', 'T'), ('T', 'Tcl'), ('T', 'Trb'), ('Tcl', 'Tom'), ('Trb', 'Tom')}


def _closure(edges):
    rel = {(s, s) for s in SYSTEMS} | set(edges)
    changed = True
    while changed:
        changed = False
        for a, b in list(rel):
            for c, d in list(rel):
                if b == c and (a, d) not in rel:
                    rel.add((a, d))
                    changed = True
    return rel


class Chain:
    def __init__(self, bound_ok, n):
        self.bound_ok = bound_ok          # Theorem 1(e): Tle = T
        self.n = n
        edges = set(_EDGES)
        if bound_ok:
            edges.add(('T', 'Tle'))
        self.rel = _closure(edges)

    def leq(self, a, b):
        if a is None:                     # bottom: the empty trace set
            return True
        if b is None:
            return a is None
        return (a, b) in self.rel

    def label(self, s):
        return {'Tle': f'B({self.n})', 'T': 'U', 'Tcl': 'U_C', 'Trb': 'U_R',
                'Tom': 'U_w'}[s]


# model kind -> (tool, lo, hi)
def model_kind(model):
    m = re.search(r'_PV_(U|Urb)(\d+)$', model)
    if m:
        return ('PV', 'Tle', 'Tle', m.group(1) + m.group(2)) if m.group(1) == 'U' \
            else ('PV', None, 'Trb', 'Urb' + m.group(2))
    if model.endswith('_PV_lin'):
        return ('PV', 'T', 'T', 'lin')
    if model.endswith('_PV_rep'):
        return ('PV', 'Tom', 'Tom', 'rep')
    m = re.search(r'_T_(base|cl1|rb1|omega)$', model)
    if m:
        s = {'base': 'T', 'cl1': 'Tcl', 'rb1': 'Trb', 'omega': 'Tom'}[m.group(1)]
        return ('TM', s, s, m.group(1))
    if model.endswith('__tri'):            # translated ProVerif of a Tamarin variant
        k = model_kind(model[:-5])
        return ('TR', k[1], k[2], 'tri-' + k[3])
    raise ValueError(f'unknown model kind: {model}')


class Record:
    def __init__(self, model, prop, outcome, reason, raw, feat=None):
        self.model = model
        self.tool, self.lo, self.hi, self.enc = model_kind(model)
        self.prop = prop
        self.outcome = outcome            # H | W | N
        self.reason = reason              # for N: cannot | noterm | TIMEOUT | HEAP | KILLED | ...
        self.raw = raw
        self.feat = feat or {}

    def __repr__(self):
        return f'{self.enc}:{self.outcome}' + (f'({self.reason})' if self.outcome == 'N' else '')


def load_cim(path):
    with open(path, 'rb') as f:
        s = tomllib.load(f)
    props = {}
    for p in s.get('property', []):
        props[p['name']] = p
    return s['name'], props


def same_formula(p, q):
    keys = ('kind', 'premise', 'conclusion', 'events', 'absent')
    return all(p.get(k) == q.get(k) for k in keys)


def load_checks(path):
    st = {}
    for line in open(path):
        if line.startswith('#') or not line.strip():
            continue
        parts = line.split(None, 2)
        st[parts[0]] = (parts[1], parts[2].strip() if len(parts) > 2 else '')
    return st


def pv_outcome(v):
    return {'true': ('H', None), 'false': ('W', None), 'cannot': ('N', 'cannot')}.get(
        v, ('N', 'noterm'))


def tm_outcome(v, exists):
    if v == 'verified':
        return ('W', None) if exists else ('H', None)
    if v == 'falsified':
        return ('H', None) if exists else ('W', None)
    return ('N', v)


def tri_outcome(v, exists):
    if exists:
        return {'exists': ('W', None), 'no_trace': ('H', None)}.get(
            v, ('N', 'unmapped' if v in ('true', 'false') else v))
    return {'true': ('H', None), 'false': ('W', None), 'cannot': ('N', 'cannot')}.get(v, ('N', v))


def load_records(name, props, pv_files=(), tm_files=(), tri_files=()):
    recs = []
    alias = {}
    # Properties with a misuse exception are printed for ProVerif only in
    # their pure form; ProVerif results of an identical formula apply.
    for pn, p in props.items():
        if p.get('misuse_exception'):
            for qn, q in props.items():
                if not q.get('misuse_exception') and same_formula(p, q):
                    alias.setdefault(qn, []).append(pn)
    for f in pv_files:
        for line in open(f):
            r = json.loads(line)
            if not r['model'].startswith(name + '_PV_'):
                continue
            o, why = pv_outcome(r['verdict'])
            targets = [r['query']] if r['query'] != '*' else list(props)
            for q in targets:
                if q not in props:
                    continue
                for pn in [q] + alias.get(q, []):
                    recs.append(Record(r['model'], pn, o, why, r['verdict'],
                                       {'seconds': r.get('seconds')}))
    for f in tm_files:
        for line in open(f):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            r = json.loads(line)
            if not r['model'].startswith(name + '_T_') or r['lemma'] not in props:
                continue
            ex = props[r['lemma']]['kind'] == 'phi3'
            o, why = tm_outcome(r['verdict'], ex)
            recs.append(Record(r['model'], r['lemma'], o, why, r['verdict'], r))
    # Translator records (kit3/triangulate.sh): 'model' is the Tamarin file
    # name; exists-trace lemmas are exported negated and come back as
    # 'exists' / 'no_trace'; all-traces lemmas as 'true' / 'false'.
    for f in tri_files:
        for line in open(f):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            r = json.loads(line)
            m = r.get('model') or r.get('source', '')
            m = m[:-6] if m.endswith('.spthy') else m
            if not m.startswith(name + '_T_') or r['lemma'] not in props:
                continue
            o, why = tri_outcome(r['verdict'], props[r['lemma']]['kind'] == 'phi3')
            recs.append(Record(m + '__tri', r['lemma'], o, why, r['verdict'], r))
    return recs


def applies(chain, prop, rec, s):
    """Can record rec establish an outcome for system s?
    Returns the outcome (H or W) it establishes on s, or None."""
    if rec.outcome == 'N':
        return None
    if prop.get('misuse_exception') and (s in ('Tcl', 'Trb') or rec.lo in ('Tcl', 'Trb')):
        # the formula differs on the misuse variants: direct evidence only
        if not (rec.lo == rec.hi == s):
            return None
    if rec.outcome == 'H' and rec.lo is not None and chain.leq(s, rec.lo):
        return 'H'
    if rec.outcome == 'W' and chain.leq(rec.hi, s):
        return 'W'
    return None


def implied_on_model(chain, prop, rec, others):
    """Outcome on the traces of rec's model implied by the other records."""
    found = set()
    for o in others:
        if o is rec or o.outcome == 'N':
            continue
        if prop.get('misuse_exception') and ({rec.lo, rec.hi, o.lo, o.hi} & {'Tcl', 'Trb'}) \
                and not (rec.lo == rec.hi == o.lo == o.hi):
            continue
        if o.outcome == 'H' and o.lo is not None and chain.leq(rec.hi, o.lo):
            found.add(('H', o))
        if o.outcome == 'W' and rec.lo is not None and chain.leq(o.hi, rec.lo):
            found.add(('W', o))
    return found
