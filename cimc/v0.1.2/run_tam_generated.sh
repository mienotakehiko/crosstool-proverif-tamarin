#!/bin/bash
# Run Tamarin 1.12.0 on the generated Tamarin variants (64 GB machine).
# Usage: HEAP=56g TMO=86400 [MEMSTEP=10] ./run_tam_generated.sh <dir>
# Writes results/tam_generated.tsv (one line per job) and
# results/tam_generated.jsonl (the same plus the RSS growth in the first and
# last 30 % of the run, used by the diagnosis of TIMEOUT); the memory curve
# of each job is kept in results/tamout/<model>_<lemma>.mem.
# Skips jobs that already have a verdict.
set -u
export LC_ALL=C.UTF-8 LANG=C.UTF-8
DIR=${1:?dir}; HEAP=${HEAP:-56g}; TMO=${TMO:-86400}; STEP=${MEMSTEP:-10}
mkdir -p results/tamout; OUT=results/tam_generated.tsv; JS=results/tam_generated.jsonl
touch "$OUT" "$JS"
for f in "$DIR"/*_T_*.spthy; do
  b=$(basename "$f" .spthy)
  for l in $(grep -oE '^lemma [A-Za-z0-9_]+' "$f" | awk '{print $2}'); do
    grep -qP "^$b\t$l\t(verified|falsified)" "$OUT" && continue
    o=results/tamout/${b}_$l; s=$(date +%s)
    timeout "$TMO" tamarin-prover +RTS -M"$HEAP" -RTS --prove="$l" "$f" > "$o.out" 2>&1 &
    tp=$!; : > "$o.mem"
    ( while kill -0 $tp 2>/dev/null; do
        kb=0
        for p in $(pgrep -P $tp) $(for c in $(pgrep -P $tp); do pgrep -P $c; done); do
          kb=$((kb + $(ps -o rss= -p $p 2>/dev/null || echo 0)))
        done
        printf '%d\t%d\n' $(( $(date +%s)-s )) $((kb/1024)) >> "$o.mem"; sleep "$STEP"
      done ) &
    sp=$!; wait $tp; rc=$?; kill $sp 2>/dev/null; wait $sp 2>/dev/null
    r=$(grep -E "^  $l \(" "$o.out" | head -1 | sed 's/^ *//')
    case "$r" in *verified*) v=verified;; *falsified*) v=falsified;; *) v=OTHER;; esac
    grep -q 'Heap exhausted' "$o.out" && v=HEAP
    [ $rc = 251 ] && v=HEAP; [ $rc = 124 ] && v=TIMEOUT; [ $rc = 137 ] && v=KILLED
    t=$(( $(date +%s)-s ))
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$b" "$l" "$v" "$rc" "$t" "$r" | tee -a "$OUT"
    python3 - "$b" "$l" "$v" "$rc" "$t" "$r" "$o.mem" "$HEAP" "$TMO" >> "$JS" <<'PY'
import json, re, sys
b, l, v, rc, t, r, mem, heap, tmo = sys.argv[1:]
c = [tuple(map(int, x.split())) for x in open(mem) if len(x.split()) == 2]
def slope(seg):
    if len(seg) < 2 or seg[-1][0] == seg[0][0]:
        return None
    return round((seg[-1][1] - seg[0][1]) / ((seg[-1][0] - seg[0][0]) / 60), 1)
n = len(c)
m = re.search(r'\((\d+) steps\)', r)
print(json.dumps(dict(model=b, lemma=l, verdict=v, rc=int(rc), seconds=float(t), raw=r,
                      steps=int(m.group(1)) if m else None, heap_cap=heap, timeout_s=int(tmo),
                      rss_max_mb=max((x[1] for x in c), default=None),
                      rss_growth_early_mb_per_min=slope(c[:max(2, int(0.3 * n))]) if n >= 4 else None,
                      rss_growth_late_mb_per_min=slope(c[int(0.7 * n):]) if n >= 4 else None)))
PY
  done
done
