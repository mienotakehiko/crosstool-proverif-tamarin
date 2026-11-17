# Mapping between the manuscript and this repository

[README.md](../README.md) maps manuscript series to commands and table or figure subjects. [series_map.tsv](../registry/series_map.tsv) gives the evidence status of each series. [recovered-files.tsv](../registry/recovered-files.tsv) maps recovered files to archive members and SHA-256 values. The version and outcome in each archived record govern comparisons.

| Review item | Evidence in this repository | Original evidence still needed |
| --- | --- | --- |
| 1. Generator and assurance | Compiler versions 0.1.0, 0.1.1 and 0.1.2, Diagnosis v1.1 source, 9 guard checks, 13 hygiene checks, 37 AL assertions, and captured-input and scalar-pattern controls | Original Diagnosis v1.1 24-test run |
| 2. G Tamarin | Sandbox data, 23 rows with 19 conclusive outcomes | The 32 production judgments, matching JSONL and `tamout/`, generation manifest and environment |
| 3. Screening models | All nine requested original theories and the six existing theories. Derived hashes match 19 variants in P1–P3, covering 207 jobs | None for the nine requested inputs |
| 4. M | [October pilot, October main experiment and November frozen-query re-evaluation](../runs/M/README.md) | Two wrapper ZIPs referenced by the November scheduler and compiler checksums are unavailable; their extracted research files are included |
| 5. X1 | B0/B1/B2 comparison, 21 models, all 60 pairs and all 540 archived stage invocations, two patches and build records | The original binaries if a direct binary hash recheck is desired |
| 6. X2 | 20 exports, legacy LMS and HSS ProVerif pilots, [HSS premise comparison](../runs/X2/hss-candidate-comparison.tsv), native HSS runs and byte-identity check | None for the reported fixed-build results |
| 7. X0 | 15 archived naming-fix runs and a 40-row post-rename join | None for the reported outcome counts |
| 8. K | 12 specifications, original generators, 24 matching generated models, direct-run outputs and Stage D records | See the [K evidence notes](../runs/K/README.md) for how the 24 slots link to the outputs |
| 9. Lemma 1 | [Restricted suite, fixture and 21 stored pass records](../scheduler/README.md) | Full semantic equivalence is outside the scope of the suite |
| 10. Morio et al. | Original dataset, 41-row subset and calculation script | None for the 41-row subset |

The [release checklist](RELEASE_CHECKLIST_20261117.md) links the quantitative and publication audits.

## Counting rules

- Screening selects the latest recorded attempt per job in the cumulative checkpoint. These are the 295 P1–P4 jobs. The eight corpus hashes come from the P4 records. Seven also match the original files recorded in the companion kit. The corpus K1 hash identifies the author's imported input.
- P5 counts five archived trials per selected baseline. It does not estimate the chance of obtaining a result on all screening jobs. The ladder data distinguish nine new trials from earlier 56 GiB reference points. The cloud environment record identifies CPU count, memory and tool versions. The EC2 instance type remains unknown.
- X0 joins the 15 recorded alpha-renaming reruns by theory and lemma. Of the 40 retained pairs, 9 have raw `true`, 1 has raw `false`, 26 have `cannot be proved`, and 4 have `TIMEOUT`. The original raw verdicts, including their query polarity, remain in the original records.
- X1 compares the same 60 pairs across three builds. The 540 stages cover native Tamarin, export, and ProVerif for each of those pairs. The earlier image-based probes and the focused intervention have different scopes.
- X2's application archive supplies exports. Separate pilot and premise archives supply logical verdicts. For `DgInj` with `TopAuth` as an ordinary native lemma, Tamarin verifies `exec` and `LS7` in 14 and 408 steps. The same source generates the two ProVerif inputs byte for byte. `TopAuth` alone times out in the two premise experiments.
- K juxtaposes 49 original Stage D lemma comparisons and 12 separate diagnostic comparisons. The 24-row index connects 12 schedules to their direct ProVerif and Tamarin inputs. Stage D uses separate per-lemma stages.
- The Morio et al. count uses seven specified theories from the dataset in [Zenodo record 21827126](https://doi.org/10.5281/zenodo.21827126). It is a selected 41-row subset. The broader CCS evaluation and the present paper's X0/X1 experiments have separate denominators.
- The 24 resource-limited translated cases in [RQ5(b)](../runs/rq5b/correspondence/) have an unconfirmed matched direct-route numerator. This repository assigns no proportion.

## Updating the manifest

```bash
git add -A
python3 -B scripts/update_manifest.py
git add registry/repository-files.tsv
python3 -B scripts/update_manifest.py --check
python3 -B scripts/verify_evidence.py
```

In archived P3 and P5 log filenames, `rank-lower-s` and `rank-upper-s` distinguish the original `s` and `S` heuristics on case-insensitive file systems. The evidence map retains the original archive member name. Job IDs in tables and records retain their original spelling.
