# Reproduction guide

This guide explains how to repeat the prover runs of the paper. The checks of the [README](../README.md) need Python only and confirm that the archived records yield the reported counts. The runs below need the provers and produce new records that a reader can compare with the archived ones.

## Tools

| Tool | Version of the runs | Use |
| --- | --- | --- |
| ProVerif | 2.05 | all direct ProVerif runs |
| Tamarin | 1.12.0 with Maude 3.5.1 | standard build of all Tamarin runs |
| Tamarin, cyclic build | 1.11.0 with Maude 3.5 | jobs with the tool name `cyc` in the series P1 to P5 and L |
| Python | 3.11 or later | generator, runners and checks |
| Container image of the exporter study | image of the artifact of Morio et al. at Tamarin commit `c293106913cc` | series X0, X1, X2 and K |

The environment records in [`env/`](../env/) state the hosts, the tool versions and the pinned commits. The validation series ran on a WSL2 host with 8 processors and 58 GiB of memory. The screening series used heap limits up to 56 GiB, and seven jobs of series L ran on a cloud host with 126,757 MB of memory under a heap limit of 96 GiB.

Run times and memory use depend on the host. A reproduction succeeds if the verdicts agree. Jobs that ended at a time or memory limit in the archived records may end with a verdict on a larger host, and the paper reports such jobs as runs without a verdict.

## Generated models in both tools (series G, V1, V2 and V4)

The runner [`validation/common/run_family.sh`](../validation/common/run_family.sh) compiles every CIM of a directory with generator 0.1.2, runs both provers on the eight generated models and cross-checks the verdicts. The following command repeats the two signers of series G in a new directory.

```bash
work=$(mktemp -d)
mkdir "$work/inputs" && cp cim/signers/*.toml "$work/inputs/"
bash validation/common/run_family.sh "$work/inputs" "$work/sets" --pv-timeout 600 --tm-timeout 3600 --heap 16g
python3 -B validation/common/xcheck.py "$work"/sets/*/
```

The same runner repeats the other series with the inputs and first limits of the following table. A second call with `--retry-unresolved` and larger limits repeats the jobs without a verdict. Every archived record states the limits of its own run in the fields `timeout_s` and `heap_cap`.

| Series | Inputs | ProVerif limit | Tamarin limit | Heap |
| --- | --- | --- | --- | --- |
| V1, LM-OTS family | the five `lmots_*.toml` of [`inputs/fixed/`](../validation/V1-families/inputs/fixed/) | 600 s | 300 s | 16g |
| V1, LMS and OTP families | [`inputs/renamed/`](../validation/V1-families/inputs/renamed/) | 600 s | 300 s | 16g |
| V2, random models | [`inputs/renamed/`](../validation/V2-random/inputs/renamed/) | 60 s | 60 s | 8g |
| V4, mutants | sets written by [`mutate.py`](../validation/V4-mutation/mutate.py) | 600 s | 300 s | 56g |

The LMS family of V1 and the two control probes of V2 used [`run_set_monotonic.py`](../validation/common/run_set_monotonic.py), which differs from `run_set.py` only in the clock. For the mutants of V4, write the sets first and then call `run_set.py` on each set.

```bash
for signer in lmots lms_s2; do
  python3 -B validation/V4-mutation/mutate.py --cimc cimc/v0.1.2 cim/signers/$signer.toml "$work/mutants"
  python3 -B validation/V4-mutation/mutate.py --cimc cimc/v0.1.2 cim/signers/$signer.toml "$work/mutants" --ops property
done
for set in "$work"/mutants/*/; do
  python3 -B validation/common/run_set.py "$set" --pv-timeout 600 --tm-timeout 300 --heap 56g
done
python3 -B validation/V4-mutation/score.py "$work/mutants"
```

## Boundary probes (series V2)

The option `--provers` of [`run_boundary.py`](../validation/V2-boundary/run_boundary.py) runs both tools on every probe whose model files exist. The command for the four pair-shaped probes follows. It takes a few seconds per probe.

```bash
python3 -B validation/V2-boundary/run_boundary.py --cimc cimc/v0.1.2 \
    --probes validation/V2-boundary/probes_pair \
    --expected validation/V2-boundary/probes_pair/expected_pair.tsv \
    --out "$work/boundary-pair" --provers
```

The generator step reports one mismatch, because generator 0.1.2 accepts the probe `b13_numeral_literal_pair`, and the prover step reports excluded pairs for all four probes. The script therefore ends with status 1. With `--cimc cimc/v0.1.3` the generator refuses all four probes.

## Tamarin screening (series P1 to P5, L and V7)

The kit in [`models/tamarin-kit-v3/`](../models/tamarin-kit-v3/) derives the variants of the hand-written theories and proves one lemma per call. The tables `runs/P1/jobs.tsv` to `runs/P4/jobs.tsv` list every job with its tool, model, lemma, heuristic, search mode, heap limit and time limit.

```bash
python3 -B models/tamarin-kit-v3/tactics/make_variants.py
bash models/tamarin-kit-v3/run_one_v3.sh P1_std_HSS_LS7_inj_T0_exec_d_prove std variants/HSS_LS7_inj__T0.spthy exec default prove 56g 3600
```

The runner writes `results/records.jsonl` and the raw outputs below the kit directory, and `.gitignore` excludes both. The tool name `cyc` needs the binary `tamarin-cyclic` and the variable `MAUDE_CYC`. The corpus theories of P4 come from their upstream sources, which [`corpus/README.md`](../corpus/README.md) names. Series P5 repeats a job five times with the job names `P5_<job>_r1` to `P5_<job>_r5`. Series L repeats three jobs with the heap limits 8g, 16g and 32g. Series V7 repeats the ten jobs of [`jobs_e7.tsv`](../validation/V7-time-limit/jobs_e7.tsv) with a time limit of 14,400 s, and [`select_jobs.py`](../validation/V7-time-limit/select_jobs.py) prints their commands.

## Scheduler lemmas

```bash
python3 -B scheduler/lemma1/run_checks.py --with-provers
bash scheduler/lemma2/run_checks.sh
```

The first command repeats the seven ProVerif runs and the three Tamarin runs of the fixture models of Lemma 1. The second command needs no prover.

## Series with the scripts of the original runs (M, X0, X1, X2 and K)

These series ran in the working directories and containers of the original study. The repository keeps their scripts as records of the procedure, together with every input and output. The scripts expect the directory layout of those runs, so a repetition calls the provers on the archived inputs.

| Series | Inputs | Procedure |
| --- | --- | --- |
| M | `model.pv` and `model.spthy` of each case in [`runs/M/historical/`](../runs/M/historical/), frozen inputs in [`runs/M/frozen_20261111/pv/`](../runs/M/frozen_20261111/pv/) and [`tm/`](../runs/M/frozen_20261111/tm/) | `proverif FILE` and `tamarin-prover --prove FILE`, as the scripts in the same directories record |
| X0 | translated inputs in [`runs/X0/alpha-fix/`](../runs/X0/alpha-fix/) | `proverif FILE` inside the pinned image |
| X1 | theories in [`runs/X1/step8/inputs/models/`](../runs/X1/step8/inputs/models/), patches in [`exporter/patches/`](../exporter/patches/) | build the three exporters with the recipes in [`exporter/recipes/`](../exporter/recipes/), then run `run-step8.sh` |
| X2 | theories and translated inputs in the subdirectories of [`runs/X2/`](../runs/X2/) | the run script of each subdirectory states its container command |
| K | 24 model inputs that [`runs/K/jobs.tsv`](../runs/K/jobs.tsv) lists | `proverif FILE` and `tamarin-prover --prove FILE` on each input |

The command `python3 -B scripts/check_kudos_models.py` regenerates the 24 inputs of series K from their specifications, and `python3 -B exporter/index_regression.py` rebuilds the stage index of series X1 from the stored stage files.
