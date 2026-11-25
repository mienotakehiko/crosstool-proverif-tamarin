# Public theory corpus

The table [`corpus.tsv`](corpus.tsv) names the eight public Tamarin theories of series P4 with their authors, their upstream paths and their SHA-256 hashes. The repository holds no copy of these theories.

The theories K2 to K8 belong to the [example suite of Tamarin 1.12.0](https://github.com/tamarin-prover/tamarin-prover/tree/1.12.0/examples), and the column `upstream_path` is relative to that suite. Compare the hash of a downloaded file with the column `record_sha256` before a run. The theory K1 is the KUDOS model of Höglund et al. The following script fetches it at the recorded commit and checks its hash.

```bash
bash corpus/get_kudos_model.sh /path/to/K1_hoglund_KUDOS.spthy
```

## Subset of the evaluation data of Morio et al.

The paper compares its results with 41 rows of the evaluation data of [Morio, Ivanov and Künnemann](https://doi.org/10.5281/zenodo.21827126). These rows are all lemmas of the theories K2 to K8 in that data.

| File | Content |
| --- | --- |
| [`morio/eval-results.jsonl`](morio/eval-results.jsonl) | Evaluation data of the artifact, without change |
| [`morio/CC0-1.0.txt`](morio/CC0-1.0.txt) | Public-domain dedication of the data |
| [`morio/subset41.tsv`](morio/subset41.tsv) | The 41 rows with the category of each ProVerif outcome |

The command `python3 -B corpus/recompute_morio.py` derives the subset from the data and compares it with the stored table. The ProVerif outcomes of the subset are 1 Boolean verdict, 17 runs out of memory, 12 timeouts, 6 errors and 5 runs without a verdict.
