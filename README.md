# Cross-tool verification of iterative cryptographic protocols

This repository accompanies *A Cross-Tool Formal Verification Methodology for Cryptographic Protocols with Iterative Behavior Using ProVerif and Tamarin Prover*. It contains the Common Iterative Model (CIM) compiler, selected symbolic models, state-translation probes, and result tables from the my research snapshot.

Project repository on [GitHub](https://github.com/mienotakehiko/crosstool-proverif-tamarin).

## Verification paths

| Path | Input and procedure |
| --- | --- |
| (a) Native Tamarin | Tamarin checks a lemma in a multiset-rewriting model. |
| (b) Direct ProVerif | The CIM compiler generates a ProVerif encoding directly from a TOML model. The correspondence applies under the stated conditions for the encoding and property. |
| (c) Translated ProVerif | The pinned Tamarin exporter translates the input model and lemma for ProVerif. The recorded verdicts retain the effects of query polarity and any translation warnings. |

Model assumptions, query scope, and termination status determine which verdicts can be compared. For example, a reconstructed trace for a negated event query establishes reachability, while a timeout leaves the property unresolved. The tables distinguish archived runs from diagnostic interventions.

## Repository layout

| Location | Contents |
| --- | --- |
| [`code/cimc/pv-kit-v2/`](code/cimc/pv-kit-v2/) | CIM compiler and diagnosis tools, LM-OTS and LMS inputs, generated fixtures, and regression tests |
| [`code/tamarin-kit/v3/`](code/tamarin-kit/v3/) | Selected Tamarin models, tactic generation, and single-run and summary tools |
| [`code/studies/state-translation/`](code/studies/state-translation/) | Initial, zero-argument, guarded, and expanded state probes |
| [`experiments/`](experiments/) | Historical run records and result tables, including C1, H1/H2, the pinned corpus, and LMS |
| [`environments/fixed-ccs26/`](environments/fixed-ccs26/) | Recorded tool hashes, commit markers, and fixed container identity |
| [`registry/`](registry/) | Cohort descriptions, state comparison rows, and SHA-256 inventories |
| [`scripts/verify_evidence.py`](scripts/verify_evidence.py) | Offline integrity and consistency checks |

## Check the snapshot

The offline checker requires Python 3.11 or later. Run it from the repository root.

```bash
python3 -B scripts/verify_evidence.py
```

The script checks the current file manifest, archived counts, and evidence references. Pass `--archives /path/to/extracted/cross-tool-evidence` to verify the original archive files by SHA-256. Pass `--u5-a /path/to/U5_A_models_results.tar.gz` for the separate U5 archive. The checker reads the files without extracting their contents or starting either prover.

Run the CIM unit and regression tests and regenerate the LMS fixtures in a temporary directory.

```bash
(
  cd code/cimc/pv-kit-v2 &&
  python3 -B tests/test_al.py &&
  python3 -B tests/regress_al.py &&
  output_dir="$(mktemp -d)" &&
  python3 -B -m cimc cims/lms_s2.toml "$output_dir" &&
  diff -r --exclude=run_tam.sh out/lms_s2 "$output_dir"
)
```

The generated fixtures include a SHA-256 manifest and a report on the compiler's side conditions. The historical tool versions for these CIM examples were ProVerif 2.05 and Tamarin 1.12.0. The shell runners also use tools such as GNU `timeout` and `bc`. The resource settings in the historical runners reflect the original hosts.

Run the initial state probe's runner tests separately.

```bash
(cd code/studies/state-translation/initial && python3 -B -m unittest -v test_kit)
```

The runner tests exercise input checks and mock tool launches. The pinned probe commands below require a locally available Docker image with the identity recorded in [`runtime.json`](environments/fixed-ccs26/runtime.json). An arbitrary Tamarin or ProVerif release does not reproduce this environment. The version markers and executable hashes establish the recorded runtime identity. The snapshot does not establish a byte-identical rebuild from the recorded source commits.

| Working directory under `code/studies/state-translation/` | Command | Comparison |
| --- | --- | --- |
| `initial/` | `bash run_pinned.sh` | Native and translated verdicts for finite state consumption |
| `zero-argument/` | `bash run_pinned.sh` | Zero-argument and successor state patterns |
| `guarded/` | `python3 -B guard_compare.py` | Saved and equality-guarded ProVerif inputs |
| `source/source_probe/` | `python3 -B run_probe.py` | Nested, paired, and variable state patterns |

## Archived comparisons

| Cohort | Observations |
| --- | --- |
| Initial state probe | 16 agreements in 16 native–export comparisons |
| Zero-argument state probe | 10 agreements and 6 differences in 16 comparisons |
| Explicit equality guard | The original inputs reproduced all 16 saved ProVerif verdicts. All 16 guarded verdicts agreed with the saved native results. |
| Expanded state probe | 13 agreements and 3 differences in 16 native–export comparisons |
| H1/H2 Stage D | 48 agreements in 49 original comparisons and 12 agreements in 12 separate diagnostic comparisons |
| C1 native closeout | Four universal properties verified, one universal property falsified, and two existence lemmas verified |
| RQ5(b) | The correspondence table records the 24 resource-limited cases. The numerator and proportion remain undetermined. |

These counts apply to the listed cohorts. The guard study changes generated ProVerif inputs for a local diagnostic comparison. The candidate exporter patch had reached a static apply check at the date of this snapshot. The state probes address specific patterns in finite test models.

The repository contains selected records from the research archive. Where a public table projects columns from its source, it retains case IDs, verdicts, and relevant digests. The separate evidence archive retains the original host paths, full output, and additional historical inputs. The evidence inventory includes third-party inputs and historical materials outside this repository.

## Sources and attribution

The LMS and LM-OTS models use abstractions of the schemes in [RFC 8554](https://www.rfc-editor.org/rfc/rfc8554). The translation experiments reference [the pinned Tamarin fork](https://github.com/felixlinker/tamarin-prover/tree/c293106913ccf7bb41f49b0dc555a8074e8ea88c) and [the CCS evaluation artifact](https://zenodo.org/records/21827126). The latter appears as `ccs26.zip` in the evidence inventory. Consult the original distributions for their source code and license notices.


## Contact

Takehiko Mieno, EPSON AVASYS Corporation, Ueda, Nagano 386-1214, Japan.
Email: `Mieno.Takehiko2@exc.epson.co.jp`.

