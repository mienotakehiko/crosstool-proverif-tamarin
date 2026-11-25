# Series M, mutation of generated encodings

Series M seeds faults into the generated ProVerif encodings of the two signers and asks whether the comparison with Tamarin exposes them.

| Cohort | Cases | Outcome |
| --- | --- | --- |
| [Pilot of 28 October 2026](historical/oct28/pilot/) | 3 mutants and 1 unchanged control | 2 of 3 mutants detected, no difference on the control |
| [Main experiment of 29 October 2026](historical/oct29/mutation_extension_20261029/) | 10 operators on each of the 2 signers and 2 unchanged controls | 12 of 20 mutants detected, no difference on the controls |
| [Frozen re-evaluation of 11 November 2026](frozen_20261111/) | the same 20 mutants with a fixed, wider set of queries | 20 of 20 detected with the audit queries, 18 of 20 with the ordinary queries alone |

## Main experiment

The file `results.json` keeps the first run, in which Tamarin reached its time limit on the 11 LMS cases. All 11 cases share one Tamarin input with the same SHA-256 hash, so one reference run of that input completes them, and `results_completed_reference.json` holds the completed results. The reference run is in [`historical/oct29/shared_tamarin_reference/`](historical/oct29/shared_tamarin_reference/). The case `unpublished_identity` is an auxiliary case outside the counts of 20 mutants and 2 controls.

## Frozen re-evaluation

The file `freeze.json` fixes the 68 input files and decision tree 1.1 before the run, and `execution_started.json` and `execution_finished.json` record its start and end. The run consists of 66 ProVerif invocations with 231 formulas and 14 Tamarin invocations. The file `results.json` holds the normalized verdict of every formula, and `mutation_assessment.json` holds the detection of each mutant with and without the audit queries.

The re-evaluation uses the mutants of the main experiment and a wider set of observations. Its counts describe their own cohort and replace no count of the main experiment.

## Checks

```bash
python3 -B scripts/verify_evidence.py
python3 -B scripts/recompute_paper_numbers.py
```

The first command compares every model with the hash in its record, every log with the original hash that its record cites, and the frozen inputs with `freeze.json`. The second command recomputes the detection counts of the three cohorts. The scripts in the cohort directories are the scripts of the original runs and expect the working directories of those runs.
