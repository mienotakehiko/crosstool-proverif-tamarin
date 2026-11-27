"""Replay the 60 Step 4 and Step 5 cases with the Step 7 translator."""

from collections import Counter
import csv
import difflib
import importlib.util
import json
from pathlib import Path
import re

from common import dump, pv_reach, pv_results, run, sha, tm_verdict


KIT = Path(__file__).resolve().parent
OUT = Path("/work")
TAMARIN = ["/step8-tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS", "-d=0"]
FIELDS = (
    "origin", "suite", "case", "lemma", "native", "previous", "translated",
    "previous_raw", "pv_raw", "pv_check", "changed_from_previous", "trace_ids",
    "native_rc", "export_rc", "pv_rc", "status", "reason",
)


def read_evaluator():
    spec = importlib.util.spec_from_file_location("ccs26_eval", "/opt/eval/eval.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    return evaluator


def stable_pv(model):
    return model.split("\n(*\nGenerated from:", 1)[0].rstrip() + "\n"


def goal_trace_ids(stdout):
    goal = re.search(r"^event eGood\(([^\n)]+)\) at \{\d+\} in copy (\S+) \(goal\)$",
                     stdout, re.M)
    if not goal or "A trace has been found." not in stdout:
        return []
    sid, copy = map(re.escape, goal.groups())
    return re.findall(rf"^get tSt\(([^,\n]+),\s*{sid},[^\n]+\) at \{{\d+\}} in copy {copy}$",
                      stdout, re.M)


def write_diff(path, before, after, label):
    diff = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                fromfile=label, tofile="regenerated")
    path.write_text("".join(diff))


def measure(case, evaluator):
    suite, name, lemma = (case[field] for field in ("suite", "case", "lemma"))
    folder = OUT / case["origin"] / suite / name / lemma
    model = KIT / "models" / suite / (name + ".spthy")
    if sha(model) != case["model_sha256"]:
        raise RuntimeError(f"unexpected input SHA-256: {model}")
    row = dict(case, native="unknown", translated="not_run", pv_raw="", trace_ids="",
               native_rc=None, export_rc=None, pv_rc=None, pv_check="not_run",
               changed_from_previous=None, reason=[])
    native = run(folder, "native", TAMARIN + ["--prove=" + lemma, str(model)], 60)
    row["native_rc"] = native["rc"]
    native_stdout = (folder / "native.stdout.txt").read_text(errors="replace")
    row["native"] = tm_verdict(native_stdout, lemma, native["rc"])
    if row["native"] == "unknown":
        row["reason"].append("native_incomplete_or_unresolved")

    pv_path = folder / "translated.pv"
    export = run(folder, "export", TAMARIN + [
        "-m=proverif", "--lemma=" + lemma, "-o=" + str(pv_path), str(model),
    ], 60)
    row["export_rc"] = export["rc"]
    if export["rc"] != 0 or not pv_path.is_file() or pv_path.stat().st_size == 0:
        row["reason"].append("export_incomplete")
        return dict(row, status="REVIEW")

    body = pv_path.read_text()
    row["translated_sha256"] = sha(pv_path)
    actual = stable_pv(body)
    previous = stable_pv((KIT / case["old_pv"]).read_text())
    expected = stable_pv((KIT / case["expected_pv"]).read_text())
    row["changed_from_previous"] = actual.split() != previous.split()
    same_as_reference = actual.split() == expected.split()
    row["pv_check"] = "OK" if same_as_reference else "REVIEW"
    if row["changed_from_previous"]:
        write_diff(folder / "previous-to-regenerated.diff", previous, actual, "step4-or-step5")
    if not same_as_reference:
        row["reason"].append("generated_model_differs_from_reference")
        write_diff(folder / "expected-to-regenerated.diff", expected, actual, "expected")

    flags = evaluator.extract_translation_flags(body)
    row["translation_flags"] = flags
    if len(re.findall(r"^\s*query\b", body, re.M)) != 1 or any(flags.values()) or re.search(
        r"\b(?:warning|omitted)\b|(?:Restriction|Axiom) (?:translation failed|has negated event)",
        body, re.I,
    ):
        row["reason"].append("query_or_translation_warning")

    proof = run(folder, "pv", ["/usr/local/bin/proverif", str(pv_path)], 60)
    row["pv_rc"] = proof["rc"]
    stdout = (folder / "pv.stdout.txt").read_text(errors="replace")
    results = pv_results(stdout, proof["rc"])
    if len(results) == 1 and results[0] in ("true", "false"):
        row["pv_raw"] = results[0]
        if suite in ("initial", "zero_argument"):
            value, note = evaluator.reconstruct_proverif_result(body, stdout)
            row["evaluator_note"] = note
            if isinstance(value, bool) and note is None:
                positive, negative = ("holds", "violated") if lemma == "single_consumption" else (
                    "reachable", "unreachable",
                )
                row["translated"] = positive if value else negative
        else:
            row["translated"] = pv_reach(results[0])
    if row["translated"] in ("unknown", "not_run"):
        row["reason"].append("pv_incomplete_or_unresolved")
    if name == "linear_pair" and lemma == "good_reachable" and row["translated"] == "reachable":
        ids = goal_trace_ids(stdout)
        row["trace_ids"] = ",".join(ids)
        if len(ids) != 2 or len(set(ids)) != 2:
            row["reason"].append("trace_ids_not_distinct")
    if row["reason"]:
        return dict(row, status="REVIEW")
    if (row["native"], row["translated"], row["pv_raw"]) != (
        case["native_expected"], case["expected"], case["expected_raw"],
    ):
        row["reason"].append("verdict_differs_from_reference")
        return dict(row, status="DIFFERENT")
    return dict(row, status="MATCH")


def main():
    cases = json.loads((KIT / "cases.json").read_text())
    evaluator = read_evaluator()
    rows = []
    with (OUT / "summary.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, extrasaction="ignore",
                                delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for case in cases:
            row = measure(case, evaluator)
            rows.append(row)
            writer.writerow(dict(row, reason=",".join(row["reason"])))
            stream.flush()
            print(row["origin"], row["case"], row["lemma"], row["native"], row["translated"],
                  row["pv_check"], row["status"], *row["reason"], sep="\t", flush=True)

    counts = Counter(row["status"] for row in rows)
    matching = [row for row in rows if row["status"] == "MATCH"]
    preserved = sum(row["previous"] == row["translated"] for row in matching)
    repaired = sum(row["previous"] != row["translated"] for row in matching)
    changed_pv = sum(row["changed_from_previous"] is True for row in rows)
    passed = len(rows) == 60 and counts["MATCH"] == 60 and (
        preserved, repaired, changed_pv,
    ) == (59, 1, 2)
    dump(OUT / "summary.json", rows)
    dump(OUT / "decision.json", {
        "decision": "PASS" if passed else "REVIEW",
        "rows": len(rows), "step4_rows": sum(row["origin"] == "step4" for row in rows),
        "step5_rows": sum(row["origin"] == "step5" for row in rows),
        "MATCH": counts["MATCH"], "DIFFERENT": counts["DIFFERENT"], "REVIEW": counts["REVIEW"],
        "preserved": preserved, "repaired": repaired, "changed_pv": changed_pv,
    })
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
