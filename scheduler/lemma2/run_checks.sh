#!/bin/bash
# Bounded comparison of the two schedulers of the unrolled scheduler lemma (Lemma 2).
#
#   bash scheduler/lemma2/run_checks.sh [WORKDIR]
#
# WORKDIR receives the regenerated inputs and defaults to a new temporary directory.
# CIMC_DIR names the directory that holds the package cimc and defaults to cimc/v0.1.0.
# The run needs Python 3.11 or later, starts no prover and takes a few minutes.
#
#   suite A  one thread, words of at most four events. The two signer models,
#            two controls and 200 random models (seed 20261116).
#   suite B  one thread, words of at most three events. The twelve family models.
#   suite C  two threads, words of at most three events. Five models of suite A.
#   suite D  four models that violate a condition of the lemma. The sets must differ.
set -u
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
work=${1:-$(mktemp -d)}; mkdir -p "$work"
cimc_dir=$(cd "${CIMC_DIR:-$root/cimc/v0.1.0}" && pwd)
signers=$root/cim/signers
probes=$root/validation/V2-boundary/probes
python3 -B "$root/validation/V2-random/gen_small_cims.py" "$work/random" --count 200 --seed 20261116 \
  --verify "$root/validation/V2-random/manifest_20261116.tsv" | tail -1 || exit 1
python3 -B "$root/validation/V1-families/make_family.py" "$work/family" > /dev/null
check() { python3 -B "$here/unrolled_check.py" --cimc "$cimc_dir" "$@" | tail -1; }
status=0
echo "suite A"; check --threads 1 --length 4 "$signers/lmots.toml" "$signers/lms_s2.toml" \
  "$probes/b01_control_inputs.toml" "$probes/b02_control_silent.toml" "$work"/random/*.toml || status=1
echo "suite B"; check --threads 1 --length 3 "$work"/family/*.toml || status=1
echo "suite C"; check --threads 2 --length 3 "$signers/lmots.toml" "$signers/lms_s2.toml" \
  "$probes/b01_control_inputs.toml" "$probes/b02_control_silent.toml" "$work/random/r001.toml" || status=1
echo "suite D"; check --threads 1 --length 4 --expect-difference B03,B04,B05,B08 "$probes/b03_overlap.toml" \
  "$probes/b04_two_silent.toml" "$probes/b05_mixed_dispatch.toml" "$probes/b08_unpublished_identity.toml" || status=1
exit $status
