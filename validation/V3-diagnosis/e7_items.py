#!/usr/bin/env python3
"""Derive diagnosis items from the reruns with a longer time limit (series V7 and V3).

    python3 -B e7_items.py --original RECORDS.jsonl --reruns RECORDS.jsonl --labels-out labels_e7.tsv
    python3 -B e7_items.py --original RECORDS.jsonl --reruns RECORDS.jsonl --cimc CIMC_DIR \\
                           --predictions-out predictions_e7.tsv

An original job of the screening series stopped at its time limit. The
decision tree read its memory curve and called the cause TM-search (flat
memory) or TM-res (growing memory). The rerun E7x4_<job> repeats the job with
four times the limit and thereby shows the cause without the tree.

  TM-search  the rerun ends with a verdict, so more time was enough
  TM-res     the rerun exhausts the heap or the system kills it, so memory
             was the obstacle
  no label   the rerun stops at the longer time limit as well

The option --labels-out writes the labels from the reruns alone. The option
--predictions-out writes what the decision tree of the generator in CIMC_DIR
says about the original records. Publish the hash of the label file before
the second call. Append both files to the label and prediction files of the
other items (without the header line) before score_diagnosis.py runs.

By default, --original reads runs/screening/records.jsonl and --reruns reads
validation/V7-time-limit/records.jsonl of this repository.
"""
import argparse
import hashlib
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def latest(path):
    table = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                table[record["job"]] = record
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--original", default=os.path.join(ROOT, "runs", "screening", "records.jsonl"))
    parser.add_argument("--reruns", default=os.path.join(ROOT, "validation", "V7-time-limit", "records.jsonl"))
    parser.add_argument("--prefix", default="E7x4_")
    parser.add_argument("--cimc")
    parser.add_argument("--labels-out")
    parser.add_argument("--predictions-out")
    args = parser.parse_args()
    original, reruns = latest(args.original), latest(args.reruns)
    pairs = [(job[len(args.prefix):], record) for job, record in sorted(reruns.items()) if job.startswith(args.prefix)]
    pairs = [(job, record) for job, record in pairs if job in original]
    if args.labels_out:
        rows = []
        for job, record in pairs:
            if record["verdict"] in ("verified", "falsified"):
                rows.append((f"E7|{job}|tamarin", "TM-search", f"rerun: {record['verdict']} after {record['seconds']} s"))
            elif record["verdict"] in ("HEAP", "KILLED"):
                rows.append((f"E7|{job}|tamarin", "TM-res", f"rerun: {record['verdict']} after {record['seconds']} s"))
        text = "item\tcause\tsource\n" + "".join("\t".join(row) + "\n" for row in rows)
        with open(args.labels_out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"{len(rows)} labeled item(s) of {len(pairs)} rerun(s); sha256 {hashlib.sha256(text.encode()).hexdigest()}")
    if args.predictions_out:
        if not args.cimc:
            parser.error("--predictions-out needs --cimc")
        sys.path.insert(0, os.path.abspath(args.cimc))
        from cimc import diagnose
        rows = []
        for job, _ in pairs:
            record = original[job]
            fake = types.SimpleNamespace(model=job, tool="TM", enc="base", reason=record["verdict"], feat=record,
                                         outcome="N", lo="T", hi="T")
            finding = diagnose._no_outcome(fake, set(), None, ())
            rows.append((f"E7|{job}|tamarin", finding["cause"]))
        with open(args.predictions_out, "w", encoding="utf-8") as handle:
            handle.write("item\tcause\n" + "".join("\t".join(row) + "\n" for row in rows))
        print(f"{len(rows)} prediction(s); decision tree version {diagnose.TREE_VERSION}, sha256 {diagnose.tree_hash()}")


if __name__ == "__main__":
    main()
