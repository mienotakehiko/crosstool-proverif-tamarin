# Restricted scheduler lemma

[Restricted suite and evidence](restricted_20261111/) contains the Appendix B Lemma 1 fixture, the exact saved test log, supplementary model outputs, and the source snapshot. The suite concerns a single initialized ground thread and the fixture's relevant-term closure. The archived fixture explores 3 atomic states and 13 worker states, including 3 abandoned states, with 3 observed words on each side. The checks establish the stated fixture properties within that scope.

From the repository root, run:

```bash
python3 -B scheduler/restricted_20261111/run_checks.py
```

The replay runs 21 Python tests using a temporary output directory. The runner uses the archived input snapshot and leaves it intact. The optional `--with-provers` also starts the historical ProVerif and Tamarin commands if the tools are available. The release audit reran the Python suite and checked the saved prover outputs by provenance. Full semantic equivalence of ProVerif and Tamarin, branching bisimulation and liveness fall outside the premise of this suite.
