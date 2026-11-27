# Public-derivation follow-up of series V1

This follow-up asks both provers whether the unforgeability results of the signers survive a public derivation function and whether the reveal alternative then becomes necessary. It lies outside the validation plan, and its records enter none of the counts of series V1.

## Question

The LM-OTS and LMS families of series V1 derive the starting values of their chains with the function `prf`, which their inputs declare private. An attacker who holds the seed cannot apply a private function. A revealed seed therefore yields no chain value, and the unforgeability property never needs its reveal alternative in these models. The pseudorandom key generation that RFC 8554 describes applies a hash function to the seed and to public values, so a public function is the closer model.

The follow-up declares `prf` public in two members, LM-OTS(2,1) and LMS(1,2), and changes nothing else in the model part. It asks two questions.

1. Do the properties of series V1 keep their outcomes on all eight models?
2. Does unforgeability hold with the reveal alternative and fail without it?

## Inputs

The script [`make_public_inputs.py`](make_public_inputs.py) derives one input per member from the input of series V1. It removes the attribute `private` from the declaration of `prf`, keeps every other line and appends two properties.

| Member | New property | Statement | Predicted outcome on the eight models |
| --- | --- | --- | --- |
| LM-OTS(2,1) | `LS1_unforge_noreveal` | An acceptance follows a signing event | A trace against the property |
| LM-OTS(2,1) | `forge_noreveal` | An acceptance without a signing event | Such a trace exists |
| LMS(1,2) | `LS1_noreveal` | An acceptance follows a signing event | A trace against the property |
| LMS(1,2) | `LS3_forge_noreveal` | An acceptance without a signing event | Such a trace exists |

The table [`inputs/expected_public.tsv`](inputs/expected_public.tsv) states the predictions per model in the notation of series V1. The properties of V1 keep the predictions of V1, because every use of a revealed seed comes with the reveal event, which these properties name. The new properties have a trace on every model. The leak outputs the seed, the attacker applies the public function to it and forges a signature without a signing step, so the trace involves no state reuse. Like the predictions of V1, the table admits a missing outcome of ProVerif on the linear encoding.

The atomic scheduler gives the same prediction without a prover. The file [`inputs/scheduler_prediction.txt`](inputs/scheduler_prediction.txt) holds the output of `scheduler/lemma2/predict_reveal.py` for the two inputs of V1 and the two inputs of this follow-up. With the private function, the enumeration finds no acceptance without its signing event. With the public function, it finds an acceptance that follows a reveal and no signing event.

The directory [`sets/`](sets/) holds the two model sets that generator 0.1.3 writes for these inputs. Both side-condition reports contain no failed check. The script [`check_model_part.py`](check_model_part.py) compares the 16 model files with the files of series V1. Outside the first line, each file differs from its counterpart by the declaration of `prf` and by two further queries or lemmas, and every query or lemma of V1 occurs unchanged. A difference between a verdict of this follow-up and a verdict of V1 on a property of V1 can therefore only stem from the declaration.

| File | Content |
| --- | --- |
| [`inputs/lmots_w2m1_pub.toml`](inputs/lmots_w2m1_pub.toml), [`inputs/lms_h1w2_pub.toml`](inputs/lms_h1w2_pub.toml) | The two inputs |
| [`inputs/expected_public.tsv`](inputs/expected_public.tsv) | Predicted outcomes of the 92 records |
| [`inputs/scheduler_prediction.txt`](inputs/scheduler_prediction.txt) | Prediction of the atomic scheduler |
| [`inputs/inputs.sha256`](inputs/inputs.sha256), [`models.sha256`](models.sha256) | Hashes of the inputs and of the files of the two model sets |

## Run

```bash
bash validation/V1-families/public_derivation_followup/run_public.sh WORKDIR
```

`WORKDIR` lies outside the repository and receives the raw outputs of the provers. The script checks the hashes, regenerates the two model sets with generator 0.1.3 and compares them with the archived sets and with the sets of series V1. It then runs both provers on the archived model files with the limits of series V1, which are 600 s per ProVerif file, 300 s per Tamarin lemma and a heap of 16g. A second pass repeats the jobs without a verdict under limits of 3,600 s and 7,200 s, and the option `--no-retry` omits it. The variables `PROVERIF` and `TAMARIN` name the binaries.

LM-OTS(2,1) contributes four ProVerif files with five queries each and four Tamarin theories with five lemmas each. LMS(1,2) contributes four ProVerif files with six queries each and four Tamarin theories with seven lemmas each, because the property with a misuse exception has no ProVerif query. The two members thus yield 92 verdict records. The runs use the runner `validation/common/run_set_monotonic.py` with its monotonic clock. The wrapper [`run_with_host_placeholder.py`](run_with_host_placeholder.py) starts the runner unchanged and lets it write the placeholder `host-redacted` in place of the host name.

## Records

The script copies the records of the runs into this directory and summarizes them.

| Path | Content |
| --- | --- |
| `sets/<set>/results/` | `pv_results.jsonl`, `tam_results.jsonl` and `environment.json` of the runner |
| `records/summary.txt` | Outcome of every property on every model, the comparison with series V1 and the conclusion |
| `records/xcheck.txt`, `records/xcheck.json` | Cross-check of the verdicts against the inclusion chain and the predictions |
| `records/raw-verdict-lines.tsv` | Verdict line and SHA-256 hash of the complete tool output of every job |
| `records/run-info.txt` | Start and end time of each call, the commit of the repository and the hashes of the two hash lists |

The raw outputs stay in `WORKDIR`. If a job has several records, the last one counts.

## Result

The run started on 26 November 2026 at 10:00 UTC on commit `f799ea3` of this repository and used ProVerif 2.05, Tamarin 1.12.0 and Maude 3.5.1. The Tamarin binary is the one of the reveal follow-up, a build of release 1.12.0 whose version record names the commit of the release tag and a build tree with uncommitted changes. Of the 92 jobs, 89 ended under the first limits. Three Tamarin lemmas of LMS(1,2) reached the limit of 300 s, and the second pass decided them in 541.13 s, 555.29 s and 325.55 s.

| Property on the standard system | ProVerif on `PV_U` | Tamarin on `T_base` | Outcome |
| --- | --- | --- | --- |
| `LS1_unforge` and `LS1`, with the reveal alternative | `true` | `verified` | No trace against the property |
| `forge` and `LS3_forge`, with the reveal alternative | `true` | `falsified` | No such trace |
| `LS1_unforge_noreveal` and `LS1_noreveal` | `false` | `falsified` | A trace against the property |
| `forge_noreveal` and `LS3_forge_noreveal` | `false` | `verified` | Such a trace exists |

The table holds for both members. The two new properties of each member have a trace in all 32 cells of model and property.

Of the 92 records, 87 carry a verdict. The other five are the answer `cannot be proved` of ProVerif on the linear encoding for the properties `LS1_unforge`, `forge`, `LS4_pure`, `LS1` and `LS3_forge`. The predictions admit this answer, and series V1 shows it in the same five cells. No outcome contradicts its prediction, the cross-check finds no excluded pair, and both tools decide and agree on 11 properties on the standard system. The twelfth property, `LS4`, has no ProVerif query. The summary therefore ends with `CONFIRMED`.

The properties of V1 keep the outcome of V1 in all 55 cells in which both runs hold an outcome. Of the 32 Tamarin results of these properties, 28 keep their number of steps. The other four are the proofs of unforgeability and of its reachability form on the standard system. They grow from 23 to 39 steps for LM-OTS(2,1) and from 74 to 580 steps for LMS(1,2), because the attacker gains the function `prf`.

With a public derivation function, the unforgeability of these two signers therefore needs its reveal alternative. The result concerns two small members. The other members of the two families, the random models and the hand-written theories have no run with a public derivation function.

## Reading of the summary

The summary ends with one of three lines. `CONFIRMED` means that both tools decide unforgeability and its reachability form on the standard system of both members, with and without the reveal alternative and with the predicted outcomes, that no verdict contradicts a prediction or the inclusion chain, and that every comparable outcome of a property of V1 equals the outcome of V1. `INCOMPLETE` names the verdicts that this conclusion still needs. `NOT CONFIRMED` names a contradiction, which is then a discrepancy to diagnose.

The comparison with V1 counts the cells in which both runs hold an outcome. Proof sizes may differ from V1, because the attacker gains the function `prf`, and the summary reports how many Tamarin results keep their number of steps.
