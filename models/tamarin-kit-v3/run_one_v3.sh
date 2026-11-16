#!/bin/bash
# Prove one lemma once and write one JSON record (kit v3).
#
#   usage: run_one_v3.sh <job_id> <tool> <variant_file> <lemma> <heur> <search> <heap> <timeout_s>
#     tool     std (tamarin-prover, historically 1.12.0) or cyc (tamarin-cyclic)
#     heur     default | s | S | C | I | c | i  (T4); "tactic" means --heuristic={statefirst} (T1)
#     search   prove | bfs     (bfs = attack search with --stop-on-trace=BFS, T3)
#     heap     GHC heap cap, e.g. 8g or 56g (the runner always applies the T5 runtime flags)
#
# Output, under results/:
#   out/<job_id>.out    prover output
#   out/<job_id>.rts    GHC statistics (peak heap)
#   out/<job_id>.mem    memory curve: elapsed seconds, RSS in MB (prover plus Maude)
#   records.jsonl       one JSON object per run (appended)
#
# Environment: MAUDE (default "maude"), MAUDE_CYC (default "maude35"),
#              MEMSTEP seconds between memory samples (default 10),
#              THREADS GHC capabilities (default 4).
set -u
cd "$(dirname "$0")"
export LC_ALL=C.UTF-8 LANG=C.UTF-8
job=$1; tool=$2; file=$3; lemma=$4; heur=$5; search=$6; heap=$7; tmo=$8
case $tool in
  std) bin=tamarin-prover; mw=(--with-maude="${MAUDE:-maude}") ;;
  cyc) bin=tamarin-cyclic; mw=(--with-maude="${MAUDE_CYC:-maude35}") ;;
  *) echo "unknown tool: $tool" >&2; exit 2 ;;
esac
args=(--derivcheck-timeout=0 --prove="$lemma")
case $heur in
  default) ;;
  tactic) args+=("--heuristic={statefirst}") ;;
  *) args+=("--heuristic=$heur") ;;
esac
[ "$search" = bfs ] && args+=(--stop-on-trace=BFS)
mkdir -p results/out
out=results/out/$job.out; rts=results/out/$job.rts; mem=results/out/$job.mem
start=$(date +%s.%N)
# T5: fixed runtime flags. -A64m enlarges the allocation area (fewer minor
# collections), -qg disables the parallel collector (it costs memory and
# rarely helps Tamarin), -N sets the number of capabilities.
timeout -s INT -k 120 "$tmo" "$bin" "${mw[@]}" "${args[@]}" "$file" \
  +RTS -M"$heap" -A64m -qg -N"${THREADS:-4}" -s"$rts" -RTS > "$out" 2>&1 &
tpid=$!
: > "$mem"
(
  while kill -0 "$tpid" 2>/dev/null; do
    kb=0
    for p in $(pgrep -P "$tpid" 2>/dev/null) $(pgrep -P "$(pgrep -P "$tpid" 2>/dev/null | head -1)" 2>/dev/null); do
      kb=$((kb + $(ps -o rss= -p "$p" 2>/dev/null | awk '{s+=$1} END {print s+0}')))
    done
    now=$(date +%s.%N)
    printf '%d\t%d\n' "$(echo "$now - $start" | bc | cut -d. -f1)" "$((kb / 1024))" >> "$mem"
    sleep "${MEMSTEP:-10}"
  done
) &
spid=$!
wait "$tpid"; rc=$?
kill "$spid" 2>/dev/null; wait "$spid" 2>/dev/null
secs=$(echo "$(date +%s.%N) - $start" | bc)
python3 - "$job" "$tool" "$file" "$lemma" "$heur" "$search" "$heap" "$tmo" "$rc" "$secs" "$out" "$rts" "$mem" <<'PY'
import json, os, re, sys, hashlib, datetime
job, tool, file, lemma, heur, search, heap, tmo, rc, secs, out, rts, mem = sys.argv[1:]
text = open(out, errors='replace').read()
m = re.findall(r'^\s+' + re.escape(lemma) + r' \((all-traces|exists-trace)\): (verified|falsified[^\n(]*|analysis incomplete)[^\n]*?(?:\((\d+) steps\))?$', text, re.M)
verdict, steps, quant = None, None, None
if m:
    quant, v, s = m[-1]
    verdict = 'verified' if v.startswith('verified') else 'falsified' if v.startswith('falsified') else 'incomplete'
    steps = int(s) if s else None
elif 'Heap exhausted' in text or 'heap overflow' in text:
    verdict = 'HEAP'
elif int(rc) in (124, 130, 137):
    verdict = 'TIMEOUT' if int(rc) != 137 else 'KILLED'
else:
    verdict = 'ERROR'
peak = None
if os.path.exists(rts):
    mm = re.search(r'([\d,]+) bytes maximum residency', open(rts).read())
    if mm:
        peak = round(int(mm.group(1).replace(',', '')) / 2**20)
curve = []
if os.path.exists(mem):
    for line in open(mem):
        p = line.split()
        if len(p) == 2:
            curve.append((int(p[0]), int(p[1])))
rss_max = max((c[1] for c in curve), default=None)
# Growth of RSS in the first and in the last 30 % of the run (MB per
# minute). Used by the R3 rule: a lemma goes to the cloud only if the
# late growth is at most half of the early growth (the curve flattens).
def slope(seg):
    if len(seg) < 2 or seg[-1][0] == seg[0][0]:
        return None
    return round((seg[-1][1] - seg[0][1]) / ((seg[-1][0] - seg[0][0]) / 60), 1)
n = len(curve)
early = slope(curve[: max(2, int(0.3 * n))]) if n >= 4 else None
late = slope(curve[int(0.7 * n):]) if n >= 4 else None
rec = dict(job=job, time=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
           tool=tool, file=file, model=os.path.basename(file), sha256=hashlib.sha256(open(file, 'rb').read()).hexdigest(),
           lemma=lemma, quantifier=quant, heuristic=heur, search=search, heap_cap=heap,
           timeout_s=int(tmo), rc=int(rc), seconds=round(float(secs), 1), verdict=verdict,
           steps=steps, peak_heap_mb=peak, rss_max_mb=rss_max,
           rss_growth_early_mb_per_min=early, rss_growth_late_mb_per_min=late)
with open('results/records.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(f"{job:40s} {verdict:10s} {float(secs):9.1f}s heap={peak}MB rss={rss_max}MB steps={steps}")
PY
