# cimc 0.1.2 independent guarded copy (2026-11-11)

This directory is a full copy of the original cimc tree. Only this copy
is modified. `out/` and `tests/data/` remain byte-identical historical
evidence, including their old version headers. New outputs are under
`audit_0_1_2/generated/`, never written over `out/`.

Version 0.1.2 conservatively rejects backend-reserved identifiers,
unbound equality subterms, same-pattern equality references to newly
bound variables, unbound body terms, and scalar equality input patterns.
It does NOT implement constructor decomposition or automatic alpha-renaming.
Unsupported models are refused by BOTH backend APIs and by the CLI before
creating an output directory. The new report entries are `Hygiene`,
`Binding`, and `PatternSupported`. Other existing check failures retain
the historical generate-and-report behavior.

The `x` constructor-capture counterexample is rejected, not repaired into
a supposedly equivalent supported model. See `FIX_REPORT_ja.md` and
`manuscript_correction_en.md`. This is not a proof of full translation
correctness and does not remove the manuscript's simulation assumptions.

Reproduce sequentially: `PYTHONDONTWRITEBYTECODE=1 python -B audit_fix.py`.
The audit uses 750 MiB child address-space ceilings, one Tamarin core,
450 MiB Tamarin heap limits, and per-process deadlines. Full Tamarin
security proofs are not rerun. Docker comparison is outside this task.

The original kit instructions below are preserved as historical context;
do not follow their large-memory Tamarin settings in this sandbox.

## Historical kit instructions

cimc compiles one Common Iterative Model (CIM, a TOML file) into
four ProVerif encodings and four Tamarin variants, and checks the side
conditions of Theorem 1 on its own output.

| Output | Meaning |
|---|---|
| `*_PV_U<n>.pv` | state unrolled n times (Theorem 1(a), (e)) |
| `*_PV_Urb<n>.pv` | unrolled, with one rollback on request (Theorem 1(d)) |
| `*_PV_lin.pv` | private state channel, one `out` per step (Theorem 1(b)) |
| `*_PV_rep.pv` | private state channel, `!out` per step (Theorem 1(c)) |
| `*_T_base.spthy` | linear state fact St |
| `*_T_cl1.spthy` | + rule Clone, restriction OneMisuse |
| `*_T_rb1.spthy` | + snapshots, rule Rollback, OneMisuse |
| `*_T_omega.spthy` | persistent state fact !St |
| `*_checks.txt` | side conditions: OK / FAIL / BY-CONSTRUCTION |
| `*_manifest.json` | SHA-256 of every output and of the CIM |

Requirements: Python 3.11 or later (tomllib), ProVerif 2.05, Tamarin
1.12.0, bc. Always `export LC_ALL=C.UTF-8`.

## Step 1: regenerate and compare (5 minutes)

```bash
tar xzf pv_kit_v1.tar.gz && cd cimc
export LC_ALL=C.UTF-8
python3 -m cimc cims/lms_s2.toml regen
diff -r -x '*.out' -x '*.log' -x '*.sh' regen out/lms_s2 && echo SAME
```
Expected: the check table with no FAIL, `wrote 9 files`, and `SAME`
(the generator is deterministic).

## Step 2: ProVerif (1 minute)

```bash
./run_pv.sh out/lms_s2 3600
python3 tests/compare.py
```
Expected: `9/9 as expected`.

## Step 3: Tamarin on the generated variants (64 GB machine)

Do not run this at the same time as the P1-P4 phases of kit v3.

```bash
nohup env HEAP=56g TMO=3600 ./run_tam_generated.sh out/lms_s2 > tg1.log 2>&1 &
# after it finishes, the second pass without the 1 h limit:
nohup env HEAP=56g TMO=86400 ./run_tam_generated.sh out/lms_s2 > tg2.log 2>&1 &
```
Expected: the verdicts in `tests/expected_tam_lms_s2.tsv`. A different
verdict is a finding, not an error; send it back unchanged. The step
counts may differ from the hand-written models (the rule set is the same,
but the generated model names numerals as constants).

## What to send back

```bash
tar czf pvkit_results_$(hostname)_$(date +%Y%m%d).tar.gz results tg1.log tg2.log
```
`results/pv_results.jsonl`, `results/tam_generated.tsv`; the `*.out`
files only on request.


## Changes in kit v2 (2026-10-14)

- New CIM `cims/lmots.toml` (LM-OTS, w = 2, p = 2) with generated models in `out/lmots/`.
- `run_tam_generated.sh` now samples RSS every `MEMSTEP` seconds (default 10) and
  writes `results/tam_generated.jsonl` with the RSS growth in the first and last 30 %
  of each run; the memory curve is kept in `results/tamout/*.mem`.
- `python3 -m cimc.al_assign` computes the Achievement Levels and the diagnosis
  (tree version 1.0) from the result files.
- Tests: `python3 tests/test_al.py` (33 unit tests), `python3 tests/regress_al.py`.

### Additional run for kit v2

```
./run_pv.sh out/lmots 3600 && python3 tests/compare.py          # expect 21/21 as expected
HEAP=56g TMO=86400 ./run_tam_generated.sh out/lmots              # minutes
HEAP=56g TMO=86400 ./run_tam_generated.sh out/lms_s2             # long (cl1); not together with kit v3 P1-P4
python3 -m cimc.al_assign cims/lms_s2.toml out/lms_s2/LMS_S2_checks.txt -o results/al_lms_s2 \
    --pv results/pv_results.jsonl --tm results/tam_generated.jsonl
```

Send back `results/` (all files).
