# Generator cimc

The generator `cimc` compiles one Common Iterative Model into eight models and checks the side conditions of the correspondence hypothesis on its own output. It needs Python 3.11 or later and no further package.

| Output file | Model |
| --- | --- |
| `*_PV_U<n>.pv` | ProVerif, state unrolled n times |
| `*_PV_Urb<n>.pv` | ProVerif, unrolled with one rollback on request |
| `*_PV_lin.pv` | ProVerif, private state channel with one output per step |
| `*_PV_rep.pv` | ProVerif, private state channel with a replicated output per step |
| `*_T_base.spthy` | Tamarin, linear state fact |
| `*_T_cl1.spthy` | Tamarin, with the rule Clone and one permitted misuse |
| `*_T_rb1.spthy` | Tamarin, with snapshots, the rule Rollback and one permitted misuse |
| `*_T_omega.spthy` | Tamarin, persistent state fact |
| `*_checks.txt` | Side conditions with the results OK, FAIL or BY-CONSTRUCTION |
| `*_manifest.json` | SHA-256 hashes of the input and of every output |

## Versions

| Version | Role in the paper |
| --- | --- |
| [`v0.1.0/`](v0.1.0/) | Generator of the first run of series G and of the sixteen models in [`models/generated/`](../models/generated/) |
| [`v0.1.1/`](v0.1.1/) | Adds the guard tests of the correspondence and decision tree 1.1 |
| [`v0.1.2/`](v0.1.2/) | Refuses reserved identifiers, unbound terms and input patterns of one constant. All models of the validation series come from this version |
| [`v0.1.3/`](v0.1.3/) | Refuses a string literal in the shape of a numeral, such as `'n1'`. Only `validation.py`, `__init__.py` and `__main__.py` differ from version 0.1.2 |

The back ends print the numeral `k` as the ProVerif constant `n<k>` and as the Tamarin constant `'n<k>'`. A string literal `'n1'` therefore denotes the numeral 1 in the Tamarin output and a different constant in the ProVerif output. Version 0.1.2 accepts such an input, and the probe `b13_numeral_literal_pair` of [series V2](../validation/V2-boundary/) shows the resulting disagreement of the two tools. Version 0.1.3 reports the literal under `Hygiene` and writes no model.

The reports and comments of the generator call the correspondence hypothesis of the paper "Theorem 1", its name in an early draft. The statement in the paper is the authoritative one.

## Run the generator and its tests

```bash
(cd cimc/v0.1.3 && python3 -B -m cimc ../../cim/signers/lms_s2.toml "$(mktemp -d)")
(
  cd cimc/v0.1.3 &&
  python3 -B tests/test_correspondence_guards.py &&
  python3 -B tests/test_hygiene.py &&
  python3 -B tests/test_literals.py &&
  python3 -B tests/test_al.py
)
```

The four test files report 9, 13 and 5 passing unit tests and 37 passing assertions. Versions 0.1.1 and 0.1.2 run the same commands without the files that they lack. Version 0.1.0 has `tests/test_al.py` with 33 assertions.

The script `tests/regress_al.py` of the versions 0.1.0 and 0.1.2 recomputes the Achievement Levels from the stored sandbox records under `tests/data/` and compares them with the stored reports. The program `python3 -m cimc.al_assign` computes the levels and the diagnosis of a model set from its verdict records, and the validation scripts call it for the levels of series V1.

## Stored outputs of version 0.1.2

The directory [`v0.1.2/audit_0_1_2/`](v0.1.2/audit_0_1_2/) holds the outputs of the audit that accompanied version 0.1.2. They include the logs of the 9 guard tests, the 13 hygiene tests and the 37 assertions, the models before and after the change, and the ProVerif and Tamarin logs of the captured-variable counterexample. The script `audit_fix.py` produced them in the directory layout of that session. The directory [`v0.1.2/out/`](v0.1.2/out/) holds generated models of the two signers.

The hash list [`validation/plan/generator.txt`](../validation/plan/generator.txt) fixes the nine source files of version 0.1.2, and `python3 -B scripts/verify_evidence.py` compares them with it.
