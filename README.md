# Cross-tool verification of iterative cryptographic protocols

This repository is the reproduction package of the paper *A Cross-Tool Formal Verification Methodology for Cryptographic Protocols with Iterative Behavior Using ProVerif and Tamarin Prover* by Takehiko Mieno. It holds the generator `cimc`, the models, the run scripts and the records of every experimental series of the paper. Seven scripts check these records and recompute each reported count without a prover.

## Contents

| Directory | Content |
| --- | --- |
| [`cimc/`](cimc/) | Generator of ProVerif and Tamarin models from a Common Iterative Model (CIM), versions 0.1.0 to 0.1.3 with their tests |
| [`cim/`](cim/) | CIM sources of the two signers and the specifications of the twelve KUDOS schedules |
| [`models/`](models/) | Sixteen generated signer models, the hand-written Tamarin theories and the kit that derives and runs their variants |
| [`runs/`](runs/) | Records of the series G, P1 to P5, L, M, X0, X1, X2 and K |
| [`validation/`](validation/) | Plan, scripts, inputs and records of the validation series V1 to V7 |
| [`exporter/`](exporter/) | Probes, patches and build recipes of the Tamarin-to-ProVerif exporter study |
| [`scheduler/`](scheduler/) | Executable checks of the two scheduler lemmas |
| [`diagnosis/`](diagnosis/) | Decision tree 1.1 of the diagnosis procedure |
| [`corpus/`](corpus/) | Sources and hashes of the public theory corpus and the subset of the evaluation data of Morio et al. |
| [`env/`](env/) | Environment records of the hosts and the pinned container image |
| [`registry/`](registry/) | Inventory of all files with SHA-256 hashes, table of normalized files and index of the series |
| [`scripts/`](scripts/) | Checks and recomputations that need Python only |
| [`docs/`](docs/) | Map from the paper to the records, guide to the prover runs and third-party notices |

## Check the records without a prover

The checks need Python 3.11 or later and no further package. Run them from the root of the repository.

```bash
bash scripts/check_all.sh
```

The script runs the following commands in turn and stops at the first failure.

```bash
python3 -B scripts/verify_evidence.py
python3 -B scripts/recompute_paper_numbers.py
python3 -B scripts/recompute_validation_numbers.py --check validation/expected_counts.tsv
python3 -B scripts/check_model_hashes.py
python3 -B scripts/check_kudos_models.py
python3 -B corpus/recompute_morio.py
python3 -B exporter/index_regression.py
```

| Command | Result on an unchanged copy |
| --- | --- |
| `verify_evidence.py` | Every file matches the inventory, every internal hash list matches the original hashes, and the records of the series are consistent |
| `recompute_paper_numbers.py` | 115 counts of the series G to K, M, L and of Lemma 1 equal the values of the paper |
| `recompute_validation_numbers.py` | 527 counts of the series V1 to V4 and V7 equal the stored table |
| `check_model_hashes.py` | 19 derived theory variants and 8 corpus theories carry the hashes of the screening records |
| `check_kudos_models.py` | 24 regenerated KUDOS model inputs are byte-identical to the archived inputs |
| `recompute_morio.py` | The 41 rows of the corpus subset follow from the evaluation data |
| `index_regression.py` | The index of the 540 exporter stages follows from the stage files |

## Regenerate the models

The generator needs Python only. The following commands run its unit tests, check the hashes of the sixteen signer models, regenerate the 1,728 model files of the validation series and run the checks of the two scheduler lemmas.

```bash
(cd cimc/v0.1.2 && python3 -B tests/test_correspondence_guards.py && python3 -B tests/test_hygiene.py && python3 -B tests/test_al.py)
(cd models/generated && sha256sum -c --quiet SHA256SUMS)
python3 -B validation/common/regen_check.py --cimc cimc/v0.1.2 \
    validation/V1-families/sets validation/V2-random/sets validation/V2-boundary/sets/controls \
    validation/V4-mutation/sets/LMOTS__control validation/V4-mutation/sets/LMS_S2__control
python3 -B scheduler/lemma1/run_checks.py
bash scheduler/lemma2/run_checks.sh
```

The regeneration reports 216 sets and 1,728 identical model files. The two scheduler checks report 21 passing tests and four suites without an unexpected result. The README of each directory lists further commands.

## Rerun the provers

The runs of the paper used ProVerif 2.05, Tamarin 1.12.0 and Maude 3.5.1. The [reproduction guide](docs/REPRODUCTION.md) states the tools, the limits and one command per series. The [evidence map](docs/PAPER_MAPPING.md) relates each series, table and claim of the paper to its records and names the records that this repository lacks.

## Integrity of the files

The inventory [`registry/repository-files.tsv`](registry/repository-files.tsv) lists the size and the SHA-256 hash of every file. Model files, inputs and verdict records keep the bytes of the runs. The published bytes of 613 other files differ from the bytes of the runs. In 586 logs and environment records, placeholders replace host names and local paths. Seven files carry notes, headings or messages in English translation, and 20 scripts carry revised comments or default paths for the layout of this repository. The table [`registry/normalized-files.tsv`](registry/normalized-files.tsv) states the original and the published hash of each such file, and the [registry notes](registry/README.md) explain how the checks use both.

Tool outputs and third-party sources keep their wording, including the first-person plural in ProVerif messages and in license texts.

## Sources and licenses

The signer models abstract LM-OTS, LMS and HSS of [RFC 8554](https://www.rfc-editor.org/rfc/rfc8554). The exporter study starts from a [pinned commit of the development branch of Tamarin](https://github.com/tamarin-prover/tamarin-prover/tree/c293106913ccf7bb41f49b0dc555a8074e8ea88c) and from the [artifact of Morio, Ivanov and Künnemann](https://doi.org/10.5281/zenodo.21827126). The [third-party notices](docs/THIRD_PARTY_NOTICES.md) name the sources, their licenses and the modified files. The [MIT License](LICENSE) covers the author's original files.

## Citation and contact

[`CITATION.cff`](CITATION.cff) identifies the repository. Please cite the paper if these results contribute to other work. The paper cites the repository by its address and names no commit. The page [`docs/RELEASES.md`](docs/RELEASES.md) relates the releases of the repository to the versions of the paper.

Takehiko Mieno, EPSON AVASYS Corporation, Ueda, Nagano, Japan, `mieno.takehiko2@exc.epson.co.jp`
