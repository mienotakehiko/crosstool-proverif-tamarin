# Correction of the first patch for inputs, build B3 (follow-up of series V6)

The benchmark comparison of series V6 finds one theory for which the exporter build B2 writes a file that ProVerif rejects ([notes](../benchmark/README.md)). This directory holds the records that locate the rejected line, the build B3 that corrects the first patch for inputs, and the runs of B3. The follow-up dates from 27 November 2026 and states no prediction.

## Builds

| Build | Source | SHA-256 of the exporter binary |
| --- | --- | --- |
| B2 | Pinned commit with [`all-translator-fixes.patch`](../../../exporter/patches/all-translator-fixes.patch) | `a07b24ef01cbd12b3eba99491d9b980f1561ec2df41a8137d0fe2f4744dbd6f5` |
| B3 | B2 with [`input-equality-pattern.patch`](../../../exporter/patches/input-equality-pattern.patch) | `59a810bf9494eca1476cfc344ee1f657e2c327c4c31d7721ba4375afa10ef9fc` |

The patch changes the input branch of the function `translatePatternFact` in `lib/export/src/Export/ProVerif/Rule.hs`. An input whose pattern is an equality pattern no longer carries the type `bitstring`. The patched file has the SHA-256 hash `ece58c7131e460541c2db6ee5e42d66839d7165230f6ff1e6a9e3d0468b3bcda`. The directory `lib/export` is identical at the pinned commit `c293106913cc`, at the commit `a75fec7ff13c` of the upstream report and at the head `011643205781` of the upstream development branch of 26 November 2026, so the three patches yield the same file at each of these commits.

## The rejected line of B2

The first run exports the lemma `Login_reachable` of `examples/related_work/YubiSecure_KS_STM12/Yubikey.spthy` with B2 in the container image of the benchmark comparison and passes the file to ProVerif. The export ends with exit code 0, and ProVerif ends with exit code 2 and the following message.

```
File "/out/yubikey_b2.pv", line 99, character 36:
Error: Syntax error.
```

The rule `InitSucc` of the theory has the premises `In(myzero)` and `In(S(myzero))`. Lines 99 and 100 of the export translate them, and character 36 of line 99 is the colon.

```
let rInitSucc =
        in(publicChannel, =myzero(): bitstring);
        in(publicChannel, =S(myzero()): bitstring);
```

The first patch writes the equality pattern for a term without variables and names, the input branch appends the type to every pattern, and the grammar of ProVerif admits no type after an equality pattern.

## The export of B3

The second run repeats the export with B3 and calls ProVerif with the option `-parse-only`. ProVerif ends with exit code 0. The two exports differ in lines 99 and 100 and in the line that states the build time.

```
let rInitSucc =
        in(publicChannel, =myzero());
        in(publicChannel, =S(myzero()));
```

In this mode ProVerif parses the file and evaluates no query, so its summary reads `No query in the input file.` although the export contains a query.

## The five pairs of the YubiKey theory under B3

The third run passes the five pairs of the theory through the evaluation scripts of the artifact with the limits of the benchmark comparison, 300 s and 8,192 MB. The B3 binary replaces the exporter of the B2 image by a read-only mount, and every other file of the image stays the same. A separate pass calls ProVerif with `-parse-only` on each export.

| Index | Lemma | B0 | B2 | B3, parser | B3, ordinary run |
| --- | --- | --- | --- | --- | --- |
| 433 | `Login_reachable` | No result | Syntax error | Accepted | No result after 75.007 s |
| 434 | `no_replay` | Time limit | Syntax error | Accepted | Time limit |
| 435 | `slightly_weaker_invariant` | Time limit | Syntax error | Accepted | Time limit |
| 436 | `injective_correspondance` | Time limit | Syntax error | Accepted | Time limit |
| 437 | `Login_invalidates_smaller_counters` | Time limit | Syntax error | Accepted | Time limit |

ProVerif parses all five exports of B3, and each pair returns to the outcome class that it has under B0. No build yields a definitive outcome for any of the five pairs, and the published run of the artifact decides none of them either.

## The regression of series X1 under B3

The fourth run repeats the regression of step 8 of series X1 with the B3 binary, in the fixed image of that step and with its 21 models and 60 pairs of model and lemma. The translated route agrees with native Tamarin on all 60 pairs, and all 180 stages end with exit code 0 and within their limit. Every pair has the outcome that it has under B2, and the 60 exports equal the exports of B2 apart from the line that states the build time. The models of the regression set contain no input fact, so the patch leaves their exports unchanged.

## The other 561 pairs of the benchmark

The other 561 pairs need no run under B3, because the records of B2 and the patch determine their exports.

The patch changes an export only where B2 writes a type after an equality pattern of an input. ProVerif rejects every such file at its parser, as it does for the five pairs above. Under B2, ProVerif reports a syntax error for these five pairs and for no other pair of the benchmark.

| Pairs | Outcome under B2 | Consequence for B3 |
| --- | --- | --- |
| 521 | A verdict, a limit, no result or the message that the equations lack a termination proof. Each of these outcomes follows the parser | The export of B2 contains no such input, so B3 writes the same file apart from the line that states the build time |
| 40 | The formula translation declines the lemma for a KU fact or, in an exists-trace lemma, for a K fact. B0 reports the same message | The three patches change the file `lib/export/src/Export/ProVerif/Rule.hs` alone, and the formula translation lies in `Formula.hs` of the same directory |

A textual scan of the 121 theories agrees with this result. It finds an input of a term without variables and names in the rule `InitSucc` alone.

## Scope

- The five pairs have no definitive outcome under any build. The runs show that the syntax error is gone and say nothing about the lemmas.
- The statement on the other 561 pairs follows from the rows of B2 and from the patch. It rests on no run of B3 for these pairs.
- The records hold no export of the unmodified exporter B0 for this theory. By a reading of the source, B0 writes such an input as a helper variable without a check and accepts every message there.
- The rows of the runs record that the exporter omits the restriction `smaller_implies_unequal` of the theory under B0, B2 and B3, and the stored exports of B2 and B3 state the omission.
- The patch comes without a proof of semantic preservation and without a review by the maintainers of the exporter.

## Files

| Path | Content |
| --- | --- |
| [`single/b2/`](single/b2/), [`single/b3/`](single/b3/) | Commands, exit codes, logs, hashes and the export of the lemma `Login_reachable` under each build |
| [`single/b2-b3.diff`](single/b2-b3.diff) | Difference of the two exports |
| [`build/`](build/) | Build log of B3, the patch, the difference of the source file and the hashes of the patched file and of the binary |
| [`five_pairs/`](five_pairs/) | Conditions, summary table and, for each index, the records of the parser pass and of the ordinary run |
| [`regression/`](regression/) | Stage files, summaries and inputs of the regression under B3, in the layout of [`runs/X1/step8/`](../../../runs/X1/step8/) |
| [`regression_console.log`](regression_console.log) | Console output of the regression run |
| [`scripts/single/`](scripts/single/) | Scripts of the single exports and of the build, with the hash list of their kit |
| [`scripts/five_pairs/`](scripts/five_pairs/) | Script of the run of the five pairs with its two wrappers, its reference data and the hash list of its kit |
| [`summarize_b3.py`](summarize_b3.py) | Recomputes the counts of this page from the records |
| [`summary.txt`](summary.txt) | Output of that script |

The build script unpacks the build kit of B2, which the repository holds as [`exporter/recipes/step7/`](../../../exporter/recipes/step7/). The exports derive from a theory of the Tamarin repository, and the [third-party notices](../../../docs/THIRD_PARTY_NOTICES.md) state its license. In 36 records, a placeholder replaces the home directory of the runs, and the run script of the five pairs carries English messages in place of the original ones. The table [`registry/normalized-files.tsv`](../../../registry/normalized-files.tsv) lists these files with both hashes. The kits of the runs also contain instructions and notes in Japanese. The repository leaves them out, and the hash lists still name them.

## Recompute

```bash
python3 -B validation/V6-exporter/b3_followup/summarize_b3.py
```

The command reads the records and starts no tool. Its output equals [`summary.txt`](summary.txt).
