#!/usr/bin/env python3
"""Prepare the resource runs of series V3.

    python3 -B make_resource_runs.py --e1 SETROOT --out OUTROOT [--max 8] [--min-seconds 1200]

The script reads the Tamarin records of series V1 and selects jobs by two
fixed rules, in the order of the records.

  lowheap    the first --max jobs with a verdict. The rerun gets a heap limit
             of 64 MB, far below the need of the prover, so the memory limit
             causes the missing verdict (label TM-res).
  shorttime  the first --max jobs that ended with a verdict after at least
             --min-seconds while the sampled memory stayed flat in the last
             30 % of the run (growth of at most 1 MB per minute). The rerun
             gets a quarter of that time, so the search and not the memory
             causes the missing verdict (label TM-search). The default of
             20 minutes leaves the rerun a window of more than a minute for
             the memory rule of the decision tree. Memory samples have a
             resolution of 1 MB, which a shorter window turns into a slope
             above the threshold.

The script copies the model files of the selected jobs to
OUTROOT/lowheap/<set>/ and OUTROOT/shorttime/<set>/, writes one job file per
rerun and prints the commands for run_set.py. It starts no prover. If no job
satisfies a rule, the series has no item for that label, and the report has
to say so.
"""
import argparse
import glob
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.normpath(os.path.join(HERE, "..", "common", "run_set.py"))


def records(setdir):
    path = os.path.join(setdir, "results", "tam_results.jsonl")
    last = {}
    if os.path.exists(path):
        for line in open(path):
            if line.strip():
                record = json.loads(line)
                last[(record["model"], record["lemma"])] = record
    return list(last.values())


def copy_models(setdir, target):
    os.makedirs(target, exist_ok=True)
    for pattern in ("*.spthy", "*_checks.txt", "cim.toml"):
        for path in glob.glob(os.path.join(setdir, pattern)):
            shutil.copy2(path, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--e1", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max", type=int, default=8)
    parser.add_argument("--min-seconds", type=float, default=1200)
    args = parser.parse_args()
    low, short = [], []
    for name in sorted(os.listdir(args.e1)):
        setdir = os.path.join(args.e1, name)
        for record in records(setdir):
            if record["verdict"] not in ("verified", "falsified"):
                continue
            if len(low) < args.max:
                low.append((name, setdir, record))
            late = record.get("rss_growth_late_mb_per_min")
            if len(short) < args.max and record["seconds"] >= args.min_seconds and late is not None and late <= 1.0:
                short.append((name, setdir, record))
    plan, commands = ["group\tset\tmodel\tlemma\toriginal_seconds\tlimit"], []
    for index, (name, setdir, record) in enumerate(low):
        target = os.path.join(args.out, "lowheap", name)
        copy_models(setdir, target)
        jobs = os.path.join(target, f"jobs_{index}.tsv")
        with open(jobs, "w", encoding="utf-8") as handle:
            handle.write(f"{record['model']}\t{record['lemma']}\n")
        plan.append(f"lowheap\t{name}\t{record['model']}\t{record['lemma']}\t{record['seconds']}\theap 64m")
        commands.append(f"python3 -B {RUNNER} {target} --skip-proverif --heap 64m --tm-timeout 300 --tm-jobs {jobs}")
    for index, (name, setdir, record) in enumerate(short):
        target = os.path.join(args.out, "shorttime", name)
        copy_models(setdir, target)
        jobs = os.path.join(target, f"jobs_{index}.tsv")
        limit = max(20, int(record["seconds"] / 4))
        with open(jobs, "w", encoding="utf-8") as handle:
            handle.write(f"{record['model']}\t{record['lemma']}\n")
        plan.append(f"shorttime\t{name}\t{record['model']}\t{record['lemma']}\t{record['seconds']}\ttime {limit} s")
        commands.append(f"python3 -B {RUNNER} {target} --skip-proverif --heap {record.get('heap_cap', '16g')} "
                        f"--tm-timeout {limit} --tm-jobs {jobs}")
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "resource_plan.tsv"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(plan) + "\n")
    with open(os.path.join(args.out, "resource_runs.sh"), "w", encoding="utf-8") as handle:
        handle.write("#!/bin/bash\n" + "\n".join(commands) + "\n")
    print(f"lowheap: {len(low)} job(s); shorttime: {len(short)} job(s)")
    print(f"plan: {os.path.join(args.out, 'resource_plan.tsv')}; commands: {os.path.join(args.out, 'resource_runs.sh')}")


if __name__ == "__main__":
    main()
