"""Achievement Level (AL) of every property of one CIM (Section 5.5).

usage: python3 -m cimc.al_assign <cim.toml> <checks.txt> -o <prefix>
         [--pv pv_results.jsonl ...] [--tm tam.jsonl|tam.tsv ...]
         [--tri triangulation.jsonl ...]

Writes <prefix>.json (machine-readable, with the evidence of every level
and the hashes of this script and of the diagnosis tree) and <prefix>.md.
No level requires a manual judgment.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

from . import __version__
from .evidence import (Chain, SYSTEMS, applies, load_checks, load_cim, load_records)
from .diagnose import diagnose, tree_hash, TREE_VERSION

LEVEL_NAME = {4: 'Cross-validated', 3: 'Transferred', 2: 'Triangulated',
              1: 'Single-model', 0: 'Inconclusive'}


def _tm_to_jsonl(paths):
    """Accept kit records.jsonl and run_tam_generated.sh TSV files."""
    tmp = tempfile.NamedTemporaryFile('w', delete=False, suffix='.jsonl')
    for p in paths:
        for line in open(p):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            if line.startswith('{'):
                r = json.loads(line)
                r['model'] = re.sub(r'(\.spthy)$', '', r['model'])
            else:
                f = line.split('\t')
                r = dict(model=f[0], lemma=f[1], verdict=f[2], rc=int(f[3]), seconds=float(f[4]),
                         raw=f[5] if len(f) > 5 else '')
                m = re.search(r'\((\d+) steps\)', r['raw'])
                r['steps'] = int(m.group(1)) if m else None
            tmp.write(json.dumps(r) + '\n')
    tmp.close()
    return tmp.name


def scope_label(chain, s, fixed_params):
    lab = chain.label(s)
    if fixed_params and lab.startswith('U'):
        lab = 'P' + lab[1:]
    return lab


def level_for(chain, prop, recs, s, failed, findings):
    """Outcome and assurance level on system s."""
    if failed:
        # without the theorem only direct evidence on s counts
        use = [r for r in recs if r.lo == r.hi == s and r.tool in ('TM', 'TR')]
    else:
        use = recs
    est = {}
    for r in use:
        o = applies(chain, prop, r, s) if not failed else (r.outcome if r.outcome != 'N' else None)
        if o:
            est.setdefault(o, []).append(r)
    if len(est) != 1:
        return (None, 0, [], 'conflict' if len(est) > 1 else 'no outcome')
    (o, ev), = est.items()
    tools = {r.tool for r in ev}
    direct = [r for r in ev if r.lo == r.hi == s]
    if 'PV' in tools and 'TM' in tools and not failed:
        return (o, 4, ev, 'both tools' + ('' if direct else ', via Theorem 1'))
    main = tools - {'TR'}
    other = 'TM' if 'PV' in main else 'PV'
    # the other tool counts only with a model that could have decided s
    other_n = [r for r in recs if r.tool == other and r.outcome == 'N'
               and _could_decide(chain, prop, r, s, o)]
    diagnosed = [f for f in findings if f['cause'] != 'undetermined'
                 and any(m in f['records'] for m in (r.model for r in other_n))]
    if not failed and other_n and diagnosed:
        return (o, 3, ev, f'{other} gave no outcome on ' + ', '.join(r.enc for r in other_n)
                + '; cause ' + ', '.join(sorted({f["cause"] for f in diagnosed})))
    if 'TR' in tools and len(tools) > 1:
        return (o, 2, ev, 'one tool and the translation agree' +
                ('' if failed else '; the other tool gave no outcome'))
    return (o, 1, ev, 'one tool' + ('' if direct else ' via Theorem 1'))


def _could_decide(chain, prop, r, s, o):
    """Would outcome o on r's model have established o on s?"""
    from .evidence import Record
    probe = Record.__new__(Record)
    probe.__dict__.update(r.__dict__)
    probe.outcome = o
    return applies(chain, prop, probe, s) == o


def al_string(scope, lvl, outcome, kind):
    sup = 'a' if (outcome == 'W' and kind in ('phi1', 'phi2')) else ''
    return f'AL-{scope}{lvl}' + (f'^{sup}' if sup else '')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='al_assign')
    ap.add_argument('cim')
    ap.add_argument('checks')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--pv', nargs='*', default=[])
    ap.add_argument('--tm', nargs='*', default=[])
    ap.add_argument('--tri', nargs='*', default=[])
    a = ap.parse_args(argv)

    name, props = load_cim(a.cim)
    import tomllib
    meta = tomllib.load(open(a.cim, 'rb')).get('meta', {})
    fixed = bool(meta.get('parameters')) and not meta.get('cutoff', False)
    checks = load_checks(a.checks)
    failed = [k for k, (s, _) in checks.items() if s == 'FAIL']
    b = checks.get('Bound(e)', ('FAIL', ''))
    mn = re.search(r'n = (\d+)', b[1])
    chain = Chain(bound_ok=(b[0] == 'OK'), n=int(mn.group(1)) if mn else 0)
    tm = _tm_to_jsonl(a.tm) if a.tm else None
    recs = load_records(name, props, a.pv, [tm] if tm else [], a.tri)
    if tm:
        os.unlink(tm)

    report = dict(cim=os.path.basename(a.cim), name=name, cimc=__version__,
                  al_assign_sha256=hashlib.sha256(open(__file__, 'rb').read()).hexdigest(),
                  diagnosis_tree=TREE_VERSION, diagnosis_sha256=tree_hash(),
                  checks_failed=failed, bound_transfer=chain.bound_ok,
                  fixed_parameters=meta.get('parameters'), properties={})
    md = [f'# Achievement Levels for {name}', '',
          f'cimc {__version__}; diagnosis tree {TREE_VERSION} (sha256 {tree_hash()[:12]}); '
          f'side conditions: {"all OK" if not failed else "FAIL " + ", ".join(failed)}; '
          f'Theorem 1(e): {"applies, n = " + str(chain.n) if chain.bound_ok else "does not apply"}'
          + (f'; parameters fixed ({meta["parameters"]}), scope P' if fixed else ''), '']
    for pn, p in props.items():
        pr = [r for r in recs if r.prop == pn]
        findings = diagnose(p, pr, checks, chain)
        rows = []
        for s in SYSTEMS:
            if s == 'Tle' and chain.bound_ok:
                continue  # identical to T
            o, lvl, ev, why = level_for(chain, p, pr, s, failed, findings)
            sc = scope_label(chain, s, fixed)
            rows.append(dict(system=s, scope=sc, outcome=o, level=lvl,
                             al=al_string(sc, lvl, o, p['kind']) if o else f'AL-{sc}0',
                             evidence=[f'{r.enc}:{r.raw}' for r in ev], basis=why))
        head = next((r for r in rows if r['system'] == 'T' and r['outcome']), None) \
            or next((r for r in rows if r['system'] == 'Tle' and r['outcome']), None)
        report['properties'][pn] = dict(kind=p['kind'], headline=head['al'] if head else 'AL-0',
                                        systems=rows, records=[repr(r) for r in pr],
                                        findings=findings)
        md += [f'## {pn} ({p["kind"]}): {head["al"] if head else "AL-0"}', '',
               '| System | Scope | Outcome | Level | AL | Evidence | Basis |',
               '|---|---|---|---|---|---|---|']
        for r in rows:
            oc = {'H': 'holds' if p['kind'] != 'phi3' else 'unreachable',
                  'W': 'attack' if p['kind'] != 'phi3' else 'reachable', None: '-'}[r['outcome']]
            md.append(f"| {r['system']} | {r['scope']} | {oc} | {r['level']} {LEVEL_NAME[r['level']]} "
                      f"| {r['al']} | {', '.join(r['evidence']) or '-'} | {r['basis']} |")
        if findings:
            md += ['', 'Diagnosis:', '']
            for f in findings:
                md.append(f"- **{f['cause']}**{' (provisional)' if f.get('provisional') else ''}: "
                          f"{', '.join(f['records']) or '-'}; {f['note']}")
        md.append('')
    with open(a.out + '.json', 'w') as f:
        json.dump(report, f, indent=1)
    with open(a.out + '.md', 'w') as f:
        f.write('\n'.join(md) + '\n')
    print('\n'.join(md))
    return 0


if __name__ == '__main__':
    sys.exit(main())
