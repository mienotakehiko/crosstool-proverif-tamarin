#!/usr/bin/env python3
"""Select the jobs of series V7 and print their commands.

    python3 -B select_jobs.py [--records FILE] [--factor 4] [--count 10] [--per-model 2]

The plan fixed the following rule before any rerun. Among the screening jobs
of the series P1 to P4 whose last attempt ended at the time limit, take the
jobs with the smallest peak resident memory, at most --per-model jobs per
model file, until the selection holds --count jobs. A small peak means that
the search and not the memory stopped the job, so these jobs are the most
likely to profit from a longer time limit. Jobs that the system killed, jobs
that exhausted the heap (series L repeats them at 96 GiB) and jobs with tool
errors are no candidates.

The script writes jobs_e7.tsv next to itself and prints one command per job
for the runner models/tamarin-kit-v3/run_one_v3.sh. Each rerun keeps the
build, the model file, the lemma, the heuristic, the search mode and the heap
limit of the original job and multiplies the time limit by --factor. By
default, --records reads runs/screening/records.jsonl of this repository.
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT = os.path.join(ROOT, "runs", "screening", "records.jsonl")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--records", default=DEFAULT)
    parser.add_argument("--factor", type=int, default=4)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--per-model", type=int, default=2)
    args = parser.parse_args()
    latest = {}
    with open(args.records, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                latest[record["job"]] = record
    candidates = [r for job, r in latest.items()
                  if job.split("_")[0] in ("P1", "P2", "P3", "P4") and r["verdict"] == "TIMEOUT"]
    candidates.sort(key=lambda r: (r["rss_max_mb"], r["job"]))
    chosen, per_model = [], {}
    for record in candidates:
        if per_model.get(record["model"], 0) >= args.per_model:
            continue
        per_model[record["model"]] = per_model.get(record["model"], 0) + 1
        chosen.append(record)
        if len(chosen) == args.count:
            break
    header = ["new_job", "original_job", "tool", "model", "lemma", "heuristic", "search", "heap",
              "original_timeout_s", "new_timeout_s", "original_peak_rss_mb", "original_late_growth_mb_per_min"]
    rows = []
    for record in chosen:
        rows.append([f"E7x{args.factor}_{record['job']}", record["job"], record["tool"], record["model"],
                     record["lemma"], record["heuristic"], record["search"], record["heap_cap"],
                     record["timeout_s"], record["timeout_s"] * args.factor, record["rss_max_mb"],
                     record["rss_growth_late_mb_per_min"]])
    with open(os.path.join(HERE, "jobs_e7.tsv"), "w", encoding="utf-8") as handle:
        handle.write("\t".join(header) + "\n")
        handle.writelines("\t".join(str(x) for x in row) + "\n" for row in rows)
    print(f"# {len(candidates)} candidates, {len(rows)} selected, run from models/tamarin-kit-v3")
    for row in rows:
        print(f"./run_one_v3.sh {row[0]} {row[2]} variants/{row[3]} {row[4]} {row[5]} {row[6]} {row[7]} {row[9]}")


if __name__ == "__main__":
    main()
