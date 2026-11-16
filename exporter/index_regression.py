#!/usr/bin/env python3
"""Build the X1 stage index from saved summaries, exit codes and metadata."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
X1 = ROOT / "runs/X1"


def read_tsv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main():
    summaries = {}
    for step in ("step4", "step5"):
        for runner in ("baseline", "candidate"):
            summaries[step, runner] = {
                (r["suite"], r["case"], r["lemma"]): r
                for r in read_tsv(X1 / step / runner / "summary.tsv")
            }
    final = {(r["suite"], r["case"], r["lemma"]): r for r in read_tsv(X1 / "step8/summary.tsv")}
    rows = []
    for comparison in read_tsv(X1 / "comparison.tsv"):
        origin = comparison["origin"]
        key = tuple(comparison[k] for k in ("suite", "case", "lemma"))
        b1_path = comparison["previous_archive_path"]
        sources = (
            ("B0", X1 / origin / b1_path.replace("candidate/", "baseline/", 1),
             summaries[origin, "baseline"][key], "baseline"),
            ("B1", X1 / origin / b1_path, summaries[origin, "candidate"][key], "leafless"),
            ("B2", X1 / "step8" / comparison["final_archive_path"], final[key], "row_guards"),
        )
        for build, path, summary, column in sources:
            if any(summary[k] != comparison[j] for k, j in (
                ("native", "native"), ("translated", column), ("pv_raw", f"{column}_pv_raw")
            )):
                raise ValueError(f"Comparison differs from {build} summary for {key}")
            for stage in ("native", "export", "pv"):
                metadata = path / f"{stage}.meta.json"
                status = json.loads(metadata.read_text())
                exit_code = int((path / f"{stage}.exit_code.txt").read_text())
                if exit_code != int(summary[f"{stage}_rc"]) or exit_code != status["rc"]:
                    raise ValueError(f"Exit code differs for {metadata}")
                if exit_code or status["timeout"]:
                    raise ValueError(f"Unexpected stage termination for {metadata}")
                rows.append((build, *key, stage, exit_code, status["timeout"],
                             metadata.relative_to(ROOT).as_posix()))
    if len(rows) != 540 or len({r[:5] for r in rows}) != len(rows):
        raise ValueError("Expected 540 unique stage invocations")
    with (X1 / "jobs.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("build", "suite", "case", "lemma", "stage", "exit_code",
                         "timeout", "metadata_path"))
        writer.writerows(rows)
    print(f"Indexed {len(rows)} invocations.")


if __name__ == "__main__":
    main()
