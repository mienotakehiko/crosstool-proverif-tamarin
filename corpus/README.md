# Public theory corpus

[The corpus registry](../registry/corpus.tsv) identifies the eight source theories and expected screening hashes. For K2–K8, the path names are relative to the [Tamarin example suite](https://github.com/tamarin-prover/tamarin-prover/tree/1.12.0/examples). Confirm the SHA-256 before using an upstream copy. For K1, [the KUDOS source repository](https://github.com/rikard-sics/kudos-tamarin-model) was recorded with commit prefix `bfe9bd09ba42`. The helper retrieves that revision and checks the expected digest.

```bash
bash corpus/get_kudos_model.sh /path/to/K1_hoglund_KUDOS.spthy
```

The seven-theory subset of the [Morio, Ivanov and Künnemann dataset](https://doi.org/10.5281/zenodo.21827126) uses K2–K8. The original `eval-results.jsonl`, its [CC0 dedication](morio/CC0-1.0.txt) and the resulting [41-row table](morio/subset41.tsv) are included. From the root, use `python3 -B corpus/recompute_morio.py` to check the subset against the source. Use `--write` to regenerate the table.
