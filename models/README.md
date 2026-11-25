# Models

| Path | Content |
| --- | --- |
| [`generated/v0.1.0/`](generated/v0.1.0/) | The sixteen models that generator 0.1.0 writes for the LM-OTS and the LMS signer, with their side-condition reports and manifests |
| [`handwritten/`](handwritten/) | Hand-written Tamarin theories of LM-OTS, LMS, HSS and the chain protocol |
| [`tamarin-kit-v3/`](tamarin-kit-v3/) | Kit that derives the variants of the hand-written theories and proves one lemma per call |

## Generated models

The hash list `generated/SHA256SUMS` covers the sixteen model files. The following commands check the list and regenerate the LMS models with generator 0.1.0.

```bash
(cd models/generated && sha256sum -c --quiet SHA256SUMS)
work=$(mktemp -d)
(cd cimc/v0.1.0 && python3 -B -m cimc ../../cim/signers/lms_s2.toml "$work")
diff -r --exclude=run_tam.sh models/generated/v0.1.0/lms_s2 "$work"
```

## Hand-written theories

The script `handwritten/gen_stage2.py` prints the three LMS theories `LMS_S2_base`, `LMS_S2_rollback` and `LMS_S2_clone`, which share one rule set and differ in the permitted evolution of the signer state. The theory `hss_dginj_only.spthy` is the HSS theory with the injectivity restriction of the digest alone, which series X2 uses.

The script `tamarin-kit-v3/tactics/make_variants.py` writes two variants of every theory. The variant `__T0` is the theory without change, and the variant `__T1` adds the tactic `statefirst`, which changes the order of the proof search and no rule, restriction or lemma. The command `python3 -B scripts/check_model_hashes.py` derives the variants in a temporary directory and compares their hashes with the records of the series P1 to P3.

The runner `tamarin-kit-v3/run_one_v3.sh` proves one lemma and appends one record. The [reproduction guide](../docs/REPRODUCTION.md) shows a call. The table `tamarin-kit-v3/expected_v3.tsv` states the verdicts that the kit expected before the screening, and `summarize_v3.py` compares a record file with it.
