# Plan of the validation series

The validation series follow a plan that fixes inputs, tools and rules before the first prover run. The files of this directory are the hash lists of that plan. Each list names files of this repository by a relative path, so `sha256sum -c` checks it from this directory.

| File | Fixed before the runs |
| --- | --- |
| [`inputs.sha256`](inputs.sha256) | The 12 family inputs of V1 with their predictions and family table, and the 200 random inputs of V2 with their manifest |
| [`inputs_renamed.sha256`](inputs_renamed.sha256) | The 200 random inputs after the renaming for generator 0.1.2 |
| [`generator.txt`](generator.txt) | Version 0.1.2 of the generator with the hashes of its nine source files |
| [`mutations.sha256`](mutations.sha256) | The file `mutation.json` of each of the 32 sets of V4, which states the operator, the side and the hashes of the model files |
| [`labels.sha256`](labels.sha256) | The 41 labels of V3 before the predictions of the decision tree |

## Rules of the plan

The plan states one rule for each series.

| Series | Rule |
| --- | --- |
| V1 | The table `expected_e1.tsv` predicts the outcome of every property on every model of every family member. A verdict that contradicts a prediction counts as a finding |
| V2 | The seed 20261116 determines the 200 random inputs. The series predicts no verdict and counts the excluded pairs |
| V2, boundary | The table `expected.tsv` states for each probe whether the generator has to accept it |
| V3 | A label follows from the construction of an item. The hash of the labels precedes the predictions |
| V4 | The operators and the two signers determine the mutants. A mutant counts as detected if it shows an excluded pair that its control lacks |
| V5 | The four suites and their bounds determine the enumerations. Suite D has to show different sets |
| V7 | Among the screening jobs that ended at the time limit, the ten jobs with the smallest peak memory run again, at most two per model file, with four times the limit |

The [validation notes](../README.md) report the two deviations from the plan.
