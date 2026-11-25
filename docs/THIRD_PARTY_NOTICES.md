# Third-party notices

This repository redistributes or modifies the following material of other authors. This material keeps its own licenses, and the [MIT License](../LICENSE) of the repository does not apply to it.

| Component | Source | License and notes |
| --- | --- | --- |
| Patches for the Tamarin exporter | [Tamarin Prover](https://github.com/tamarin-prover/tamarin-prover), fork commit [`c293106913cc`](https://github.com/felixlinker/tamarin-prover/tree/c293106913ccf7bb41f49b0dc555a8074e8ea88c) | GNU GPL version 3. The modified source file carries the copyright notice of Julian Biehl. The [license text](../exporter/patches/TAMARIN-LICENSE) accompanies the patches, and the [exporter notes](../exporter/README.md) describe the two modifications of 15 November 2026. |
| Evaluation data of the translation artifact | Kevin Morio, Yavor Ivanov and Robert Künnemann, *A Sound Translation from Tamarin to ProVerif: Enabling Comparative Analysis*, [artifact DOI 10.5281/zenodo.21827126](https://doi.org/10.5281/zenodo.21827126) | The artifact dedicates its evaluation data to the public domain (CC0) and distributes its source under GNU GPL version 3. The [CC0 text](../corpus/morio/CC0-1.0.txt) accompanies the data. The Dockerfile under [`env/fixed-ccs26/`](../env/fixed-ccs26/) and the Dockerfiles under [`exporter/recipes/`](../exporter/recipes/) record the pinned build and the changes of the three exporter builds. |
| Public theory corpus | Eight Tamarin theories that [`corpus/corpus.tsv`](../corpus/corpus.tsv) attributes to their authors | The repository holds the hashes and the upstream paths of the theories and no copy of them. The script [`corpus/get_kudos_model.sh`](../corpus/get_kudos_model.sh) fetches the KUDOS model from its source. |
| Provers and container dependencies | ProVerif, Tamarin, Maude and the packages of the container image | The build recipes fetch these tools from their distributors. The repository holds recipes and recorded binary hashes and no binary. |

The GNU GPL requires that a modified source keeps its copyright and license notices and states the modification and its date. The patches under [`exporter/patches/`](../exporter/patches/) keep these notices.

Tool outputs in the run directories quote the messages of ProVerif, Tamarin, Maude and Docker without change.
