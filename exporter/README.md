# Exporter study

Series X1 examines the exporter that translates a Tamarin theory into a ProVerif model. The study starts at commit `c293106913ccf7bb41f49b0dc555a8074e8ea88c` of the development branch of Tamarin and compares three builds.

| Build | Source |
| --- | --- |
| B0 | The exporter of the pinned commit without change |
| B1 | B0 with [`leafless_ground_candidate.patch`](patches/leafless_ground_candidate.patch) |
| B2 | B0 with [`all-translator-fixes.patch`](patches/all-translator-fixes.patch), which equals the patch of B1 followed by [`row-id-guards.patch`](patches/row-id-guards.patch) |

Both modifications date from 15 November 2026. The file [`patches/TAMARIN-LICENSE`](patches/TAMARIN-LICENSE) is the license of the modified source.

## Contents

| Path | Content |
| --- | --- |
| [`probes/initial/`](probes/initial/) | Kit of four state-machine models with a constant and a constructor encoding of the state. All 16 comparisons with native Tamarin agree |
| [`probes/zero-argument/`](probes/zero-argument/) | Kit with a nullary and a successor encoding of the state, which exposes the disagreement. 10 of 16 comparisons agree |
| [`probes/source/`](probes/source/) | Probe on the pinned source with the script that collects the identity of the build. 13 of 16 comparisons agree |
| [`probes/guarded/`](probes/guarded/) | Comparison of the saved translation with explicit guards on the state. All 16 comparisons agree |
| [`recipes/step3/`](recipes/step3/), [`recipes/step7/`](recipes/step7/), [`recipes/step8/`](recipes/step8/) | Dockerfiles, build scripts and regression inputs of the three builds |
| [`index_regression.py`](index_regression.py) | Rebuilds the index of the 540 stages from the stored stage files |

The table [`runs/X1/historical-probes/state_comparisons.tsv`](../runs/X1/historical-probes/state_comparisons.tsv) holds the 64 comparisons of the four probes. The records of the regression are in [`runs/X1/`](../runs/X1/). The table [`runs/X1/comparison.tsv`](../runs/X1/comparison.tsv) reports 49, 59 and 60 agreements with native Tamarin among the 60 pairs of model and lemma for B0, B1 and B2. The file [`runs/X1/provenance.json`](../runs/X1/provenance.json) states the base commit and the hashes of the three binaries.

## Checks

```bash
python3 -B exporter/index_regression.py
(cd exporter/probes/initial && python3 -B -m unittest -v test_kit)
```

The first command confirms that all 540 stage invocations ended with exit status 0 and that the stored index follows from the stage files. The second command runs the 14 unit tests of the first probe kit, which need no container.

The builds used a fixed local runtime and shared dependencies. The records establish the identity of each build and the results of its stages. A bit-for-bit reconstruction of the binaries would also need the exact runtime of each build, which the repository lacks.

The validation series V6 repeats two probes on the upstream head of Tamarin. Its records are in [`validation/V6-exporter/`](../validation/V6-exporter/). The pinned commit lies on the same branch, and the directory `lib/export` is identical at the pinned commit and at that head (`03215cd03e7c`). The author reported both defects to the upstream project as [issue 996](https://github.com/tamarin-prover/tamarin-prover/issues/996).

## Benchmark of the artifact and a limit of the first patch

Series V6 also runs the 121 theories of the translation artifact with B0 and with B2 ([notes](../validation/V6-exporter/benchmark/README.md)). Both builds decide the same 308 of the 566 pairs of theory and lemma, and the outcomes are equal. For the theory `examples/related_work/YubiSecure_KS_STM12/Yubikey.spthy`, ProVerif rejects the export of B2 with a syntax error.

The first patch causes this error. For a term without variables and names, the patch writes an equality pattern. The input branch of `translatePatternFact` appends `: bitstring` to every pattern, and the grammar of ProVerif admits no type after an equality pattern. The rule `InitSucc` of the theory reads `In(myzero)` and `In(S(myzero))`, so its export contains an input whose pattern has the form `=t: bitstring`. This explanation follows from the patched source, because the benchmark run stored no exported file. B1 contains the same patch.

The patch therefore needs a correction that omits the type after an equality pattern of an input, as the function `translateFact` of the exporter does for an input without a pattern. The repository holds no such correction. The 21 models of the regression set contain no input fact, so the regression of series X1 could not show the error.
