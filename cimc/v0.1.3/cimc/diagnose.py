"""Diagnosis of disagreements (Section 5.6 of the paper).

The decision tree below is FROZEN: its SHA-256 (of this file) is written
into every report, and the mutant study of Section 10 uses the hash that
was recorded before the mutants were generated. Change the tree only
together with a new version number.

Input: the records of one property, the side-condition report and the
inclusion chain. Output: one finding per disagreement or per missing
outcome, each with exactly one of the eight causes, or 'undetermined'.
"""
import hashlib
import os

TREE_VERSION = '1.1'
CAUSES = ('ENC-map', 'ENC-clone', 'PV-abs', 'PV-rec', 'PV-term',
          'TM-res', 'TM-search', 'SPEC-expr')

# Thresholds of the memory test (fixed with the tree).
FLAT_RATIO = 0.10        # late RSS growth <= 10 % of early growth: flat
FLAT_ABS_MB_MIN = 1.0    # or late growth <= 1 MB per minute


def tree_hash():
    with open(os.path.abspath(__file__), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def _misuse_split(prop, a, b):
    return prop.get('misuse_exception') and ({a.lo, a.hi, b.lo, b.hi} & {'Tcl', 'Trb'})


def diagnose(prop, recs, checks, chain):
    from .evidence import SYSTEMS, applies, implied_on_model
    out = []
    failed = [k for k, (s, _) in checks.items() if s == 'FAIL']

    # D1. Property text differs between the tools.
    if prop.get('rewrite'):
        out.append(dict(cause='SPEC-expr', records=[], note=f"rewritten for {prop['rewrite']}"))

    # D2. A side condition fails: every disagreement is ENC-map.
    if failed:
        dis = [r for r in recs if r.outcome != 'N']
        if len({r.outcome for r in dis}) > 1:
            out.append(dict(cause='ENC-map', records=[r.model for r in dis],
                            note='side conditions failed: ' + ', '.join(failed)))
        for r in recs:
            if r.outcome == 'N':
                out.append(_no_outcome(r, None, chain))
        return out

    # D3. Impossible pair (Corollary 2): H and W established on one system.
    # One finding per pair of records, listing the systems concerned.
    pairs = {}
    for s in SYSTEMS:
        for h in recs:
            if applies(chain, prop, h, s) != 'H':
                continue
            for w in recs:
                if applies(chain, prop, w, s) == 'W':
                    pairs.setdefault((h.model, w.model), []).append(s)
    for (hm, wm), ss in pairs.items():
        out.append(dict(cause='ENC-map', records=[hm, wm],
                        note=f'impossible pair on {", ".join(ss)}: a hypothesis, the generator or a tool is at fault'))
    if pairs:
        return out

    # D4. Opposite outcomes on models at different levels of the chain:
    # one finding per property, listing the holding and the failing models.
    hold, fail = set(), set()
    for a in recs:
        for b in recs:
            if a.outcome != 'H' or b.outcome != 'W' or _misuse_split(prop, a, b):
                continue
            if a.lo is not None and not chain.leq(b.hi, a.lo):
                hold.add(a)
                fail.add(b)
    if hold:
        hs = sorted(hold, key=lambda r: r.model)
        fs = sorted(fail, key=lambda r: r.model)
        out.append(dict(cause='ENC-clone', records=[r.model for r in hs + fs],
                        note='holds on ' + ', '.join(f'{r.enc} ({r.lo})' for r in hs)
                        + '; fails on ' + ', '.join(f'{r.enc} ({r.hi})' for r in fs)
                        + ': the difference is the reuse of a state value'))

    # D5. Missing outcomes.
    for r in recs:
        if r.outcome == 'N':
            out.append(_no_outcome(r, implied_on_model(chain, prop, r, recs), chain, recs))
    return out


def _no_outcome(r, implied, chain, recs=()):
    base = dict(records=[r.model], reason=r.reason)
    if r.tool == 'TR':
        return dict(base, cause='undetermined', note=f'translation path: {r.reason}')
    if r.tool == 'PV':
        if r.reason != 'cannot':
            return dict(base, cause='PV-term', note='saturation did not finish within the budget')
        kinds = {k for k, _ in implied} if implied else set()
        if kinds == {'H'}:
            return dict(base, cause='PV-abs', note='the property holds on this model (from '
                        + ', '.join(sorted({o.enc for _, o in implied})) + '): false alarm')
        if kinds == {'W'}:
            return dict(base, cause='PV-rec', note='an attack exists on this model (from '
                        + ', '.join(sorted({o.enc for _, o in implied})) + '): no trace reconstructed')
        if r.enc == 'lin' and any(o.outcome == 'W' and o.hi in ('Tcl', 'Trb', 'Tom') for o in recs):
            return dict(base, cause='PV-abs', provisional=True,
                        note='Corollary 1: the property fails with state reuse, so ProVerif cannot return true on PV-R_lin; truth on T not yet known')
        return dict(base, cause='undetermined', note='no other outcome on this model')
    # Tamarin
    if r.reason == 'HEAP' or r.feat.get('oom_confirmed') is True:
        return dict(base, cause='TM-res', note='memory limit reached')
    if r.reason == 'KILLED':
        return dict(base, cause='TM-res', provisional=True,
                    note='forced termination; exit code alone does not distinguish timeout escalation from OOM')
    if r.reason == 'TIMEOUT':
        e, l = r.feat.get('rss_growth_early_mb_per_min'), r.feat.get('rss_growth_late_mb_per_min')
        if e is None or l is None:
            return dict(base, cause='TM-res', provisional=True, note='time limit; no memory curve recorded')
        if l <= FLAT_ABS_MB_MIN or (e > 0 and l <= FLAT_RATIO * e):
            return dict(base, cause='TM-search', provisional=True,
                        note=f'time limit with flat sampled memory (early {e}, late {l} MB/min); heuristic, not proof of a missing invariant')
        return dict(base, cause='TM-res', provisional=True,
                    note=f'time limit with growing sampled memory (early {e}, late {l} MB/min); progress and benefit of more memory are not established')
    return dict(base, cause='undetermined', note=f'Tamarin ended with {r.reason}')
