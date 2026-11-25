# Records of the series G to K

Each subdirectory holds the records of one series of the paper. A record states the model with its SHA-256 hash, the lemma or query, the limits, the exit status and the verdict of one run. The command `python3 -B scripts/recompute_paper_numbers.py` recomputes every count that the paper reports for these series.

| Directory | Series | Content |
| --- | --- | --- |
| [`G/`](G/) | G | 28 ProVerif verdicts of the first run on the sixteen generated signer models. The rerun of both tools is in the two control sets of [series V4](../validation/V4-mutation/) |
| [`screening/`](screening/) | P1 to P4 | Cumulative record of all screening attempts. The last attempt of a job counts |
| [`P1/`](P1/), [`P2/`](P2/), [`P3/`](P3/), [`P4/`](P4/) | P1 to P4 | Job table, final record of every job and archived prover outputs |
| [`P5/`](P5/) | P5 | Records of 1,125 repeated trials with their memory curves and runtime statistics |
| [`L/`](L/) | L | Nine runs with heap limits of 8, 16 and 32 GiB with their outputs, and seven runs at 96 GiB |
| [`M/`](M/) | M | Pilot, main experiment and frozen re-evaluation of the mutation study ([notes](M/README.md)) |
| [`X0/`](X0/) | X0 | Translation of the hand-written theories before and after the renaming fix |
| [`X1/`](X1/) | X1 | Exporter regression on three builds with all stage files ([notes](X1/README.md)) |
| [`X2/`](X2/) | X2 | Exporter applications to LMS and HSS ([notes](X2/README.md)) |
| [`K/`](K/) | K | Finite KUDOS schedules ([notes](K/README.md)) |
| [`chain/`](chain/) | chain theory | Summary of the seven native Tamarin properties of the theory `C1_E1g` |

## Screening and repetition

The fields of a screening record are the job name, the time, the tool (`std` for Tamarin 1.12.0, `cyc` for the cyclic build), the model with its hash, the lemma, the heuristic, the search mode, the heap limit, the time limit, the exit status, the elapsed seconds, the verdict, the proof steps and the memory measures. The verdicts are `verified`, `falsified`, `TIMEOUT`, `HEAP`, `KILLED` and `ERROR`.

The files under `P1/raw/` to `P4/raw/` are the prover outputs. For P2 the repository holds the outputs, memory curves and runtime statistics of nine jobs. The files under `P5/raw/` are the memory curve and the runtime statistics of every trial. The outputs of P3 and P5 use the names `rank-lower-s` and `rank-upper-s` for the heuristics `s` and `S`, because some file systems ignore case.

## Series X0

| Path | Content |
| --- | --- |
| [`X0/original/triangulation.jsonl`](X0/original/triangulation.jsonl) | 62 records of the first translation run |
| [`X0/alpha-fix/`](X0/alpha-fix/) | 15 reruns after the renaming fix, each with the translated input, the ProVerif output, the container log and a result record |
| [`X0/post-rename.tsv`](X0/post-rename.tsv) | Outcome of the 40 pairs of model and lemma before and after the fix |
| [`X0/resource-limited/correspondence_24.tsv`](X0/resource-limited/correspondence_24.tsv) | 24 translated runs that ended at a resource limit and have no matched direct result |

## Series L

The records under `L/ladder/` belong to three jobs that exhausted a heap of 56 GiB in series P2. Each job ran again with limits of 8, 16 and 32 GiB, and all nine runs ended with heap exhaustion and exit status 251. The time to exhaustion grows with the limit, which the figure of the paper shows together with the three reference points at 56 GiB from `P2/records.jsonl`. The records under `L/heap96/` belong to the seven jobs that ran on a cloud host with a limit of 96 GiB and exhausted it as well.
