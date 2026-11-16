"""Compare results/pv_results.jsonl with tests/expected_*.tsv."""
import json, glob, sys
got = {}
for l in open('results/pv_results.jsonl'):
    r = json.loads(l); got[(r['model'], r['query'])] = r['verdict']
bad = n = 0
models = {m for m, _ in got}
files = sys.argv[1:] or ['tests/expected_lms_s2.tsv', 'tests/expected_lmots.tsv']
for f in files:
    for l in open(f):
        if l.startswith('#') or not l.strip(): continue
        m, q, e, _ = l.rstrip('\n').split('\t')
        if m not in models: continue  # CIM not run in this results file
        g = got.get((m, q), 'MISSING'); n += 1
        flag = 'ok' if g == e else '!!'
        bad += g != e
        print(f'{flag} {m:16s} {q:12s} expected={e:7s} got={g}')
print(f'{n - bad}/{n} as expected')
sys.exit(1 if bad else 0)
