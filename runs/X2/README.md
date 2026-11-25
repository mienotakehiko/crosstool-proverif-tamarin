# Series X2, exporter applications to LMS and HSS

Series X2 applies the exporter builds B0 and B2 to the hand-written LMS and HSS theories.

| Path | Content |
| --- | --- |
| [`lms_hss_application_cndk8z5k/`](lms_hss_application_cndk8z5k/) | Exports of ten pairs of model and lemma by both builds. The table `results/comparison.tsv` states the translation status of the 20 exports |
| [`legacy_lms_pilot/`](legacy_lms_pilot/) | ProVerif runs on the exports of the lemmas `exec` and `LS1` of the LMS theory |
| [`hss_pilot/`](hss_pilot/), [`hss_noinj_300s/`](hss_noinj_300s/), [`hss_premises/`](hss_premises/) | ProVerif runs on the HSS exports under four combinations of two premises |
| [`hss_native_dginj/`](hss_native_dginj/) | Native Tamarin runs of the HSS theory with the digest restriction alone |
| [`hss_model_link/`](hss_model_link/) | Exports of that theory and their comparison with the inputs of the premise runs |
| [`hss-candidate-comparison.tsv`](hss-candidate-comparison.tsv) | Outcome of `exec` and `LS7` under each of the four premise combinations |
| [`hss-assumptions.tsv`](hss-assumptions.tsv) | Result lines of all HSS runs, including the native runs |
| [`historical/`](historical/) | Summaries and pinned commits of five earlier probes on the LMS lemmas `LS1` and `LS4_pure` |

The statuses of the application table are translation results. The ProVerif verdicts come from the pilot and premise directories.

The two premises are the injectivity restriction of the digest (`DgInj`) and the lemma `TopAuth` as an axiom. With `DgInj` alone, native Tamarin verifies `exec` in 14 steps and `LS7` in 408 steps, and the exports of that theory are byte-identical to the ProVerif inputs of the premise run. On these inputs ProVerif answers `false` for the negated query `exec`, which gives a witness of reachability, and `true` for `LS7`. With the axiom `TopAuth` alone, both ProVerif runs reach the time limit, and a run at its time limit supplies no verdict.

The run scripts of the subdirectories record the container commands of the runs. Four of them printed Japanese messages in the runs and carry English messages here. The [table of normalized files](../../registry/normalized-files.tsv) states their original hashes.
