# Boundary probes of series V2

The probes test the side-condition checks of the generator. Each probe is a small CIM. Two controls stay inside the fragment of the generator, and every other probe leaves it in one respect. The tables [`expected.tsv`](expected.tsv) and [`probes_pair/expected_pair.tsv`](probes_pair/expected_pair.tsv) state the expected answer of the generator and the difference between the tools that each probe predicts if the generator accepts it.

| Path | Content |
| --- | --- |
| [`probes/`](probes/) | The twelve probes of the plan |
| [`probes_controls/`](probes_controls/) | The two controls with a pair-shaped input |
| [`probes_pair/`](probes_pair/) | Four of the probes outside the fragment with a pair-shaped input |
| [`sets/fixed/`](sets/fixed/) | Answers of generator 0.1.2 to the twelve probes and the records of the two probes with model files |
| [`sets/controls/`](sets/controls/) | Model sets and records of the two controls |
| [`sets/pair/`](sets/pair/) | Model sets and records of the four pair-shaped probes |
| [`run_boundary.py`](run_boundary.py) | Compiles the probes and, with `--provers`, runs both tools |

## Twelve probes of the plan

Generator 0.1.2 refuses all ten probes outside the fragment. It writes model files for the probes `b03_overlap` and `b04_two_silent`, whose check `Det` fails. On these two sets ProVerif reaches both events with one message and Tamarin admits one, which gives 4 excluded pairs in 16 records.

Generator 0.1.2 also refuses the two controls, because their input pattern consists of one constant. The controls under `probes_controls/` use the input `tup('ctl', ...)` and pass all checks. Their 40 records hold 39 verdicts, no excluded pair and agreement on all 5 properties on the standard system.

For four probes outside the fragment (`b05`, `b06`, `b08` and `b10`), the only failed check is this check of the input pattern, so the refusal says nothing about the condition that they test. The pair-shaped probes repeat these four with the input `tup('ctl', ...)`, and `b13_numeral_literal_pair` is the repetition of `b06_numeral_literal`.

## Four pair-shaped probes

The run of 25 November 2026 used generator 0.1.2, ProVerif 2.05, Tamarin 1.12.0 and Maude 3.5.1 with limits of 120 s per ProVerif file, 300 s per Tamarin lemma and a heap of 4 GiB. Each probe contributes four ProVerif queries and four Tamarin lemmas. All 32 runs ended with a verdict and exit status 0.

| Probe | Generator 0.1.2 | Generator 0.1.3 | Verdicts | Excluded pairs |
| --- | --- | --- | --- | --- |
| `b05_mixed_dispatch_pair` | refuses, `Det` | refuses | 8 of 8 | 2 |
| `b08_unpublished_identity_pair` | refuses, `LeakGuard` and `LeakUse` | refuses | 8 of 8 | 6 |
| `b10_event_order_pair` | refuses, `EvtSep`, `Blk` and `ObsOne` | refuses | 8 of 8 | 11 |
| `b13_numeral_literal_pair` | accepts | refuses, `Hygiene` | 8 of 8 | 6 |

The runner exercises the model files of every probe, including the three probes with a failed check. Each probe shows at least one excluded pair, 25 in total, and the two tools disagree on the standard system for all four properties. The cross-tool comparison therefore exposes each of these faults without the checks.

The probe `b13_numeral_literal_pair` is the third counterexample of the paper. It uses the string literal `'n1'`, which the Tamarin back end prints as the numeral 1 and the ProVerif back end prints as a different constant. Generator 0.1.2 accepts the probe without a failed check. ProVerif then proves the acceptance event unreachable in all four encodings, and Tamarin verifies its reachability in all four variants in four steps each. Generator 0.1.3 refuses the probe and writes no model.

| File under `sets/pair/` | Content |
| --- | --- |
| `boundary_generator.tsv`, `boundary_pairs.tsv` | Answers of generator 0.1.2 and counts per probe |
| `boundary_xcheck.json`, `boundary_xcheck.txt` | Cross-check of the 32 verdicts |
| `raw-verdict-lines.tsv` | Verdict line and SHA-256 hash of each of the 32 complete tool outputs |
| `generator-0.1.3/` | Answers of generator 0.1.3, its message for `b13` and the log of its five literal tests |

## Commands

```bash
work=$(mktemp -d)
python3 -B validation/V2-boundary/run_boundary.py --cimc cimc/v0.1.2 --out "$work/fixed"
python3 -B validation/V2-boundary/run_boundary.py --cimc cimc/v0.1.3 \
    --probes validation/V2-boundary/probes_pair \
    --expected validation/V2-boundary/probes_pair/expected_pair.tsv --out "$work/pair"
python3 -B validation/common/xcheck.py validation/V2-boundary/sets/pair/b*/
```

The first command repeats the generator step for the twelve probes and ends with status 1, because it reports the two refused controls as mismatches. The second command shows that generator 0.1.3 refuses all four pair-shaped probes. The third command recomputes the cross-check from the stored verdicts. It reports 4 sets, 32 conclusive records, 4 disagreements on the standard system and 25 excluded pairs, and it ends with status 1 because excluded pairs exist.
