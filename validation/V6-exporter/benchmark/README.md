# Benchmark of the translation artifact under two exporter builds (series V6)

This comparison runs the benchmark of the translation artifact of Morio, Ivanov and Künnemann twice, with the unmodified exporter B0 and with the repaired exporter B2 of the [exporter study](../../../exporter/README.md). It asks whether the two repairs change an outcome on theories that the regression set of series X1 does not contain. The comparison is exploratory and states no prediction.

## Setup

Both runs use the evaluation scripts and the container image `msr-to-pv-eval:ccs26` of the artifact. The two images differ in the exporter binary only. The lists [`provenance/b0/files.sha256`](provenance/b0/files.sha256) and [`provenance/b2/files.sha256`](provenance/b2/files.sha256) name six files of each image, and the five others, among them ProVerif, Maude, native Tamarin and the evaluator, are equal. Each run translates the 121 theories of the artifact, whose hashes [`provenance/models.sha256`](provenance/models.sha256) lists, and passes each of the 566 pairs of theory and lemma to ProVerif with a limit of 300 s and 8,192 MB. The published run of the artifact allowed more time and memory. Its records are in [`corpus/morio/eval-results.jsonl`](../../../corpus/morio/eval-results.jsonl), and the file [`provenance/config.json`](provenance/config.json) states their hash.

## Files

| Path | Content |
| --- | --- |
| [`B0/rows.jsonl`](B0/rows.jsonl), [`B2/rows.jsonl`](B2/rows.jsonl) | One row per pair with the outcome of ProVerif, the error message, the time and the memory |
| [`comparison/`](comparison/) | Output of the script of the run, with the paired outcomes, the changed pairs, the transitions and the two tables for `compare_runs.py` |
| [`inventory/inventory.tsv`](inventory/inventory.tsv) | The 566 pairs with their index in the published records |
| [`provenance/config.json`](provenance/config.json) | Limits, image identifiers and hashes of the scripts of the run |
| [`provenance/b0/`](provenance/b0/), [`provenance/b2/`](provenance/b2/) | Image identifier and hashes of six files of each image |
| [`provenance/models.sha256`](provenance/models.sha256) | Hashes of the 121 theories |
| [`provenance/pair_report.py`](provenance/pair_report.py) | Script of the run that wrote `comparison/` |
| [`summarize_benchmark.py`](summarize_benchmark.py) | Recomputes the counts of this page from the records |
| [`summary.txt`](summary.txt) | Output of that script with the option `--examples` |

## Result

| Outcome | B0 | B2 |
| --- | --- | --- |
| `true` | 254 | 254 |
| `false` | 54 | 54 |
| Memory exhausted | 133 | 133 |
| Time limit | 34 | 30 |
| Error of ProVerif | 43 | 48 |
| No result | 48 | 47 |

Both builds return a definitive outcome for the same 308 pairs, and the two outcomes are equal on all of them. All 308 outcomes also equal the outcome of the translated route in the published records, which decide five further pairs after 1,253 s to 4,164 s. Of the other 258 pairs, 253 end in the same class under both builds.

Five pairs change. They are the five lemmas of `examples/related_work/YubiSecure_KS_STM12/Yubikey.spthy`. Under B0, four of them reach the time limit and one ends without a result. Under B2, ProVerif rejects the exported file with the message `Syntax error` after 0.004 s. The published run decides none of the five.

On the 295 pairs for which the translated route and native Tamarin both return a definitive outcome, the outcomes are equal on 264 and differ on 31, under B0 and under B2. The published records show the same 31 differences. Thirty of them lie in 22 theories that declare the built-in theory `xor`, and one lies in `examples/usenix23-ens/dp3t.spthy`. The differences therefore stem from neither patch.

## Cause of the syntax error

The explanation follows from the source of the exporter, and the [follow-up on the build B3](../b3_followup/README.md) confirms it on the export. In the unmodified exporter, the function `translatePatternTerm` replaces every term that is no literal by a helper variable, and the input branch of `translatePatternFact` writes this variable with the type `bitstring`. The first patch lets `translatePatternTerm` return an equality pattern for a term without variables and names. The input branch still appends the type, and the grammar of ProVerif admits no type after an equality pattern. A textual scan of the 121 theories finds an input of such a term in the YubiKey theory alone, in the rule `InitSucc` with the premises `In(myzero)` and `In(S(myzero))`.

The benchmark run stored no exported file. The follow-up exports one lemma again and finds the error at line 99, character 36, which is the colon after the equality pattern of `In(myzero)`. A third patch omits this type, and ProVerif parses the exports of the resulting build B3 for all five lemmas. B1 holds the first patch without this correction. By a reading of the source, B0 exports the same input as a helper variable without a check and accepts every message there.

## Recompute

```bash
python3 -B validation/V6-exporter/benchmark/summarize_benchmark.py
python3 -B validation/V6-exporter/compare_runs.py \
    validation/V6-exporter/benchmark/comparison/results_B0.tsv \
    validation/V6-exporter/benchmark/comparison/results_B2.tsv \
    --key model,lemma --verdict verdict --reference native
```

The first command prints the counts of this page without the lines on the theory files. With `--examples DIR`, where `DIR` holds the directory `examples/` of Tamarin at commit `c293106913cc`, the script also checks the hashes of the 121 theories and repeats the scan, and its output equals [`summary.txt`](summary.txt). The second command reports 561 of 566 unchanged outcomes. Its agreement count of 268 includes four pairs without a result on both sides, which the count of 264 leaves out.
