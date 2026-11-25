# Validation series V1 to V7

This directory holds the plan, the scripts, the inputs and the records of the validation series of the paper. ProVerif 2.05 and Tamarin 1.12.0 produced every verdict. The commands on this page compare records and start no prover, and the [reproduction guide](../docs/REPRODUCTION.md) shows the prover runs.

| Directory | Series | Content |
| --- | --- | --- |
| [`plan/`](plan/) | all | Hash lists that fix the inputs, the generator, the mutants and the labels before the runs |
| [`common/`](common/) | all | Runner of one model set, cross-check of verdict pairs and regeneration check |
| [`V1-families/`](V1-families/) | V1 | 12 members of the LM-OTS, LMS and one-time password families with their predictions |
| [`V2-random/`](V2-random/) | V2 | 200 random CIMs from the seed 20261116 |
| [`V2-boundary/`](V2-boundary/) | V2 | 12 boundary probes and 4 pair-shaped probes ([notes](V2-boundary/README.md)) |
| [`V3-diagnosis/`](V3-diagnosis/) | V3 | 41 sealed labels and the predictions of decision tree 1.1 |
| [`V4-mutation/`](V4-mutation/) | V4 | 30 mutants and 2 controls of the two signers, and 94 input mutants |
| [`V6-exporter/`](V6-exporter/) | V6 | Two exporter probes on the upstream head of Tamarin |
| [`V7-time-limit/`](V7-time-limit/) | V7 | Ten screening jobs with a fourfold time limit |

Series V5 is the bounded enumeration of the schedulers of Lemma 2 in [`scheduler/lemma2/`](../scheduler/lemma2/).

## Model sets and records

A model set is one directory with the eight generated models, the side-condition report, the manifest, the input `cim.toml` and the directory `results/`. The file `results/pv_results.jsonl` holds one record per ProVerif query, `results/tam_results.jsonl` holds one record per Tamarin lemma, and `results/environment.json` states the host, the limits, the tool versions and the hash of the runner. If a job has several records, the last one counts.

The script [`common/xcheck.py`](common/xcheck.py) reads the records of a set. It reports every excluded pair, that is, a property that holds on one model and has a trace on a second model whose traces all belong to the first. It also counts the properties on which both tools agree on the standard system T.

## Recompute the counts

```bash
python3 -B scripts/recompute_validation_numbers.py --check validation/expected_counts.tsv
python3 -B validation/common/regen_check.py --cimc cimc/v0.1.2 \
    validation/V1-families/sets validation/V2-random/sets validation/V2-boundary/sets/controls \
    validation/V4-mutation/sets/LMOTS__control validation/V4-mutation/sets/LMS_S2__control
(cd validation/plan && sha256sum -c --quiet inputs.sha256 inputs_renamed.sha256 mutations.sha256 labels.sha256)
```

The first command recomputes 527 counts of the series V1 to V4 and V7, including the Achievement Levels, and compares them with [`expected_counts.tsv`](expected_counts.tsv). The second command regenerates the 1,728 model files of the 216 model sets without a failed side condition and compares them with the archived files. Generator 0.1.3 regenerates the same files, because the comparison skips the line that names the version. The third command checks the fixed inputs.

## Results by series

| Series | Records | Result |
| --- | --- | --- |
| V1 | 372 records on 50 properties, 322 with a verdict | No excluded pair. Both tools agree on all 43 properties that both decide on T. The verdicts confirm 346 of 372 predicted cells and contradict none |
| V2, random | 8,192 records on 1,024 properties, 7,986 with a verdict | No excluded pair. Both tools agree on all 1,024 properties on T |
| V2, boundary | 12 probes | Generator 0.1.2 refuses all ten probes outside its fragment. The [boundary notes](V2-boundary/README.md) report the prover runs |
| V3 | 41 items | Decision tree 1.1 assigns the labeled cause to all 41 items, which cover three of the eight causes |
| V4 | 972 records in 32 sets, and 94 input mutants | The comparison detects 12 of 26 encoding mutants and none of 4 property mutants. No verdict changes for the other mutants. The generator refuses 87 of 94 input mutants |
| V6 | 2 models | Both exports of the upstream exporter admit a witness of the forbidden event that native Tamarin excludes, and one correction per export removes it |
| V7 | 10 jobs | All ten jobs reach the fourfold time limit of 14,400 s without a verdict |

The two unchanged controls of V4, `LMOTS__control` and `LMS_S2__control`, are the rerun of series G with generator 0.1.2. They hold 28 ProVerif and 32 Tamarin verdicts on the two signers.

The seven input mutants that the generator accepts all come from the operator `literal_numeral`. This result led to the literal check of generator 0.1.3.

## Scripts of the series

| Script | Purpose |
| --- | --- |
| `common/run_family.sh`, `common/run_set.py` | Compile the inputs of a directory, run both provers on each model set and record every verdict |
| `common/run_set_monotonic.py` | The same runner with a monotonic clock, which the LMS family and the two control probes used |
| `V1-families/make_family.py` | Write the 12 family inputs and their predictions |
| `V1-families/summarize_e1.py` | Summarize times, proof steps and memory per family member |
| `V2-random/gen_small_cims.py` | Write the 200 random inputs from the seed and verify them against the manifest |
| `V2-boundary/run_boundary.py` | Compile the probes and, on request, run both provers on them |
| `V3-diagnosis/build_labels.py`, `predict.py`, `score_diagnosis.py` | Build the labels, collect the predictions and score them |
| `V3-diagnosis/make_resource_runs.py`, `e7_items.py` | Prepare runs under chosen resource limits and derive items from the reruns of V7 |
| `V4-mutation/mutate.py`, `mutate_cim.py`, `score.py` | Write the mutants of the models and of the inputs and score the mutants |
| `V6-exporter/compare_runs.py` | Compare two result tables of the translated route |
| `V7-time-limit/select_jobs.py` | Select the ten jobs by the fixed rule |

Each script states its usage at its head. The directory names of the series carry the letter V, and the scripts keep the option names `--e1` and `--e4` and the job prefix `E7x4_` of the runs.

The following commands regenerate the fixed inputs and the sealed labels in a temporary directory. The label step read the five LM-OTS sets and the 32 sets of V4.

```bash
work=$(mktemp -d)
python3 -B validation/V1-families/make_family.py "$work/family"
diff -r "$work/family" validation/V1-families/inputs/fixed
python3 -B validation/V2-random/gen_small_cims.py "$work/random" --verify validation/V2-random/manifest_20261116.tsv
mkdir "$work/lmots" && cp -r validation/V1-families/sets/lmots_* "$work/lmots/"
python3 -B validation/V3-diagnosis/build_labels.py --out "$work/labels.tsv" --e1 "$work/lmots" \
    --expected validation/V1-families/inputs/fixed/expected_e1.tsv --e4 validation/V4-mutation/sets
diff "$work/labels.tsv" validation/V3-diagnosis/labels.tsv
```

## Deviations from the plan

The [plan notes](plan/README.md) state what the hash lists fix. Two deviations occurred.

The plan assumed generator 0.1.0. Generator 0.1.2 reserves the identifiers `s0`, `c` and `x` and refuses an input pattern that consists of one constant. It therefore refused 7 of the 12 inputs of V1, which [`V1-families/refused_by_0.1.2.txt`](V1-families/refused_by_0.1.2.txt) lists, and both control probes of V2, and 161 of the 200 random inputs contain `x`. The runs use renamed inputs. The LMS family renames `s0` to `sibling0`, the one-time password family renames `c` to `rel_count`, the random models rename `x` to `recv_value`, and the two control probes use the pair-shaped input `tup('ctl', ...)`. The predictions and the seed stay unchanged. Each series keeps the fixed inputs under `inputs/fixed/` and the inputs of the runs under `inputs/renamed/`.

No run produced items for five of the eight causes of V3. The directory [`V3-diagnosis/resource-runs/`](V3-diagnosis/resource-runs/) holds the run under a heap limit of 64 MB that was to produce items for the cause TM-res. All eight of its jobs ended with a verdict, so the run yields no item.

## Clock

The runner `common/run_set.py` takes durations from the wall clock. The clock of the host moved during the runs, so the durations of these records are approximate. A negative duration appears in 104 records of V1, V2 and V4 and in one record of the pair-shaped probes. The runner `common/run_set_monotonic.py` differs from it only in the clock.
