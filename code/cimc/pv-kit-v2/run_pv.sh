#!/bin/bash
# Run ProVerif on every generated .pv file in a directory and write one
# JSON line per query to results/pv_results.jsonl.
# Usage: ./run_pv.sh <dir> [timeout_s]
set -u
DIR=${1:?dir}; TMO=${2:-3600}
mkdir -p results/pvout
OUT=results/pv_results.jsonl
for f in "$DIR"/*.pv; do
  b=$(basename "$f" .pv)
  s=$(date +%s.%N)
  timeout "$TMO" proverif "$f" > "results/pvout/$b.out" 2>&1; rc=$?
  t=$(echo "$(date +%s.%N) - $s" | bc)
  python3 - "$b" "$f" "results/pvout/$b.out" "$rc" "$t" >> "$OUT" <<'PY'
import sys, json, re, hashlib
b, src, out, rc, t = sys.argv[1:]
txt = open(out).read()
names = re.findall(r'^\(\* (\w+) \*\)\nquery', open(src).read(), re.M)
res = re.findall(r'^RESULT (.*) (is true|is false|cannot be proved)\.$', txt, re.M)
for i, (q, r) in enumerate(res):
    v = {'is true': 'true', 'is false': 'false', 'cannot be proved': 'cannot'}[r]
    print(json.dumps({'model': b, 'query': names[i] if i < len(names) else f'q{i}',
                      'verdict': v, 'rc': int(rc), 'seconds': round(float(t), 2),
                      'sha256': hashlib.sha256(open(src, 'rb').read()).hexdigest()}))
if not res:
    print(json.dumps({'model': b, 'query': '*', 'verdict': 'TIMEOUT' if rc == '124' else 'ERROR',
                      'rc': int(rc), 'seconds': round(float(t), 2)}))
PY
  echo "$b rc=$rc t=${t}s"
done
