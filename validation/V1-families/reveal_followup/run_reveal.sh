#!/bin/bash
# Reveal follow-up of series V1: run both provers on the two model sets.
#
#   bash validation/V1-families/reveal_followup/run_reveal.sh WORKDIR [--no-retry]
#
# WORKDIR must lie outside the repository. It receives the raw outputs of the
# provers and the records of the runs. The script takes four steps.
#
#   1. It regenerates the two model sets with generator 0.1.3, compares them
#      with the archived sets and compares the model part with series V1.
#   2. It runs ProVerif and Tamarin on the archived model files with the first
#      limits of series V1: 600 s per ProVerif file, 300 s per Tamarin lemma
#      and a heap of 16g.
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
sets=(otp_n2_reveal otp_n3_reveal)

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

echo "== step 4: records, cross-check and summary"
for name in "${sets[@]}"; do
  mkdir -p "$here/sets/$name/results"
  for file in pv_results.jsonl tam_results.jsonl environment.json; do
    cp "$work/results/$name/$file" "$here/sets/$name/results/$file" || exit 1
  done
done
python3 -B "$here/summarize_reveal.py" --raw "$work/results"
status=$?
echo
echo "The records are under $here/sets/ and $here/records/."
echo "The raw outputs stay under $work/results/."
exit $status
