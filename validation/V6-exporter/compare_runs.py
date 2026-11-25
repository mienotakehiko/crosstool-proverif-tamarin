#!/usr/bin/env python3
"""Compare two result tables of the translated route (series V6).

    python3 -B compare_runs.py BEFORE AFTER [--key model,lemma] [--verdict verdict] [--reference COLUMN]

BEFORE and AFTER are tables of the same jobs under two builds of the exporter,
for example the unmodified build B0 and the repaired build B2. The files may
be TSV, CSV or JSON lines. The option --key names the columns that identify a
job, and --verdict names the column that holds the outcome. The script prints
how many jobs keep their outcome, the transitions between outcomes and the
jobs that change. With --reference, it also counts for each table the jobs
whose outcome equals the reference column, for example the native Tamarin
verdict.

The script compares recorded outcomes and runs no tool.
"""
import argparse
import collections
import csv
import json


def read(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if text.lstrip().startswith("{"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    dialect = "excel-tab" if "\t" in text.splitlines()[0] else "excel"
    return list(csv.DictReader(text.splitlines(), dialect=dialect))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--key", default="model,lemma")
    parser.add_argument("--verdict", default="verdict")
    parser.add_argument("--reference")
    args = parser.parse_args()
    keys = args.key.split(",")
    tables = []
    for path in (args.before, args.after):
        tables.append({tuple(str(row[k]) for k in keys): row for row in read(path)})
    before, after = tables
    common = sorted(set(before) & set(after))
    print(f"jobs: {len(before)} before, {len(after)} after, {len(common)} in both")
    moves = collections.Counter((str(before[k][args.verdict]), str(after[k][args.verdict])) for k in common)
    same = sum(count for (a, b), count in moves.items() if a == b)
    print(f"unchanged outcome: {same} of {len(common)}")
    for (a, b), count in sorted(moves.items()):
        if a != b:
            print(f"  {a} -> {b}: {count}")
    for key in common:
        a, b = str(before[key][args.verdict]), str(after[key][args.verdict])
        if a != b:
            print("  changed:", " ".join(key), f"({a} -> {b})")
    if args.reference:
        for label, table in (("before", before), ("after", after)):
            rows = [table[k] for k in common if args.reference in table[k]]
            agree = sum(1 for row in rows if str(row[args.verdict]) == str(row[args.reference]))
            print(f"agreement with {args.reference} {label}: {agree} of {len(rows)}")


if __name__ == "__main__":
    main()
