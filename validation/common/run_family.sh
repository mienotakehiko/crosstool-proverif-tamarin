#!/bin/bash
# Compile every CIM of a directory, run both provers on each generated set and
# cross-check the verdicts.
#
#   bash run_family.sh CIMDIR SETROOT [options of run_set.py]
#   bash run_family.sh inputs sets --pv-timeout 600 --tm-timeout 3600 --heap 16g
#
# CIMC_DIR names the directory that contains the package cimc (default
# cimc/v0.1.2 of this repository). The script writes the following files.
#
#   SETROOT/<name>/            generated models, cim.toml (a copy of the input),
#                              _gen.log and results/
#   SETROOT/<name>/_rejected   present if the generator refused the input
#   SETROOT/rejected.txt       names of the refused inputs
#   SETROOT/xcheck.txt and SETROOT/xcheck.json
#
# A second call continues an interrupted series and skips finished jobs.
# The provers never run on a refused input.
set -u
here=$(cd "$(dirname "$0")" && pwd)
cimdir=$(cd "${1:?CIMDIR}" && pwd); mkdir -p "${2:?SETROOT}"; setroot=$(cd "$2" && pwd); shift 2
cimc_dir=${CIMC_DIR:-$here/../../cimc/v0.1.2}
: > "$setroot/rejected.txt"
sets=()
for toml in "$cimdir"/*.toml; do
  name=$(basename "$toml" .toml); out="$setroot/$name"; mkdir -p "$out"
  if [ ! -f "$out/_gen.log" ]; then
    cp "$toml" "$out/cim.toml"
    ( cd "$cimc_dir" && python3 -B -m cimc "$toml" "$out" ) > "$out/_gen.log" 2>&1 || touch "$out/_rejected"
  fi
  if [ -f "$out/_rejected" ]; then echo "$name" >> "$setroot/rejected.txt"; continue; fi
  python3 -B "$here/run_set.py" "$out" "$@"
  sets+=("$out")
done
expected=(); [ -f "$cimdir/expected_e1.tsv" ] && expected=(--expected "$cimdir/expected_e1.tsv")
if [ ${#sets[@]} -gt 0 ]; then
  python3 -B "$here/xcheck.py" "${sets[@]}" ${expected[@]+"${expected[@]}"} --json "$setroot/xcheck.json" | tee "$setroot/xcheck.txt"
fi
echo "refused inputs: $(wc -l < "$setroot/rejected.txt")"
