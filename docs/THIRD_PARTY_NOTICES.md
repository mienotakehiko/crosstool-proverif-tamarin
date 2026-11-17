# Third-party notices

| Component | Source and distribution notes |
| --- | --- |
| Tamarin exporter and patches | [Tamarin Prover](https://github.com/tamarin-prover/tamarin-prover), pinned fork revision [c293106913cc](https://github.com/felixlinker/tamarin-prover/tree/c293106913ccf7bb41f49b0dc555a8074e8ea88c). The source file carries Julian Biehl's copyright notice and GPL v3 designation. The [GPL v3 text](../exporter/patches/TAMARIN-LICENSE) accompanies the modified source and patches. The B1 and B2 modifications dated 2026-11-15 are identified in the [exporter notes](../exporter/README.md). |
| CCS 2026 evaluation artifact | Kevin Morio, Yavor Ivanov and Robert Künnemann, *A Sound Translation from Tamarin to ProVerif: Enabling Comparative Analysis*, [artifact DOI 10.5281/zenodo.21827126](https://doi.org/10.5281/zenodo.21827126). The original artifact designates its evaluation data CC0 and packaged source GPL v3. The [local CC0 text](../corpus/morio/CC0-1.0.txt) accompanies the dataset. The evaluation Dockerfile variants under `env/fixed-ccs26/` and `exporter/recipes/` record the pinned upstream build and the changes used in the controlled builds. |
| External theory corpus | The [corpus registry](../registry/corpus.tsv) gives the eight attributions and input hashes. The KUDOS retrieval script fetches the pinned source separately. Recorded verdicts and derived statistics cite the upstream theories. |
| Container and prover dependencies | Build recipes fetch the specified dependencies from their upstream distributions. The release contains recipes and recorded binary hashes. |

For Tamarin-derived source, keep copyright and license notices and identify the modifications and their dates. See the [GNU GPL v3, sections 4 and 5](https://www.gnu.org/licenses/gpl-3.0.html). The six original X1 bundles have a separate rights status because each archive mixes research records, commands, tool output and, in some cases, copied source. The release carries the reviewed extracted records. The original bundles remain outside it pending confirmation for archive-wide redistribution.

The supplied materials specify no repository-wide license for the author's original code and data. Confirm the intended terms and applicable rights before publishing the release candidate.
