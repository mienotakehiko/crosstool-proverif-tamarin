# Series K, finite KUDOS schedules

Series K compares both tools on twelve finite schedules of the KUDOS key update. Each schedule models stated assumptions for one conditional scenario.

| Path | Content |
| --- | --- |
| [`specification-index.tsv`](specification-index.tsv) | Specification and generator of each of the 12 schedules |
| [`jobs.tsv`](jobs.tsv) | The 24 model inputs, one ProVerif and one Tamarin input per schedule, with their SHA-256 hashes |
| [`direct/`](direct/) | Outputs of the direct runs of both tools |
| [`stage-d/stage_d_results.tsv`](stage-d/stage_d_results.tsv) | Comparison per lemma, with 49 comparisons of the original stage and 12 of a diagnostic stage |
| [`archives/`](archives/) | Inputs, records per lemma and summaries of the comparison stage |

The original stage agrees on 48 of its 49 comparisons. The specifications live in [`cim/kudos/`](../../cim/kudos/), and the source of the schedule group RB1 holds two schedules in one file.

```bash
python3 -B scripts/check_kudos_models.py
```

The command runs every generator on its specification and confirms that all 24 regenerated inputs are byte-identical to the archived inputs.
