#!/bin/bash
# Run every check of this repository that needs Python only.
#
#   bash scripts/check_all.sh
#
# The script stops at the first failing check. It starts no prover.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
python3 -B scripts/verify_evidence.py
python3 -B scripts/recompute_paper_numbers.py | tail -1
python3 -B scripts/recompute_validation_numbers.py --check validation/expected_counts.tsv
python3 -B scripts/check_model_hashes.py
python3 -B scripts/check_kudos_models.py
python3 -B corpus/recompute_morio.py
python3 -B exporter/index_regression.py
echo "All checks of scripts/check_all.sh passed."
