#!/usr/bin/env python3
"""Verify the recovered research cohorts without starting either prover."""
from collections import Counter
from datetime import datetime, timedelta
import json
import re
import sys

from verify_evidence import ROOT, checked_file, file_digest, json_lines, read_json, read_tsv, require

M = "runs/M/historical"
OCT29 = f"{M}/oct29/mutation_extension_20261029"
FROZEN = "runs/M/frozen_20261111"
LEMMA1 = "scheduler/restricted_20261111"


def historical_m(source_sha):
    pilot = read_json(f"{M}/oct28/pilot/results.json")
    require(len(pilot) == 4 and sum(x["detected"] for x in pilot if x["case"] != "control") == 2,
            "October 28 pilot")
    require(not next(x["detected"] for x in pilot if x["case"] == "control"), "Pilot control")
    for row in pilot:
        for tool, ext in (("pv", "pv"), ("tm", "spthy")):
            folder = f"{M}/oct28/pilot/{row['case']}"
            require(file_digest(ROOT / f"{folder}/model.{ext}") == row[f"{tool}_sha256"], folder)
            require((ROOT / f"{folder}/{tool.upper()}.out").stat().st_size > 0, folder)

    raw = read_json(f"{OCT29}/results.json")
    completed = read_json(f"{OCT29}/results_completed_reference.json")
    planned = read_json(f"{OCT29}/manifest_before_runs.json")
    require(len(raw) == len(completed) == len(planned) == 23, "October 29 cohort length")
    require(len({r["directory"] for r in raw}) == 23, "October 29 case uniqueness")
    reference_input = f"{M}/oct29/shared_tamarin_reference/lms_s2/generated.spthy"
    ref_out = f"{M}/oct29/shared_tamarin_reference/lms_s2/tamarin.out"
    frozen_models = read_json(f"{M}/nov11_reference_model_hashes.json")["models"]
    expected = {(r["seed"], r["operator"]): r["source_sha256"] for r in frozen_models}
    seen, timeouts = set(), 0
    for result, review, original in zip(raw, completed, planned):
        case = result["directory"]
        require(review["directory"] == original["directory"] == case, f"Case alignment: {case}")
        key = result["seed"], result["operator"]
        for tool, ext in (("pv", "pv"), ("tm", "spthy")):
            sha = result[f"{tool}_sha256"]
            require(sha == review[f"{tool}_sha256"] == original[f"{tool}_sha256"], case)
            require(file_digest(ROOT / f"{OCT29}/{case}/model.{ext}") == sha, case)
            stdout = source_sha(f"{OCT29}/{case}/{tool.upper()}.out")
            require(stdout == result[f"{tool}_run"]["stdout_sha256"]
                    == review[f"{tool}_run"]["stdout_sha256"], case)
        if key in expected:
            require(result["pv_sha256"] == expected[key], case)
            seen.add(key)
        if result["seed"] == "lms_s2":
            require(result["tm_run"]["rc"] == 124, f"Original LMS timeout: {case}")
            timeouts += 1
            ref = review["reference_completion"]
            require(ref["model_sha256"] == result["tm_sha256"] == file_digest(ROOT / reference_input),
                    f"Shared reference input: {case}")
            require(ref["stdout_sha256"] == source_sha(ref_out), f"Shared reference log: {case}")
    require(timeouts == 11 and len(seen) == len(expected) == 22, "October 29 shared reference and November 11 input linkage")

    tracked = [r for r in completed if r["seed"] in {"lmots", "lms_s2"}]
    controls = [r for r in tracked if r["operator"] == "control"]
    mutants = [r for r in tracked if r["operator"] != "control"]
    disagreements = lambda row: any(result["discrepancy"] for result in row["results"])
    require(len(mutants) == 20 and sum(map(disagreements, mutants)) == 12
            and len(controls) == 2 and not any(map(disagreements, controls)), "October 29 outcome counts")
    print("M historical: pilot 2/3; main 12/20, controls 0/2, 11 original LMS timeouts retained")


def frozen_m(source_sha):
    freeze = read_json(f"{FROZEN}/freeze.json")
    start = read_json(f"{FROZEN}/execution_started.json")
    finish = read_json(f"{FROZEN}/execution_finished.json")
    date = datetime.fromisoformat
    require(date(freeze["timestamp"]) < date(start["timestamp"]) < date(finish["timestamp"]),
            "Frozen run time order")
    freeze_sha = file_digest(ROOT / f"{FROZEN}/freeze.json")
    require(freeze_sha == start["freeze_sha256"]
            == (ROOT / f"{FROZEN}/freeze.sha256").read_text().split()[0], "Frozen input manifest")
    require(len(freeze["files"]) == 68, "Frozen input count")
    for relative, sha in freeze["files"].items():
        checked_file(ROOT / FROZEN, relative, sha)
    digest = file_digest(ROOT / "diagnosis/v1.1/diagnose.py")
    require(freeze["tree_version"] == "1.1" and digest == freeze["tree_sha256"]
            == file_digest(ROOT / "cimc/v0.1.1/cimc/diagnose.py"), "Diagnosis source identity")

    rows = read_json(f"{FROZEN}/results.json")
    seen = set()
    for row in rows:
        saved = row["run"]
        relative = saved["raw_file"]
        require(relative not in seen, f"Duplicate run log: {relative}")
        seen.add(relative)
        require(source_sha(f"{FROZEN}/{relative}") == saved["raw_sha256"], f"Original log SHA: {relative}")
        metadata = (ROOT / FROZEN / relative).parent / "run.json"
        require(json.loads(metadata.read_text()) == saved, f"Run metadata: {relative}")
        begin = date(saved["started_utc"])
        end = begin + timedelta(seconds=saved["elapsed_s"])
        require(date(start["timestamp"]) <= begin <= end <= date(finish["timestamp"]), relative)

    counts = Counter(r["tool"] for r in rows)
    total_pv = sum(len(r["results"]) for r in rows if r["tool"] == "PV")
    require(counts == {"PV": 66, "TM": 14} and total_pv == 231, "November 11 invocation totals")
    assessments = read_json(f"{FROZEN}/mutation_assessment.json")
    require(len(assessments) == 20 and all(x["detected"] for x in assessments)
            and sum(bool(x["ordinary_different_queries"]) for x in assessments) == 18,
            "November 11 separate detection totals")
    print("M frozen: 20/20 with audit observations, 18/20 without; 80 invocation records")


def scheduler_and_u7():
    result = read_json(f"{LEMMA1}/results.json")
    log = (ROOT / LEMMA1 / "tests.log").read_text()
    require((result["tests_run"], result["failures"], result["errors"]) == (21, 0, 0)
            and len(re.findall(r"\.\.\. ok$", log, re.M)) == 21, "Lemma 1 saved test log")
    require(tuple(result[key] for key in ("atomic_states", "process_states", "abandoned_states",
                                         "atomic_traces", "process_traces")) == (3, 13, 3, 3, 3),
            "Lemma 1 fixture scope")
    p5 = json_lines("runs/P5/checkpoint/results/records.jsonl")
    trials = [r for r in p5 if r["job"].startswith("P5_")]
    ladder = [r for r in json_lines("runs/L/ladder/results/records.jsonl")
              if r["job"].startswith("L_")]
    require(Counter(r["verdict"] for r in trials) == {"verified": 965, "falsified": 160}, "P5")
    require(len(ladder) == 9 and len({r["job"] for r in ladder}) == 9
            and all(r["verdict"] == "HEAP" and r["rc"] == 251 for r in ladder), "U7 ladder")
    print("Lemma 1: 21 archived passes for the restricted fixture suite")
    print("U7: 1,125 P5 trials and 9 separate ladder HEAP exits (rc 251)")


def main():
    ledger = {r["path"]: r for r in read_tsv("registry/recovered-files.tsv")}

    def source_sha(relative):
        row = ledger[relative]
        checked_file(ROOT, relative, row["published_sha256"])
        return row["source_sha256"]

    for row in read_tsv("registry/reviewed_source_manifests.tsv"):
        if row["source_check"] == "verified":
            require(source_sha(row["path"]) == row["original_sha256"], row["path"])
        else:
            require(row["source_check"] == "source delivery archive missing"
                    and not (ROOT / row["path"]).exists(), row["path"])
    historical_m(source_sha)
    frozen_m(source_sha)
    scheduler_and_u7()
    for version in ("0.1.1", "0.1.2"):
        init = ROOT / f"cimc/v{version}/cimc/__init__.py"
        require(f'__version__ = "{version}"' in init.read_text(), f"CIMC {version}")
    print("CIMC 0.1.1 / 0.1.2 inputs and historical source manifests verified")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError) as error:
        sys.exit(str(error))
