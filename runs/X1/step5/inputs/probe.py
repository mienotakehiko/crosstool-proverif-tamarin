"""Run small state-translation controls with the Step 3 binaries."""

from collections import Counter
import csv
import difflib
import importlib.util
import json
from pathlib import Path
import re
import sys

from common import dump, pv_reach, pv_results, run, sha, tm_verdict


KIT = Path(__file__).resolve().parent
LIMIT = 60
MARKERS = (
    "Restriction translation failed", "Restriction has negated event",
    "Axiom translation failed", "Axiom has negated event",
)
FIELDS = (
    "suite", "case", "lemma", "expected_native", "native", "translated",
    "pv_raw", "native_rc", "export_rc", "pv_rc", "status", "reason",
)


def read_evaluator():
    spec = importlib.util.spec_from_file_location("ccs26_eval", "/opt/eval/eval.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    return evaluator


def model_prefix(model):
    prefix, sep, _ = model.partition("(* Processes *)")
    return " ".join(prefix.split()) if sep else None


def without_build_footer(model):
    return model.split("\n(*\nGenerated from:", 1)[0].rstrip() + "\n"


def run_case(case, work, variant, evaluator):
    suite, case_id, lemma = (case[key] for key in ("suite", "case", "lemma"))
    key = Path(suite) / case_id / lemma
    folder = work / variant / key
    folder.mkdir(parents=True)
    model = KIT / "models" / suite / (case_id + ".spthy")
    if sha(model) != case["model_sha256"]:
        raise RuntimeError(f"model checksum mismatch: {model}")

    row = dict(case, native="unknown", translated="not_run", pv_raw=[],
               native_rc=None, export_rc=None, pv_rc=None, reason=[])
    tamarin = ["/step5-tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS", "-d=0"]
    pv_path = folder / "translated.pv"
    native = run(folder, "native", tamarin + ["--prove=" + lemma, str(model)], LIMIT)
    row["native_rc"] = native["rc"]
    row["native"] = tm_verdict((folder / "native.stdout.txt").read_text(errors="replace"),
                               lemma, native["rc"])
    if row["native"] != case["expected_native"]:
        row["reason"].append("native_incomplete_or_expectation_mismatch")

    export = run(folder, "export", tamarin + [
        "-m=proverif", "--lemma=" + lemma, "-o=" + str(pv_path), str(model),
    ], LIMIT)
    row["export_rc"] = export["rc"]
    if export["rc"] != 0 or not pv_path.is_file() or pv_path.stat().st_size == 0:
        row["reason"].append("export_incomplete")
        return dict(row, status="REVIEW")

    body = pv_path.read_text()
    row["translated_sha256"] = sha(pv_path)
    flags = evaluator.extract_translation_flags(body)
    markers = [m for m in MARKERS if m in body]
    if re.search(r"\b(?:warning|omitted)\b", body, re.I):
        markers.append("warning_or_omitted")
    row.update(translation_flags=flags, translation_markers=markers)
    row["query_count"] = len(re.findall(r"^\s*query\b", body, re.M))
    prefix = model_prefix(body)
    expected_event = re.escape(f"e{case['event']}")
    query = re.search(r"\bquery\b.*?\bevent\(\s*" + expected_event + r"\(", prefix or "")
    if row["query_count"] != 1 or not query or any(flags.values()) or markers:
        row["reason"].append("query_or_translation_warning")
    if variant == "candidate":
        baseline = work / "baseline" / key / "translated.pv"
        if baseline.is_file():
            before = baseline.read_text()
            if prefix is None or prefix != model_prefix(before):
                row["reason"].append("baseline_declarations_or_query_changed")
            diff = difflib.unified_diff(
                without_build_footer(before).splitlines(keepends=True),
                without_build_footer(body).splitlines(keepends=True),
                fromfile="baseline", tofile="candidate",
            )
            (folder / "baseline-to-candidate.diff").write_text("".join(diff))
        else:
            row["reason"].append("baseline_export_missing")

    proof = run(folder, "pv", ["/usr/local/bin/proverif", str(pv_path)], LIMIT)
    row["pv_rc"] = proof["rc"]
    stdout = (folder / "pv.stdout.txt").read_text(errors="replace")
    row["pv_raw"] = pv_results(stdout, proof["rc"])
    absence_result = re.search(r"^RESULT not event\(\s*" + expected_event + r"\(", stdout, re.M)
    if len(row["pv_raw"]) == 1 and absence_result:
        row["translated"] = pv_reach(row["pv_raw"][0])
    if row["translated"] in ("unknown", "not_run"):
        row["reason"].append("pv_incomplete_or_unresolved")
    comparison = "MATCH" if row["native"] == row["translated"] else "DIFFERENT"
    return dict(row, status="REVIEW" if row["reason"] else comparison)


def evaluate(variant, work, evaluator):
    cases = json.loads((KIT / "cases.json").read_text())
    output = work / variant
    output.mkdir()
    rows = []
    complete = False
    try:
        with (output / "summary.tsv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore",
                                    delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for case in cases:
                row = run_case(case, work, variant, evaluator)
                rows.append(row)
                writer.writerow(dict(row, pv_raw=",".join(row["pv_raw"]),
                                     reason=",".join(row["reason"])))
                stream.flush()
                print(variant, row["case"], row["lemma"], row["native"],
                      row["translated"], row["status"], *row["reason"], sep="\t", flush=True)
        complete = True
    finally:
        counts = Counter(r["status"] for r in rows)
        dump(output / "summary.json", rows)
        dump(output / "inside_status.json", {
            "attempted_rows": len(rows), "expected_rows": len(cases), "complete": complete,
            "MATCH": counts["MATCH"], "DIFFERENT": counts["DIFFERENT"], "REVIEW": counts["REVIEW"],
        })


if __name__ == "__main__":
    evaluate(sys.argv[1], Path("/work"), read_evaluator())
