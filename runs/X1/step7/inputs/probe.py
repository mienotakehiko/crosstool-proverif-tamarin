"""Check generated row-ID conditions and the corresponding proof results."""

from collections import Counter
import csv
import json
from pathlib import Path
import re

from common import dump, pv_reach, pv_results, run, sha, tm_verdict


KIT = Path(__file__).resolve().parent
OUT = Path("/work")
TAMARIN = ["/step7-tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS", "-d=0"]
FIELDS = (
    "model", "lemma", "expected", "native", "translated", "pv_raw",
    "read_ids", "guard_check", "status", "reason",
)


def model_body(model):
    return " ".join(model.split("\n(*\nGenerated from:", 1)[0].split())


def check_guards(body, case):
    """Check the order and the complete pairwise guard on each linear row."""
    rule = re.search(rf"^let {re.escape(case['rule'])} =\s*(.*?)(?=^let |^process\b)",
                     body, re.M | re.S)
    if not rule:
        return "missing_rule"
    reads = re.findall(r"\bget tSt\((.*?)\)(?:\s+suchthat\s+\((.*?)\))?\s+in\b",
                       rule[1], re.S)
    if len(reads) != case["reads"]:
        return "unexpected_reads"
    earlier = []
    for arguments, condition in reads:
        row_id = arguments.split(",", 1)[0].strip()
        if case["distinct"]:
            if not re.fullmatch(r"stL_St(?:_\d+)?", row_id) or row_id in earlier:
                return "unexpected_stamp"
            expected = " && ".join(f"{row_id} <> {other}" for other in earlier)
            earlier.append(row_id)
        else:
            expected = ""
        if " ".join(condition.split()) != expected:
            return "unexpected_row_condition"
    if case["model"] == "linear_pair":
        reference = KIT / "reference" / (case["lemma"] + ".pv")
        if model_body(body) != model_body(reference.read_text()):
            return "step6_model_mismatch"
    return "OK"


def positive_trace_ids(stdout, event):
    goal = re.search(
        rf"^event {re.escape(event)}\(([^\n)]+)\) at \{{\d+\}} in copy (\S+) \(goal\)$",
        stdout, re.M,
    )
    if not goal:
        return []
    sid, copy = map(re.escape, goal.groups())
    return re.findall(rf"^get tSt\(([^,\n]+),\s*{sid},[^\n]+\) at \{{\d+\}} in copy {copy}$",
                      stdout, re.M)


def measure(case):
    model, lemma, event = (case[key] for key in ("model", "lemma", "event"))
    folder = OUT / model / lemma
    path = KIT / "models" / (model + ".spthy")
    if sha(path) != case["sha256"]:
        raise RuntimeError(f"unexpected input hash: {path}")
    row = dict(case, native="unknown", translated="not_run", pv_raw="",
               guard_check="not_run", read_ids="", reason=[])
    native = run(folder, "native", TAMARIN + ["--prove=" + lemma, str(path)], 60)
    native_output = (folder / "native.stdout.txt").read_text(errors="replace")
    row["native"] = tm_verdict(native_output, lemma, native["rc"])
    if row["native"] != case["expected"]:
        row["reason"].append("unexpected_native")

    pv_path = folder / "translated.pv"
    export = run(folder, "export", TAMARIN + [
        "-m=proverif", "--lemma=" + lemma, "-o=" + str(pv_path), str(path),
    ], 60)
    if export["rc"] != 0 or not pv_path.is_file() or pv_path.stat().st_size == 0:
        row["reason"].append("export_incomplete")
        return dict(row, status="REVIEW")
    body = pv_path.read_text()
    row["translated_sha256"] = sha(pv_path)
    row["guard_check"] = check_guards(body, case)
    if row["guard_check"] != "OK":
        row["reason"].append(row["guard_check"])
    if len(re.findall(r"^\s*query\b", body, re.M)) != 1 or re.search(
        r"\b(?:warning|omitted)\b|(?:Restriction|Axiom) translation failed", body, re.I,
    ):
        row["reason"].append("query_or_translation_warning")

    proof = run(folder, "pv", ["/usr/local/bin/proverif", str(pv_path)], 60)
    stdout = (folder / "pv.stdout.txt").read_text(errors="replace")
    raw = pv_results(stdout, proof["rc"])
    if len(raw) == 1 and re.search(rf"^RESULT not event\(\s*{re.escape(event)}\(", stdout, re.M):
        row["pv_raw"] = raw[0]
        row["translated"] = pv_reach(raw[0])
    if row["translated"] == "not_run" or row["translated"] == "unknown":
        row["reason"].append("pv_incomplete_or_unresolved")
    if row["translated"] == "reachable":
        if "A trace has been found." not in stdout:
            row["reason"].append("missing_trace")
        elif case["distinct"]:
            ids = positive_trace_ids(stdout, event)
            row["read_ids"] = ",".join(ids)
            if len(ids) != case["reads"] or len(set(ids)) != case["reads"]:
                row["reason"].append("trace_ids_not_distinct")

    verdict = "MATCH" if row["native"] == row["translated"] else "DIFFERENT"
    return dict(row, status="REVIEW" if row["reason"] else verdict)


def main():
    cases = json.loads((KIT / "cases.json").read_text())
    rows = []
    with (OUT / "summary.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, extrasaction="ignore",
                                delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for case in cases:
            row = measure(case)
            rows.append(row)
            writer.writerow(dict(row, reason=",".join(row["reason"])))
            stream.flush()
            print(*(row[key] for key in FIELDS[:-1]), ",".join(row["reason"]), sep="\t", flush=True)
    counts = Counter(row["status"] for row in rows)
    passed = counts["MATCH"] == len(cases)
    dump(OUT / "summary.json", rows)
    dump(OUT / "decision.json", {
        "decision": "PASS" if passed else "REVIEW",
        "rows": len(rows), "expected_rows": len(cases),
        "MATCH": counts["MATCH"], "DIFFERENT": counts["DIFFERENT"], "REVIEW": counts["REVIEW"],
    })
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
