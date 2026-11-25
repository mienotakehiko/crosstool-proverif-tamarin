# Series X1, exporter regression

Series X1 runs 60 pairs of model and lemma from 21 theories through three builds of the exporter and compares each translated ProVerif verdict with the native Tamarin verdict. The [exporter notes](../../exporter/README.md) describe the builds B0, B1 and B2.

| Path | Content |
| --- | --- |
| [`comparison.tsv`](comparison.tsv) | Native verdict and translated verdict under each build for the 60 pairs |
| [`jobs.tsv`](jobs.tsv) | Index of the 540 stage invocations with exit status and metadata path |
| [`provenance.json`](provenance.json) | Base commit and hashes of the three exporter binaries |
| [`step3/`](step3/) to [`step8/`](step8/) | Build logs, inputs, commands and stage files of the six steps of the study |
| [`historical-probes/`](historical-probes/) | The 64 comparisons of the four probes that preceded the regression |

The builds agree with native Tamarin on 49, 59 and 60 of the 60 pairs. Each pair has the three stages native, export and pv under each build, which gives 540 invocations, and all of them ended with exit status 0.

```bash
python3 -B exporter/index_regression.py
python3 -B scripts/recompute_paper_numbers.py
```

The first command rebuilds `jobs.tsv` from the summaries, exit codes and metadata of the stages and compares it with the stored index. The theories of the regression are in [`step8/inputs/models/`](step8/inputs/models/).

The hash lists in the step directories name the binaries and the kit archives of the runs, which this repository does not hold. The recorded hashes identify them.
