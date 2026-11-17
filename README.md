# Cross-tool verification of iterative cryptographic protocols

This repository accompanies *A Cross-Tool Formal Verification Methodology for Cryptographic Protocols with Iterative Behavior Using ProVerif and Tamarin Prover*. It collects the Common Iterative Model (CIM) compiler, symbolic models, published comparison data and archived results for the manuscript. See the [GitHub repository](https://github.com/mienotakehiko/crosstool-proverif-tamarin).

**Evidence status.** The [manuscript map](docs/PAPER_MAPPING.md) identifies the original evidence available for each claim. The historical M runs, Lemma 1 suite, and compiler versions 0.1.1 and 0.1.2 are included. The original Diagnosis v1.1 run of 24 tests and the G production Tamarin runs remain unrecovered. See the [release checklist](docs/RELEASE_CHECKLIST_20261117.md) for technical and publication status.

## Recompute the manuscript results

Use Python 3.11 or later from the repository root.

```bash
python3 -B scripts/verify_evidence.py
python3 -B scripts/verify_recovery_20261117.py
python3 -B scripts/check_x1_archives.py
python3 -B scripts/check_model_hashes.py
python3 -B scripts/check_kudos_models.py
python3 -B scripts/recompute_paper_numbers.py
python3 -B corpus/recompute_morio.py
```

The default recomputation includes the baseline counts and the checks added for the recovered records. Use `--baseline-only` for the 61 baseline comparisons. The scripts read local files and start neither prover.

| Series | Records | Recalculation | Manuscript location |
| --- | --- | --- | --- |
| G | [ProVerif verdicts](runs/G/proverif/), [sandbox fixtures](cimc/v0.1.0/tests/data/) | `scripts/recompute_paper_numbers.py` | Table 9, generated-model evaluation and AL |
| P1–P4 | [P1](runs/P1/), [P2](runs/P2/), [P3](runs/P3/), [P4](runs/P4/), [cumulative checkpoints](runs/screening/) | `scripts/recompute_paper_numbers.py`, `scripts/check_model_hashes.py` | Tables 9–10, screening and corpus |
| P5 | [Repeated runs](runs/P5/) | `scripts/recompute_paper_numbers.py` | Repetition and search-order comparison |
| L | [Ladder and cloud runs](runs/L/), [host configuration](env/u11/) | `scripts/recompute_paper_numbers.py`, `paper/plot_ladder.py` | Heap-exhaustion figure and 96 GiB trials |
| M | [October and November cohorts](runs/M/) | `scripts/verify_recovery_20261117.py` | Mutation evaluation |
| X0 | [Historical and post-rename records](runs/X0/) | `scripts/recompute_paper_numbers.py` | Handwritten-model translation outcomes |
| X1 | [Comparison and stage files](runs/X1/), [patches and recipes](exporter/) | `exporter/index_regression.py`, `scripts/recompute_paper_numbers.py` | B0/B1/B2 regression table |
| X2 | [LMS/HSS exports and proof records](runs/X2/) | `scripts/recompute_paper_numbers.py` | LMS/HSS application and assumptions table |
| K | [Schedules and run records](runs/K/), [specifications and generators](cim/kudos/) | `scripts/recompute_paper_numbers.py` | Finite KUDOS schedule comparison |
| Corpus | [Theory sources and SHA-256 hashes](registry/corpus.tsv), [Morio et al. subset](corpus/morio/) | `corpus/recompute_morio.py`, `scripts/check_model_hashes.py` | Public theory corpus and related work |
| Lemma 1 | [Restricted scheduler suite](scheduler/) | `scheduler/restricted_20261111/run_checks.py` | Appendix B |

The paper references use the series names and table subjects because table and figure numbers can change between revisions.

## Source and evidence layout

| Directory | Contents |
| --- | --- |
| [`cimc/`](cimc/), [`cim/`](cim/) | Compiler versions 0.1.0, 0.1.1 and 0.1.2, and signer/KUDOS specifications |
| [`models/`](models/) | Generated signer fixtures and their SHA-256 sums, handwritten theories, and tactic generation |
| [`al/`](al/), [`diagnosis/`](diagnosis/), [`scheduler/`](scheduler/) | Version and test coverage notes |
| [`exporter/`](exporter/) | Translation probes, regression stage indexing, source patches and selected build recipes |
| [`env/`](env/), [`registry/`](registry/) | Recorded environments, manuscript map, source provenance and file inventories |
| [`paper/`](paper/) | Data and script for the memory-ladder figure |

The native Tamarin route checks a lemma against a multiset-rewriting theory. The direct ProVerif route generates a process from a CIM specification. The translated ProVerif route uses an exporter on a Tamarin model and lemma. Compare verdicts only after checking the model assumptions and query polarity. A reconstructed witness for a negated existence query establishes reachability. A timeout leaves that run unresolved.

## Check the archived compiler and models

Run the compiler and its existing tests from its version directory.

```bash
(
  cd cimc/v0.1.0 &&
  python3 -B tests/test_al.py &&
  python3 -B tests/regress_al.py &&
  work="$(mktemp -d)" &&
  python3 -B -m cimc ../../cim/signers/lms_s2.toml "$work" &&
  diff -r --exclude=run_tam.sh ../../models/generated/v0.1.0/lms_s2 "$work"
)
(cd models/generated && sha256sum -c SHA256SUMS)
(cd exporter/probes/initial && python3 -B -m unittest -v test_kit)
```

The legacy compiler checks exercise version 0.1.0. The generated signer manifest authenticates the 16 archived fixtures. To inspect the exporter build, follow the [build and regression notes](exporter/README.md). The resource budgets and runtime identities in the archived records belong to their respective cohorts.

## Sources and licensing

The LMS and LM-OTS models use abstractions of [RFC 8554](https://www.rfc-editor.org/rfc/rfc8554). The controlled translation comparison records the [pinned Tamarin fork](https://github.com/felixlinker/tamarin-prover/tree/c293106913ccf7bb41f49b0dc555a8074e8ea88c). The Morio et al. subset comes from the [CCS 2026 evaluation artifact](https://doi.org/10.5281/zenodo.21827126). The [third-party notices](docs/THIRD_PARTY_NOTICES.md) identify the source, licenses and boundaries of redistribution. [CITATION.cff](CITATION.cff) identifies the repository and its author.

The supplied materials do not identify a repository-wide license for the author's code. The author can add one after confirming the intended terms. For evidence provenance, see [recovered-files.tsv](registry/recovered-files.tsv). It records source and published hashes for files recovered from archives. Some text logs normalize host paths. Model files and benchmark inputs retain their source bytes.

## Contact

Takehiko Mieno, EPSON AVASYS Corporation, Ueda, Nagano, Japan.
Email `Mieno.Takehiko2@exc.epson.co.jp`.
