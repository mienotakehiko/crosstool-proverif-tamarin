# Reveal follow-up of series V1

This follow-up asks both provers whether the reveal alternative of the authentication property is necessary in the one-time password family. It lies outside the validation plan, and its records enter none of the counts of series V1.

## Question

The authentication property of the family states that a login with the counter value `q` follows the release of password `q`, unless the seed of the thread leaked. In the LM-OTS and LMS families a private function hides the chain values, so a revealed seed gives the attacker no key material and the property never needs the alternative. The one-time password family declares its hash function public. The atomic scheduler therefore predicts that the property fails there without the alternative, with a reveal followed by a login as the shortest example ([`inputs/scheduler_prediction.txt`](inputs/scheduler_prediction.txt)). The follow-up puts this prediction to ProVerif and Tamarin.

## Inputs

The script [`make_reveal_inputs.py`](make_reveal_inputs.py) derives one input per member from the input of series V1. It keeps every line of the model part and replaces the property list by four properties.

| Property | Statement | Predicted outcome on the eight models |
| --- | --- | --- |
| `Auth` | An acceptance follows a release or a reveal. Property of V1 | No trace against the property |
| `Forge` | An acceptance without a release and without a reveal. Property of V1 | No such trace |
| `Auth_noreveal` | An acceptance follows a release | A trace against the property |
| `Forge_noreveal` | An acceptance without a release | Such a trace exists |

The table [`inputs/expected_reveal.tsv`](inputs/expected_reveal.tsv) states the predictions per model in the notation of series V1. Like the predictions of V1, it admits a missing outcome of ProVerif on the linear encoding and, for the two properties of V1, on the replicated encoding.

The prediction follows from the parameters of the family alone. The leak outputs the seed, and the attacker applies the public hash function to it, so a login without a release exists in the standard system and in every system that contains its traces. The two properties of V1 keep their predictions.

The directory [`sets/`](sets/) holds the two model sets that generator 0.1.3 writes for these inputs. Both side-condition reports contain no failed check. The script [`check_model_part.py`](check_model_part.py) removes the queries and the lemmas from the 16 model files and compares the rest with the files of series V1. The model parts are equal, so a difference between a verdict of this follow-up and a verdict of V1 can only stem from the property.

| File | Content |
| --- | --- |
| [`inputs/otp_n2_reveal.toml`](inputs/otp_n2_reveal.toml), [`inputs/otp_n3_reveal.toml`](inputs/otp_n3_reveal.toml) | The two inputs |
| [`inputs/expected_reveal.tsv`](inputs/expected_reveal.tsv) | Predicted outcomes |
| [`inputs/scheduler_prediction.txt`](inputs/scheduler_prediction.txt) | Output of `scheduler/lemma2/predict_reveal.py` for the two inputs |
| [`inputs/inputs.sha256`](inputs/inputs.sha256), [`models.sha256`](models.sha256) | Hashes of the inputs and of the files of the two model sets |

## Run

```bash
bash validation/V1-families/reveal_followup/run_reveal.sh WORKDIR
```

`WORKDIR` lies outside the repository and receives the raw outputs of the provers. The script regenerates the two model sets with generator 0.1.3 and compares them with the archived sets. It then runs both provers on the archived model files with the limits of series V1, which are 600 s per ProVerif file, 300 s per Tamarin lemma and a heap of 16g. A second pass repeats the jobs without a verdict under limits of 3,600 s and 7,200 s, and the option `--no-retry` omits it. The variables `PROVERIF` and `TAMARIN` name the binaries.

Each member contributes four ProVerif files with four queries each and four Tamarin theories with four lemmas each, which gives 64 verdict records. The runs use the runner `validation/common/run_set_monotonic.py` with its monotonic clock. The wrapper [`run_with_host_placeholder.py`](run_with_host_placeholder.py) starts the runner unchanged and lets it write the placeholder `host-redacted` in place of the host name, so the environment records keep the bytes of the runs.

## Records

The script copies the records of the runs into this directory and summarizes them.

| Path | Content |
| --- | --- |
| `sets/<set>/results/` | `pv_results.jsonl`, `tam_results.jsonl` and `environment.json` of the runner |
| `records/summary.txt` | Outcome of every property on every model, the comparison with series V1 and the conclusion |
| `records/xcheck.txt`, `records/xcheck.json` | Cross-check of the verdicts against the inclusion chain and the predictions |
| `records/raw-verdict-lines.tsv` | Verdict line and SHA-256 hash of the complete tool output of every job |

The raw outputs stay in `WORKDIR`. If a job has several records, the last one counts.

## Reading of the summary

The summary ends with one of three lines. `CONFIRMED` means that both tools decide all four properties on the standard system of both members with the predicted outcomes and that no verdict contradicts a prediction or the inclusion chain. `INCOMPLETE` names the verdicts that this conclusion still needs. `NOT CONFIRMED` names a contradiction, which is then a discrepancy to diagnose.

The two authentication properties together locate the cause. If `Auth` holds on a model, every acceptance without a release comes with a reveal of the same identity. If `Auth_noreveal` has a trace on the same model, such an acceptance exists. The reveal alternative is then necessary, and the leak is the cause.

## Result

The run started on 25 November 2026 at 23:30 UTC and used ProVerif 2.05, Tamarin 1.12.0 and Maude 3.5.1. All 64 jobs ended with a verdict under the first limits, so the second pass did not start.

| Property | ProVerif on four encodings per member | Tamarin on four theories per member | Outcome |
| --- | --- | --- | --- |
| `Auth` | `true` in 8 of 8 files | `verified` in 8 of 8 theories | No trace against the property |
| `Forge` | `true` in 8 of 8 files | `falsified` in 8 of 8 theories | No such trace |
| `Auth_noreveal` | `false` in 8 of 8 files | `falsified` in 8 of 8 theories | A trace against the property |
| `Forge_noreveal` | `false` in 8 of 8 files | `verified` in 8 of 8 theories | Such a trace exists |

All 64 outcomes equal the predictions, the cross-check finds no excluded pair, and both tools decide and agree on all eight properties on the standard system. The summary therefore ends with `CONFIRMED`. In both members the authentication property holds with the reveal alternative and fails without it, in both tools and on all eight models.

In ProVerif, `Auth` and `Forge` translate to one query text, and so do the two properties without the reveal. The 64 records therefore count verdicts per model and property name.

The two properties of V1 reproduce the outcomes of V1 in all 32 cells. The Tamarin binary of this run is another build of release 1.12.0 than the binary of the validation series. Its version record names the commit of the release tag and a build tree with uncommitted changes, whereas the records of the validation series name no revision. The 16 Tamarin proofs of the two unchanged properties have the same numbers of steps as in V1.

The result concerns two finite members of the family. It makes no statement about the LM-OTS and LMS families, in which a revealed seed gives the attacker no key material.

## Recompute

The following commands start no prover. The first two repeat the derivation of the inputs, the third repeats the prediction of the scheduler, the fourth compares the model parts with series V1, and the last one recomputes the cross-check and the summary from the stored records.

```bash
work=$(mktemp -d)
python3 -B validation/V1-families/reveal_followup/make_reveal_inputs.py "$work/inputs"
diff -r -x inputs.sha256 -x scheduler_prediction.txt "$work/inputs" validation/V1-families/reveal_followup/inputs
python3 -B scheduler/lemma2/predict_reveal.py --cimc cimc/v0.1.3 --checker scheduler/lemma2 \
    validation/V1-families/reveal_followup/inputs/otp_n2_reveal.toml \
    validation/V1-families/reveal_followup/inputs/otp_n3_reveal.toml \
    | diff - validation/V1-families/reveal_followup/inputs/scheduler_prediction.txt
python3 -B validation/V1-families/reveal_followup/check_model_part.py
python3 -B validation/V1-families/reveal_followup/summarize_reveal.py --no-write
```
