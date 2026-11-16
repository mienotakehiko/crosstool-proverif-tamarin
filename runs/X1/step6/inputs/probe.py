"""Test row-ID disequality on the two generated linear_pair models."""

from collections import Counter
import csv
import json
from pathlib import Path
import re

from common import dump, pv_reach, pv_results, run, sha


KIT = Path(__file__).resolve().parent
OUT = Path("/work")
FIELDS = (
    "variant", "lemma", "expected", "actual", "raw_result", "trace_ids",
    "read_ids", "rc", "timeout", "status",
)


def trace_ids(stdout, event, tag):
    goal = re.search(
        rf"^event {re.escape(event)}\(([^\n)]+)\) at \{{\d+\}} in copy (\S+) \(goal\)$",
        stdout, re.M,
    )
    if not goal or "A trace has been found." not in stdout:
        return []
    sid, copy = goal.groups()
    reads = re.findall(
        rf"^get tSt\(([^,\n]+),\s*{re.escape(sid)},\s*{re.escape(tag)},"
        rf"[^\n]+\) at \{{\d+\}} in copy {re.escape(copy)}$",
        stdout, re.M,
    )
    inserts = re.findall(
        rf"^insert tSt\(([^,\n]+),\s*{re.escape(sid)},\s*{re.escape(tag)},"
        r"[^\n]+\) at \{\d+\} in copy \S+$",
        stdout, re.M,
    )
    return reads if len(reads) == 2 and set(reads) <= set(inserts) else []


def measure(case):
    variant, lemma, event = (case[k] for k in ("variant", "lemma", "event"))
    file = KIT / "models" / variant / (lemma + ".pv")
    if sha(file) != case["sha256"]:
        raise RuntimeError(f"unexpected model hash: {file}")
    folder = OUT / variant / lemma
    meta = run(folder, "pv", ["/usr/local/bin/proverif", str(file)], 60)
    stdout = (folder / "pv.stdout.txt").read_text(errors="replace")
    results = pv_results(stdout, meta["rc"])
    result_line = re.search(rf"^RESULT not event\(\s*{re.escape(event)}\(", stdout, re.M)
    raw = results[0] if len(results) == 1 and result_line else ""
    actual = pv_reach(raw)
    read_ids = trace_ids(stdout, event, case["tag"])
    pattern = "distinct" if len(set(read_ids)) == 2 else "same" if read_ids else "none"
    expected_pattern = case["expected_trace_ids"]
    trace_ok = pattern == expected_pattern or (
        expected_pattern == "any_two" and pattern in ("same", "distinct")
    )

    if actual == "unknown" or (actual == "reachable" and not read_ids):
        status = "REVIEW"
    elif actual == case["expected"] and trace_ok:
        status = "MATCH"
    else:
        status = "DIFFERENT"
    return {
        "variant": variant, "lemma": lemma, "expected": case["expected"],
        "actual": actual, "raw_result": raw, "trace_ids": pattern,
        "read_ids": ",".join(read_ids), "rc": meta["rc"], "timeout": meta["timeout"],
        "status": status,
    }


def main():
    cases = json.loads((KIT / "cases.json").read_text())
    rows = []
    with (OUT / "summary.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for case in cases:
            row = measure(case)
            rows.append(row)
            writer.writerow(row)
            stream.flush()
            print(*(row[k] for k in FIELDS), sep="\t", flush=True)
    counts = Counter(r["status"] for r in rows)
    decision = "REVIEW" if counts["REVIEW"] else (
        "SUPPORTED" if counts["MATCH"] == len(cases) else "UNEXPECTED"
    )
    dump(OUT / "summary.json", rows)
    dump(OUT / "decision.json", {
        "diagnosis": decision, "expected_rows": len(cases), "rows": len(rows),
        "MATCH": counts["MATCH"], "DIFFERENT": counts["DIFFERENT"], "REVIEW": counts["REVIEW"],
    })


if __name__ == "__main__":
    main()
