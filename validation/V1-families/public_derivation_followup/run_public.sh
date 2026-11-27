#!/bin/bash
# Public-derivation follow-up of series V1: run both provers on the two model sets.
#
#   bash validation/V1-families/public_derivation_followup/run_public.sh WORKDIR [--no-retry]
#
# WORKDIR must lie outside the repository. It receives the raw outputs of the
# provers and the records of the runs. The script takes four steps.
#
#   1. It checks the hashes of the inputs and of the model sets, regenerates
#      the two sets with generator 0.1.3, compares them with the archived sets
#      and compares them with the sets of series V1.
#   2. It runs ProVerif and Tamarin on the archived model files with the first
#      limits of series V1, which are 600 s per ProVerif file, 300 s per
#      Tamarin lemma and a heap of 16g.
#   3. It repeats the jobs without a verdict under the second limits of series
#      V1, 3,600 s and 7,200 s, unless --no-retry is given.
#   4. It copies the records into sets/<set>/results/ and writes the
#      cross-check and the summary into records/.
#
# The variables PROVERIF and TAMARIN name the binaries and default to proverif
# and tamarin-prover. A second call with the same WORKDIR skips the jobs that
# already have a verdict. The runner uses a monotonic clock.
set -u
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)
[ $# -ge 1 ] || { sed -n '2,22p' "$0"; exit 2; }
work=$(realpath -m -- "$1")
retry=yes
[ "${2:-}" = "--no-retry" ] && retry=no
case "$work/" in
  "$root"/*) echo "WORKDIR must lie outside the repository, because the inventory lists every file of the repository." >&2; exit 2 ;;
esac
mkdir -p "$work" || exit 2
proverif=${PROVERIF:-proverif}
tamarin=${TAMARIN:-tamarin-prover}
runner="$root/validation/common/run_set_monotonic.py"
sets=(lmots_w2m1_pub lms_h1w2_pub)

echo "== step 1: inputs and model sets"
(cd "$here/inputs" && sha256sum -c --quiet inputs.sha256) || { echo "The inputs differ from inputs.sha256." >&2; exit 1; }
(cd "$here" && sha256sum -c --quiet models.sha256) || { echo "The model sets differ from models.sha256." >&2; exit 1; }
for name in "${sets[@]}"; do
  regen="$work/regen/$name"
  rm -rf "$regen"; mkdir -p "$regen"
  ( cd "$root/cimc/v0.1.3" && python3 -B -m cimc "$here/inputs/$name.toml" "$regen" ) > "$work/regen/$name.log" 2>&1 \
    || { echo "Generator 0.1.3 fails on $name, see $work/regen/$name.log" >&2; exit 1; }
  cmp -s "$here/inputs/$name.toml" "$here/sets/$name/cim.toml" || { echo "cim.toml of $name differs from the input." >&2; exit 1; }
  for path in "$regen"/*; do
    cmp -s "$path" "$here/sets/$name/$(basename "$path")" \
      || { echo "Regenerated file differs from the archived file: $name/$(basename "$path")" >&2; exit 1; }
  done
done
python3 -B "$here/check_model_part.py" || exit 1
echo "The regenerated sets equal the archived sets."

# Start record without host name or path: time, commit of the repository and state of the tracked files.
{
  echo "start_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repository_commit: $(git -C "$root" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "tracked_files_modified: $(git -C "$root" status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')"
  echo "inputs_sha256: $(sha256sum "$here/inputs/inputs.sha256" | cut -d' ' -f1)"
  echo "models_sha256: $(sha256sum "$here/models.sha256" | cut -d' ' -f1)"
} >> "$work/run-info.txt"

run_pass() {  # arguments: limits and options of the runner
  for name in "${sets[@]}"; do
    python3 -B "$here/run_with_host_placeholder.py" "$runner" "$here/sets/$name" --out "$work/results/$name" \
      --proverif "$proverif" --tamarin "$tamarin" --heap 16g "$@" || return $?
  done
}

unresolved() {  # number of jobs whose last record holds no verdict
  python3 -B - "$work/results" "${sets[@]}" <<'PY'
import json, os, sys
final = {"true", "false", "cannot", "verified", "falsified"}
count = 0
for name in sys.argv[2:]:
    for file, key in (("pv_results.jsonl", "query"), ("tam_results.jsonl", "lemma")):
        last = {}
        path = os.path.join(sys.argv[1], name, file)
        if os.path.exists(path):
            for line in open(path):
                if line.strip():
                    record = json.loads(line)
                    last[(record["model"], record[key])] = record["verdict"]
        count += sum(1 for verdict in last.values() if verdict not in final)
print(count)
PY
}

echo "== step 2: first limits (600 s per ProVerif file, 300 s per Tamarin lemma, heap 16g)"
run_pass --pv-timeout 600 --tm-timeout 300 || { echo "The runner stopped. Check the two binaries." >&2; exit 2; }
open_jobs=$(unresolved)
echo "jobs without a verdict after the first limits: $open_jobs"

if [ "$open_jobs" != 0 ] && [ "$retry" = yes ]; then
  echo "== step 3: second limits (3,600 s per ProVerif file, 7,200 s per Tamarin lemma, heap 16g)"
  run_pass --pv-timeout 3600 --tm-timeout 7200 --retry-unresolved || exit 2
  echo "jobs without a verdict after the second limits: $(unresolved)"
fi
echo "end_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$work/run-info.txt"

echo "== step 4: records, cross-check and summary"
for name in "${sets[@]}"; do
  mkdir -p "$here/sets/$name/results"
  for file in pv_results.jsonl tam_results.jsonl environment.json; do
    cp "$work/results/$name/$file" "$here/sets/$name/results/$file" || exit 1
  done
done
mkdir -p "$here/records"
cp "$work/run-info.txt" "$here/records/run-info.txt" || exit 1
python3 -B "$here/summarize_public.py" --raw "$work/results"
status=$?
echo
echo "The records are under $here/sets/ and $here/records/."
echo "The raw outputs stay under $work/results/."
exit $status
