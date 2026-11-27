# Executable checks of the scheduler lemmas

Appendix B of the paper states two lemmas about the scheduler that links the atomic steps of a Common Iterative Model to the steps of the printed ProVerif process. This directory holds one executable check for each lemma. Both checks enumerate finite systems within stated bounds. They support the lemmas and replace no proof.

## Lemma 1, restricted scheduler

The suite in [`lemma1/`](lemma1/) builds one fixture model with a single initialized thread and compares the atomic scheduler with the scheduler of the process on ground terms. The fixture has 3 atomic states and 13 process states, including 3 abandoned states, and both sides produce the same 3 observable words.

```bash
python3 -B scheduler/lemma1/run_checks.py
```

The command copies the generator snapshot under `lemma1/snapshot/` to a temporary directory, regenerates the fixture models and runs 21 tests. The stored files `tests.log` and `results.json` record the 21 passes of the original run, and the `*.log` files record the ProVerif and Tamarin outputs on the fixture models. The option `--with-provers` repeats these prover runs.

The fixture models `overlap`, `unbound_guard`, `undefined_guard`, `scalar_pattern` and `capture` leave the fragment of the lemma in one respect each. The tests record how generator 0.1.1 treats each of them, and the stored logs show the answers of both provers.

## Lemma 2, unrolled scheduler

The script [`lemma2/unrolled_check.py`](lemma2/unrolled_check.py) implements the atomic scheduler and the unrolled scheduler as the appendix defines them and compares their sets of observable words for a given model.

```bash
bash scheduler/lemma2/run_checks.sh
```

| Suite | Models | Bounds | Expected result |
| --- | --- | --- | --- |
| A | two signer models, two controls and 200 random models (seed 20261116) | one thread, four events | equal sets |
| B | twelve family models | one thread, three events | equal sets |
| C | five models of suite A | two threads, three events | equal sets |
| D | three models with overlapping dispatch and one with an unpublished identity | one thread, four events | different sets |

The run takes about five minutes and reports 204, 12, 5 and 4 models without an unexpected result, which gives the 225 enumerations of series V5. The file [`lemma2/reference-run.log`](lemma2/reference-run.log) is the output of the run of 17 November 2026.

Suite D shows that the conditions of the lemma matter. If two cases of one state accept one message, the unrolled system continues both, as the parallel composition of the printed process does, and produces words with two events that the atomic system lacks. If the thread publishes no identity, the leak block of the unrolled system never runs.

## Reveal alternative

The script [`lemma2/predict_reveal.py`](lemma2/predict_reveal.py) uses the atomic scheduler for a second question. It reports whether every acceptance follows its signing or release event, with and without the alternative that a revealed seed excuses the acceptance.

```bash
python3 -B scheduler/lemma2/predict_reveal.py --cimc cimc/v0.1.2 --checker scheduler/lemma2 \
    validation/V1-families/inputs/fixed/lmots_w2m1.toml validation/V1-families/inputs/renamed/otp_n2.toml
```

For the LM-OTS signer the property holds in both readings, because a private function hides the chain values from an attacker who holds the seed. For the one-time password family it fails without the alternative. The [reveal follow-up](../validation/V1-families/reveal_followup/README.md) of series V1 puts this prediction to both provers. With a public derivation function, the property of the signers fails without the alternative as well, and the [public-derivation follow-up](../validation/V1-families/public_derivation_followup/README.md) puts that prediction to both provers.
