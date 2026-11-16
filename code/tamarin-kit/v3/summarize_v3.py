#!/usr/bin/env python3
"""Summarise results/records.jsonl (kit v3).

Writes results/summary_v3.md with
  1. the latest run of every job (verdict, time, peak heap, RSS, steps);
  2. the comparison with expected_v3.tsv, with "!!" marking differences
     from the prediction;
  3. the T0/T1 pairs (default heuristic versus tactic) side by side;
  4. the R3 candidates: jobs that ran out of heap at the highest cap and
     whose RSS curve flattens (late growth <= half of the early growth).
"""
import fnmatch, json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in open(os.path.join(HERE, 'results', 'records.jsonl')) if l.strip()]
latest = collections.OrderedDict()
for r in recs:
    latest[r['job']] = r

expect = []
for line in open(os.path.join(HERE, 'expected_v3.tsv')):
    if line.startswith('#') or not line.strip():
        continue
    model, lemma, exp, why = line.rstrip('\n').split('\t')
    expect.append((model, lemma, exp, why))


def expected(r):
    m = r['model'].replace('.spthy', '').split('__')[0]
    for pm, pl, e, why in expect:
        if fnmatch.fnmatch(m, pm) and fnmatch.fnmatch(r['lemma'], pl):
            return e, why
    return None, ''


out = []
w = out.append
w('# Kit v3 results\n')
w('| job | verdict | s | heap MB | RSS MB | steps | expected | |')
w('|---|---|---|---|---|---|---|---|')
for j, r in latest.items():
    e, _ = expected(r)
    mark = ''
    if e and r['verdict'] in ('verified', 'falsified') and r['verdict'] != e:
        mark = '!!'
    w(f"| {j} | {r['verdict']} | {r['seconds']} | {r['peak_heap_mb']} | {r['rss_max_mb']} | {r['steps']} | {e or ''} | {mark} |")

w('\n## Default heuristic (T0) versus tactic (T1)\n')
w('| model | lemma | T0 | T1 |')
w('|---|---|---|---|')
pairs = collections.defaultdict(dict)
for r in latest.values():
    if r['job'].startswith(('P1_', 'P0_')) and r['tool'] == 'std':
        base = r['model'].split('__')[0]
        v = 'T1' if r['heuristic'] == 'tactic' else 'T0'
        pairs[(base, r['lemma'])][v] = f"{r['verdict']} {r['seconds']}s {r['peak_heap_mb']}MB {r['steps'] or ''}"
for (m, l), d in sorted(pairs.items()):
    w(f"| {m} | {l} | {d.get('T0', '')} | {d.get('T1', '')} |")

w('\n## Candidates for R3 (cloud, more than 56 GB)\n')
w('Rule fixed in advance: heap exhausted at the highest cap tried, and the RSS growth in the last 30 % of the run is at most half of the growth in the first 30 %.\n')
w('| job | cap | early MB/min | late MB/min | candidate |')
w('|---|---|---|---|---|')
for r in latest.values():
    if r['verdict'] == 'HEAP':
        e, l = r['rss_growth_early_mb_per_min'], r['rss_growth_late_mb_per_min']
        cand = 'yes' if (e and l is not None and e > 0 and l <= 0.5 * e) else 'no'
        w(f"| {r['job']} | {r['heap_cap']} | {e} | {l} | {cand} |")

path = os.path.join(HERE, 'results', 'summary_v3.md')
open(path, 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
print(f'\nwritten to {path}')
