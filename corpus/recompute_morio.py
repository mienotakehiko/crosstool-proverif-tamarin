#!/usr/bin/env python3
"""Extract the selected seven theories from the pinned Morio et al. data."""
from collections import Counter
import argparse
import csv
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def category(row):
    result = row["proverif_result"]
    if isinstance(result, bool):
        return "boolean"
    if row["proverif_timeout"]:
        return "timeout"
    if row["proverif_oom"]:
        return "out of memory"
    if row["translate_error"] or row["proverif_error"] or result == "error":
        return "error"
    return "no verdict"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate morio/subset41.tsv")
    args = parser.parse_args()
    with (HERE.parent / "registry/corpus.tsv").open(newline="") as f:
        source = {row["upstream_path"]: row["corpus_id"] for row in
                  csv.DictReader(f, delimiter="\t") if row["corpus_id"] != "K1"}
    with (HERE / "morio/eval-results.jsonl").open() as f:
        rows = [json.loads(line) for line in f if line.strip()]
    subset = sorted((r for r in rows if r["input_file"] in source),
                    key=lambda r: (source[r["input_file"]], r["index"]))
    if len(subset) != 41 or len({(r["input_file"], r["lemma"]) for r in subset}) != len(subset):
        sys.exit("Unexpected subset size or duplicate theory–lemma pairs.")
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    fields = ("index", "input_file", "lemma", "trace_quantifier", "tamarin_result",
              "proverif_result", "proverif_oom", "proverif_timeout", "translate_error", "proverif_error")
    writer.writerow(("corpus_id", *fields, "proverif_category"))
    for row in subset:
        writer.writerow((source[row["input_file"]], *(json.dumps(row[k]) if
                        isinstance(row[k], (bool, type(None))) else row[k] for k in fields), category(row)))
    expected = HERE / "morio/subset41.tsv"
    if args.write:
        expected.write_text(output.getvalue(), encoding="utf-8")
    elif expected.read_text(encoding="utf-8") != output.getvalue():
        sys.exit("The checked-in subset differs from the archived data.")
    print("ProVerif:", dict(Counter(category(row) for row in subset)))
    print("Tamarin Boolean verdicts:", sum(isinstance(row["tamarin_result"], bool) for row in subset))


if __name__ == "__main__":
    main()
