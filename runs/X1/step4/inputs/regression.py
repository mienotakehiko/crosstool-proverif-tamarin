"""Compare the two rebuilt exporters on pinned state-translation models."""

import csv
import difflib
from hashlib import sha256
import importlib.util
import json
import re
import sys
from pathlib import Path

from common import dump, pv_reach, pv_results, run, sha, tm_verdict


KIT = Path(__file__).resolve().parent
LIMIT_SECONDS = 60
MODEL_CHECKS = (
    "Restriction translation failed",
    "Restriction has negated event",
    "Axiom translation failed",
    "Axiom has negated event",
)
SUITES = ("initial", "zero_argument", "source", "variable_controls")
FIELDS = (
    "suite", "case", "lemma", "expected_native", "saved_export",
    "native", "translated", "pv_raw", "native_rc", "export_rc", "pv_rc",
    "status", "review",
)


def read_evaluator():
    spec = importlib.util.spec_from_file_location("ccs26_eval", "/opt/eval/eval.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    return evaluator


def model_prefix(model):
    prefix, separator, _ = model.partition("(* Processes *)")
    if not separator:
        raise ValueError("missing Processes section in generated PV")
    return " ".join(prefix.split())


def stable_pv(model):
    return model.split("\n(*\nGenerated from:", 1)[0].rstrip() + "\n"


def run_case(case, work, variant, evaluator):
    suite, case_id, lemma = (case[key] for key in ("suite", "case", "lemma"))
    key = Path(suite) / case_id / lemma
    folder = work / variant / key
    folder.mkdir(parents=True)
    src = KIT / "models" / suite / (case_id + ".spthy")
    if sha(src) != case["model_sha256"]:
        raise RuntimeError(f"model checksum mismatch: {src}")
    tamarin = ["/step4-tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS", "-d=0"]
    translated = folder / "translated.pv"
    row = dict(case, native="unknown", translated="not_run", pv_raw=[],
               native_rc=None, export_rc=None, pv_rc=None, review=[])
    nm = run(folder, "native", tamarin + ["--prove=" + lemma, str(src)], LIMIT_SECONDS)
    row["native_rc"] = nm["rc"]
    row["native"] = tm_verdict((folder / "native.stdout.txt").read_text(errors="replace"),
                               lemma, nm["rc"])
    if nm["rc"] != 0 or row["native"] == "unknown":
        row.update(status="REVIEW", review=["native_incomplete"])
        return row, True

    em = run(folder, "export", tamarin + [
        "-m=proverif", "--lemma=" + lemma, "-o=" + str(translated), str(src),
    ], LIMIT_SECONDS)
    row["export_rc"] = em["rc"]
    if em["rc"] != 0 or not translated.is_file() or not translated.stat().st_size:
        row.update(status="REVIEW", review=["export_incomplete"])
        return row, True

    model = translated.read_text()
    row["translated_sha256"] = sha(translated)
    row["translation_flags"] = evaluator.extract_translation_flags(model)
    row["translation_markers"] = [marker for marker in MODEL_CHECKS if marker in model]
    if re.search(r"\b(?:warning|omitted)\b", model, flags=re.I):
        row["translation_markers"].append("warning_or_omitted")
    queries = re.findall(r"^\s*query\b", model, re.M)
    row["query_count"] = len(queries)
    if len(queries) != 1 or any(row["translation_flags"].values()) or row["translation_markers"]:
        row["review"].append("query_shape_or_translation_warning")

    try:
        prefix = model_prefix(model)
        row["prefix_sha256"] = sha256(prefix.encode()).hexdigest()
        if "saved_prefix_sha256" in case and row["prefix_sha256"] != case["saved_prefix_sha256"]:
            row["review"].append("saved_declarations_or_query_changed")
        if variant == "candidate":
            baseline_model = (work / "baseline" / key / "translated.pv").read_text()
            if prefix != model_prefix(baseline_model):
                row["review"].append("baseline_declarations_or_query_changed")
            old, new = stable_pv(baseline_model), stable_pv(model)
            row["stable_pv_changed"] = old != new
            diff = difflib.unified_diff(old.splitlines(keepends=True),
                                        new.splitlines(keepends=True),
                                        fromfile="baseline", tofile="candidate")
            (folder / "baseline-to-candidate.diff").write_text("".join(diff))
    except ValueError as exc:
        row["review"].append(str(exc))

    pm = run(folder, "pv", ["/usr/local/bin/proverif", str(translated)], LIMIT_SECONDS)
    row["pv_rc"] = pm["rc"]
    stdout = (folder / "pv.stdout.txt").read_text(errors="replace")
    raw = pv_results(stdout, pm["rc"])
    row["pv_raw"] = raw
    if len(raw) == 1 and raw[0] in ("true", "false"):
        if suite in ("initial", "zero_argument"):
            value, note = evaluator.reconstruct_proverif_result(model, stdout)
            row["evaluator_note"] = note
            if isinstance(value, bool) and note is None:
                labels = ("holds", "violated") if lemma == "single_consumption" else (
                    "reachable", "unreachable",
                )
                row["translated"] = labels[0] if value else labels[1]
        else:
            row["translated"] = pv_reach(raw[0])

    if row["translated"] in ("unknown", "not_run"):
        row["status"] = "REVIEW"
        row["review"].append("pv_incomplete_or_unresolved")
        return row, pm["rc"] != 0
    if row["native"] != case["expected_native"]:
        row["review"].append("native_expectation_changed")
    if variant == "baseline" and "saved_export" in case:
        if row["translated"] != case["saved_export"] or raw != case["saved_pv_raw"]:
            row["review"].append("historical_verdict_not_reproduced")
    if variant == "candidate":
        if row["translated"] != case["expected_native"]:
            row["review"].append("candidate_does_not_match_native")
        if ("saved_export" in case and row["translated"] != case["saved_export"]
                and row.get("stable_pv_changed") is False):
            row["review"].append("verdict_changed_without_pv_change")

    verdict = "MATCH" if row["native"] == row["translated"] else "DIFFERENT"
    row["status"] = "REVIEW" if row["review"] else verdict
    return row, False


def write_counts(output, rows):
    with (output / "counts.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["suite", "rows", "MATCH", "DIFFERENT", "REVIEW"])
        for suite in SUITES:
            statuses = [r["status"] for r in rows if r["suite"] == suite]
            writer.writerow([suite, len(statuses), *(statuses.count(s) for s in (
                "MATCH", "DIFFERENT", "REVIEW",
            ))])


def evaluate(variant, work, evaluator):
    cases = json.loads((KIT / "cases.json").read_text())
    output = work / variant
    output.mkdir()
    rows = []
    outcome = {"variant": variant, "expected_rows": len(cases), "complete": False}
    try:
        with (output / "summary.tsv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore",
                                    delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for case in cases:
                row, fatal = run_case(case, work, variant, evaluator)
                rows.append(row)
                writer.writerow(dict(row, pv_raw=",".join(row["pv_raw"]),
                                     review=",".join(row["review"])))
                stream.flush()
                print(variant, row["suite"], row["case"], row["lemma"], row["native"],
                      row["translated"], row["status"], *row["review"], sep="\t", flush=True)
                if fatal:
                    raise RuntimeError("tool execution stopped; see the last row and phase logs")
        outcome["complete"] = True
        outcome["accepted"] = all(r["status"] != "REVIEW" for r in rows)
    except Exception as exc:
        outcome["error"] = repr(exc)
        raise
    finally:
        outcome["rows"] = len(rows)
        dump(output / "summary.json", rows)
        dump(output / "inside_status.json", outcome)
        write_counts(output, rows)
    return 0 if outcome["accepted"] else 3


if __name__ == "__main__":
    sys.exit(evaluate(sys.argv[1], Path("/work"), read_evaluator()))
