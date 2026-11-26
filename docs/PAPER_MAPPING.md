# Evidence map

This map relates every experimental series of the paper to its records in this repository and to the command that recomputes its counts. The paper identifies each series by a letter, and this map uses the same letters. Table and figure numbers can change between revisions of the paper, so the map names the subject of each table.

## Series G to K

| Series | Content and size | Records | Recomputation |
| --- | --- | --- | --- |
| G | Generated LM-OTS and LMS signers in both tools, 28 ProVerif queries and 32 Tamarin lemmas | [`runs/G/proverif/pv_results.jsonl`](../runs/G/proverif/pv_results.jsonl) for the first ProVerif run. [`LMOTS__control`](../validation/V4-mutation/sets/LMOTS__control/) and [`LMS_S2__control`](../validation/V4-mutation/sets/LMS_S2__control/) for the rerun of both tools with generator 0.1.2 | `scripts/recompute_paper_numbers.py`, `scripts/recompute_validation_numbers.py` |
| P1 to P3 | Tamarin screening of the signer, HSS and chain theories under search variants, 81, 102 and 24 jobs | [`runs/P1/`](../runs/P1/), [`runs/P2/`](../runs/P2/), [`runs/P3/`](../runs/P3/), cumulative record [`runs/screening/records.jsonl`](../runs/screening/records.jsonl) | `scripts/recompute_paper_numbers.py`, `scripts/check_model_hashes.py` |
| P4 | Public corpus on the standard and the cyclic build, 88 jobs | [`runs/P4/`](../runs/P4/), [`corpus/corpus.tsv`](../corpus/corpus.tsv) | `scripts/recompute_paper_numbers.py`, `scripts/check_model_hashes.py` |
| P5 | Fivefold repetition of the conclusive jobs, 225 jobs and 1,125 trials | [`runs/P5/`](../runs/P5/) | `scripts/recompute_paper_numbers.py` |
| L | Heap limits for the searches that exhaust 56 GiB, 9 runs at 8 to 32 GiB and 7 runs at 96 GiB | [`runs/L/ladder/`](../runs/L/ladder/), [`runs/L/heap96/`](../runs/L/heap96/), [`env/ec2-96g/`](../env/ec2-96g/) | `scripts/recompute_paper_numbers.py` |
| M | Mutation of generated ProVerif encodings, 20 mutants and 2 controls | [`runs/M/`](../runs/M/) | `scripts/recompute_paper_numbers.py`, `scripts/verify_evidence.py` |
| X0 | Translation of hand-written theories, 40 pairs of model and lemma | [`runs/X0/`](../runs/X0/) | `scripts/recompute_paper_numbers.py` |
| X1 | Exporter regression on three builds, 60 pairs of model and lemma and 540 stages | [`runs/X1/`](../runs/X1/), [`exporter/`](../exporter/) | `exporter/index_regression.py`, `scripts/recompute_paper_numbers.py` |
| X2 | Exporter applications to LMS and HSS, 10 pairs of model and lemma and 20 exports | [`runs/X2/`](../runs/X2/) | `scripts/recompute_paper_numbers.py` |
| K | Finite KUDOS schedules, 12 schedules, 24 model inputs and 49 lemma comparisons | [`runs/K/`](../runs/K/), [`cim/kudos/`](../cim/kudos/) | `scripts/check_kudos_models.py`, `scripts/recompute_paper_numbers.py` |
| Chain model | Summary of the seven properties of the chain theory `C1_E1g` in native Tamarin | [`runs/chain/native-closeout/native_results.json`](../runs/chain/native-closeout/native_results.json) | `scripts/recompute_paper_numbers.py` |
| Corpus | Eight public theories and 41 rows of the evaluation data of Morio et al. | [`corpus/`](../corpus/) | `corpus/recompute_morio.py` |

## Validation series V1 to V7

| Series | Content and size | Records | Recomputation |
| --- | --- | --- | --- |
| V1 | Three parameterized families in both tools, 12 members and 372 records | [`validation/V1-families/`](../validation/V1-families/) | `scripts/recompute_validation_numbers.py` |
| V2 | 200 random CIMs with 1,024 properties and 8,192 records, 12 boundary probes and 4 pair-shaped probes | [`validation/V2-random/`](../validation/V2-random/), [`validation/V2-boundary/`](../validation/V2-boundary/) | `scripts/recompute_validation_numbers.py` |
| V3 | 41 sealed labels for the decision tree | [`validation/V3-diagnosis/`](../validation/V3-diagnosis/), [`validation/plan/labels.sha256`](../validation/plan/labels.sha256) | `scripts/recompute_validation_numbers.py` |
| V4 | Held-out mutation, 30 mutants and 2 controls with 972 records, and 94 input mutants | [`validation/V4-mutation/`](../validation/V4-mutation/) | `scripts/recompute_validation_numbers.py` |
| V5 | Bounded enumeration of the two schedulers of Lemma 2, 225 enumerations | [`scheduler/lemma2/`](../scheduler/lemma2/) | `bash scheduler/lemma2/run_checks.sh` |
| V6 | Exporter at the upstream head of Tamarin (commit `03215cd03e7c`), 2 models and 2 corrected exports, reported upstream as [issue 996](https://github.com/tamarin-prover/tamarin-prover/issues/996) | [`validation/V6-exporter/`](../validation/V6-exporter/) | inspection of the stored outputs |
| V7 | Fourfold time limit, 10 jobs | [`validation/V7-time-limit/`](../validation/V7-time-limit/) | `scripts/recompute_validation_numbers.py` |

## Generator, lemmas and diagnosis

| Subject of the paper | Records | Check |
| --- | --- | --- |
| Generator and its side-condition checks | [`cimc/`](../cimc/) with 9 guard tests, 13 hygiene tests, 5 literal tests and 37 assertions on the Achievement Levels | unit tests in [`cimc/README.md`](../cimc/README.md) |
| Third counterexample (literal in the shape of a numeral) | [`cimc/v0.1.3/`](../cimc/v0.1.3/), probe `b13_numeral_literal_pair` in [`validation/V2-boundary/`](../validation/V2-boundary/) | `validation/V2-boundary/run_boundary.py` |
| Lemma 1 (restricted scheduler) | [`scheduler/lemma1/`](../scheduler/lemma1/) with 21 stored passes | `scheduler/lemma1/run_checks.py` |
| Lemma 2 (unrolled scheduler) | [`scheduler/lemma2/`](../scheduler/lemma2/) | `scheduler/lemma2/run_checks.sh` |
| Decision tree 1.1 | [`diagnosis/v1.1/diagnose.py`](../diagnosis/v1.1/diagnose.py), SHA-256 `d45347db969b78a5209adb13dbee3cc00b7d6047ec0c60a14d40be7cfc0de8e6` | `scripts/verify_evidence.py` |
| Reveal alternative of the signers | [`scheduler/lemma2/predict_reveal.py`](../scheduler/lemma2/predict_reveal.py) | command in [`scheduler/README.md`](../scheduler/README.md) |
| Reveal alternative in the one-time password family, prover runs | [`validation/V1-families/reveal_followup/`](../validation/V1-families/reveal_followup/) | `python3 -B validation/V1-families/reveal_followup/summarize_reveal.py --no-write` |

## Counting rules

A record is one ProVerif query or one Tamarin lemma on one model. If a job has several records, the last one counts.

The screening counts of P1 to P4 take the last attempt of each of the 295 jobs from the cumulative record. P5 counts five trials for each of 225 conclusive jobs and compares every trial with the first run of its job. The ladder of series L holds nine new trials, and its three reference points at 56 GiB come from the records of P2.

Series X0 joins the 15 reruns after the renaming fix to the original records by theory and lemma. Of the 40 pairs, ProVerif answers `true` for 9, `false` for 1 and `cannot be proved` for 26, and 4 runs reach the time limit. The 24 translated runs that ended at a resource limit have no matched direct result, so the repository assigns no proportion to them ([`correspondence_24.tsv`](../runs/X0/resource-limited/correspondence_24.tsv)).

Series X1 compares the same 60 pairs on the three builds B0, B1 and B2. The 540 stages cover native Tamarin, export and ProVerif for each pair and build. The probes that preceded the regression form separate cohorts ([`state_comparisons.tsv`](../runs/X1/historical-probes/state_comparisons.tsv)).

Series K compares 49 lemmas in the original stage and 12 lemmas in a separate diagnostic stage. The 24 model inputs belong to 12 schedules with one ProVerif and one Tamarin input each.

The counts of the validation series follow from [`validation/common/xcheck.py`](../validation/common/xcheck.py), which counts the excluded verdict pairs and the agreement on the standard system. The Achievement Levels come from the program `al_assign` of generator 0.1.2 with decision tree 1.1. The counts of V1 and V2 refer to the renamed inputs that the [validation notes](../validation/README.md) describe.

The reveal follow-up of series V1 holds 64 records of its own, which enter none of the counts of the validation series.

## Records that this repository lacks

| Subject | Missing record | Available instead |
| --- | --- | --- |
| Series G, first run | Tamarin outputs of the 32 lemmas | Rerun of both tools in the two control sets of V4 |
| Series L | CloudTrail export with the management events of the 96 GiB host, which contains account and network identifiers | Event times, instance type and the hash of the export in [`env/ec2-96g/instance-type.md`](../env/ec2-96g/instance-type.md) |
| Series X1 | Binaries of the three exporter builds | Recorded hashes, build logs, patches and recipes |
| Series V1 to V4 | Complete tool outputs of the runs | One record per query or lemma with the verdict line, the exit status and the hash of the model |
| Pair-shaped probes of V2 | Complete tool outputs | [`raw-verdict-lines.tsv`](../validation/V2-boundary/sets/pair/raw-verdict-lines.tsv) with the verdict line and the hash of each output |
| Reveal follow-up of V1 | Complete tool outputs | [`raw-verdict-lines.tsv`](../validation/V1-families/reveal_followup/records/raw-verdict-lines.tsv) with the verdict line and the hash of each output |
| Series V3 | Items for five of the eight causes | 41 items for three causes |

The reports of the generator and its grade tables call Hypothesis 1 of the paper "Theorem 1", its name in an early draft, and [`cimc/README.md`](../cimc/README.md) explains this name. The file names of two search heuristics differ from their job identifiers. The archived outputs of P3 and P5 use `rank-lower-s` and `rank-upper-s` for the heuristics `s` and `S`, because some file systems ignore case. The records keep the original spelling.
