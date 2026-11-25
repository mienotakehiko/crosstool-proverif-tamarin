#!/usr/bin/env python3
"""Recompute the counts of the series G to K, M and L from the archived records.

    python3 -B scripts/recompute_paper_numbers.py

Each output line states one count of the paper, the value that the records
yield and the value that the paper reports. The script reads local files only
and starts no prover. It ends with status 1 if a value differs.
"""
from collections import Counter, defaultdict
import re
from statistics import median
import sys

from verify_evidence import ROOT, file_digest, json_lines, read_json, read_tsv


def latest_screening_records():
    """Return the last recorded attempt of every screening job."""
    latest = {}
    for row in json_lines("runs/screening/records.jsonl"):
        job = row["job"]
        if re.match(r"P[1-4]_", job) and (job not in latest or row["time"] >= latest[job]["time"]):
            latest[job] = row
    return latest


def screening(compare):
    phases = {
        "P1": (81, 42, 11, 26, 2, 0, 0),
        "P2": (102, 46, 7, 35, 5, 7, 2),
        "P3": (24, 11, 9, 3, 1, 0, 0),
        "P4": (88, 85, 1, 2, 0, 0, 0),
    }
    labels = ("jobs", "verified", "falsified", "TIMEOUT", "KILLED", "HEAP", "ERROR")
    latest = latest_screening_records()
    total = Counter()
    for phase, expected in phases.items():
        group = {job: row for job, row in latest.items() if job.startswith(phase + "_")}
        stored = {row["job"]: row for row in json_lines(f"runs/{phase}/records.jsonl")}
        if group != stored:
            raise ValueError(f"The records of {phase} differ from the cumulative screening record")
        counts = Counter(row["verdict"] for row in group.values())
        counts["jobs"] = len(group)
        total.update(counts)
        for label, target in zip(labels, expected):
            compare(f"{phase} {label}", counts[label], target)
    for label, target in zip(labels, (295, 184, 28, 66, 8, 7, 2)):
        compare(f"Screening {label}", total[label], target)
    conclusive = total["verified"] + total["falsified"]
    compare("Screening conclusive", conclusive, 212)
    compare("Screening without verdict", total["jobs"] - conclusive, 83)


def repetition(compare):
    records = json_lines("runs/P5/records.jsonl")
    original = {row["job"]: row for row in records if not row["job"].startswith("P5_")}
    trials = defaultdict(list)
    for row in records:
        if row["job"].startswith("P5_"):
            trials[re.sub(r"_r[1-5]$", "", row["job"][3:])].append(row)
    outcomes = Counter(row["verdict"] for group in trials.values() for row in group)
    compare("P5 jobs", len(trials), 225)
    compare("P5 trials", outcomes.total(), 1125)
    compare("P5 verified", outcomes["verified"], 965)
    compare("P5 falsified", outcomes["falsified"], 160)
    same = sum(len(group) for job, group in trials.items()
               if len(group) == 5 and len({row["job"] for row in group}) == 5
               and all(row["rc"] == 0 and (row["sha256"], row["verdict"]) ==
                       (original[job]["sha256"], original[job]["verdict"]) for row in group))
    compare("P5 trials equal to the first run", same, 1125)
    top = {job.split("_TopAuth_")[-1]: group for job, group in trials.items()
           if re.match(r"P[13]_std_HSS_LS7_inj_", job) and "_TopAuth_" in job}
    for heuristic, target in (("d_prove", 11.4), ("t_prove", 1861.5), ("C_prove", 493.7),
                              ("s_prove", 11.5), ("S_prove", 11.2), ("I_prove", 11.3)):
        compare(f"P5 TopAuth {heuristic} median seconds",
                median(row["seconds"] for row in top[heuristic]), target)


def memory_ladder(compare):
    ladder = [r for r in json_lines("runs/L/ladder/records.jsonl") if r["job"].startswith("L_")]
    compare("L ladder trials", len({r["job"] for r in ladder}), 9)
    compare("L ladder HEAP with exit status 251",
            sum(r["verdict"] == "HEAP" and r["rc"] == 251 for r in ladder), 9)
    compare("L 96 GiB HEAP", sum(r["verdict"] == "HEAP" for r in json_lines("runs/L/heap96/records.jsonl")), 7)
    reference = {r["job"]: r for r in json_lines("runs/P2/records.jsonl")}
    curves = (
        ("std", "LMOTS_E1u", "exec_accept", (372.6, 788.3, 1621.2, 3315.4)),
        ("cyc", "LMOTS_E1u", "exec_accept", (174.3, 415.1, 892.3, 2434.2)),
        ("cyc", "C1_E1g", "Auto_AcceptPk", (275.3, 622.7, 1227.1, 3400.8)),
    )
    for tool, model, lemma, expected in curves:
        points = {r["heap_cap"]: r for r in ladder
                  if (r["tool"], r["model"], r["lemma"]) == (tool, f"{model}__T0.spthy", lemma)}
        points["56g"] = reference[f"P2_{tool}_{model}_T0_{lemma}_d_prove"]
        observed = tuple(points[cap]["seconds"] for cap in ("8g", "16g", "32g", "56g"))
        heap = all(points[cap]["verdict"] == "HEAP" for cap in points)
        compare(f"L seconds to heap exhaustion {tool} {model} {lemma}", observed if heap else None, expected)


def generated_and_handwritten(compare):
    compare("G ProVerif verdict rows", len(json_lines("runs/G/proverif/pv_results.jsonl")), 28)
    x0 = json_lines("runs/X0/original/triangulation.jsonl")
    compare("X0 pairs of model and lemma", len({(r["model"], r["lemma"]) for r in x0
                                                if not r["model"].startswith(("A_", "C1_"))}), 40)
    renamed = Counter(r["after"] for r in read_tsv("runs/X0/post-rename.tsv"))
    for label, target in (("true", 9), ("false", 1), ("cannot be proved", 26), ("TIMEOUT", 4)):
        compare(f"X0 after renaming {label}", renamed[label], target)
    compare("X0 rerun inputs with the recorded hash",
            sum(file_digest(ROOT / "runs/X0/alpha-fix" / f"{r['model']}__{r['lemma']}.pv") == r["patched_sha256"]
                for r in json_lines("runs/X0/alpha-fix/pvfix_results.jsonl")), 15)
    chain = read_json("runs/chain/native-closeout/native_results.json")["properties"]
    counts = Counter((r["kind"], r["verdict"]) for r in chain)
    for kind, verdict, target in (("all-traces", "verified", 4), ("all-traces", "falsified", 1),
                                  ("exists-trace", "verified", 2)):
        compare(f"C1 {kind} {verdict}", counts[kind, verdict], target)


def exporter(compare):
    probes = read_tsv("runs/X1/historical-probes/state_comparisons.tsv")
    for name, target in (("initial", 16), ("z0", 10), ("source-fixed", 13), ("guard", 16)):
        compare(f"Exporter probe {name} agreements",
                sum(r["cohort_id"] == f"probe-{name}" and r["comparison_to_native"] == "MATCH"
                    for r in probes), target)
    x1 = read_tsv("runs/X1/comparison.tsv")
    compare("X1 theories", len({(r["suite"], r["case"]) for r in x1}), 21)
    compare("X1 pairs of model and lemma", len({(r["suite"], r["case"], r["lemma"]) for r in x1}), 60)
    for build, column, target in (("B0", "baseline", 49), ("B1", "leafless", 59), ("B2", "row_guards", 60)):
        compare(f"X1 {build} agreements", sum(r[column] == r["native"] for r in x1), target)
    stages = read_tsv("runs/X1/jobs.tsv")
    compare("X1 stage invocations", len({(r["build"], r["suite"], r["case"], r["lemma"], r["stage"])
                                         for r in stages}), 540)
    compare("X1 invocations with exit status 0", sum(r["exit_code"] == "0" for r in stages), 540)
    compare("X1 stage metadata files", sum((ROOT / r["metadata_path"]).is_file() for r in stages), 540)

    x2 = read_tsv("runs/X2/lms_hss_application_cndk8z5k/results/comparison.tsv")
    compare("X2 completed exports", sum(r[column] == "EXPORTED" for r in x2
                                        for column in ("baseline_status", "candidate_status")), 20)
    compare("X2 changed translation bodies", sum(r["body_equal"] == "False" for r in x2), 7)
    compare("X2 equal declarations and queries", sum(r["declarations_query_prefix_equal"] == "True"
                                                     for r in x2), 10)
    for lemma, steps in (("exec", 14), ("LS7", 408)):
        text = (ROOT / f"runs/X2/hss_native_dginj/{lemma}/result-lines.txt").read_text()
        found = re.search(r"verified \((\d+) steps\)", text)
        compare(f"X2 native HSS {lemma} steps", int(found[1]) if found else None, steps)
        compare(f"X2 HSS {lemma} translated inputs byte-identical",
                (ROOT / f"runs/X2/hss_model_link/{lemma}/generated.pv").read_bytes()
                == (ROOT / f"runs/X2/hss_premises/{lemma}/dginj_only/input.pv").read_bytes(), True)


def kudos_and_corpus(compare):
    stage_d = [r for r in read_tsv("runs/K/stage-d/stage_d_results.tsv") if r["cohort"] == "original"]
    compare("K comparisons", len(stage_d), 49)
    compare("K agreements", sum(r["status"] == "MATCH" for r in stage_d), 48)
    jobs = read_tsv("runs/K/jobs.tsv")
    compare("K model inputs", len({(r["case"], r["tool"]) for r in jobs}), 24)
    compare("K model inputs with the recorded hash",
            sum(file_digest(ROOT / r["model_path"]) == r["sha256"] for r in jobs), 24)
    morio = Counter(r["proverif_category"] for r in read_tsv("corpus/morio/subset41.tsv"))
    compare("Corpus subset rows", morio.total(), 41)
    for label, target in (("boolean", 1), ("out of memory", 17), ("timeout", 12),
                          ("error", 6), ("no verdict", 5)):
        compare(f"Corpus subset ProVerif {label}", morio[label], target)


def mutation(compare):
    base = "runs/M/historical"
    pilot = read_json(f"{base}/oct28/pilot/results.json")
    compare("M pilot mutants", sum(x["case"] != "control" for x in pilot), 3)
    compare("M pilot detected", sum(x["detected"] for x in pilot if x["case"] != "control"), 2)
    compare("M pilot control detected", sum(x["detected"] for x in pilot if x["case"] == "control"), 0)

    main = f"{base}/oct29/mutation_extension_20261029"
    first = read_json(f"{main}/results.json")
    completed = [r for r in read_json(f"{main}/results_completed_reference.json")
                 if r["seed"] in {"lmots", "lms_s2"}]

    def differs(row):
        return any(result["discrepancy"] for result in row["results"])

    mutants = [r for r in completed if r["operator"] != "control"]
    controls = [r for r in completed if r["operator"] == "control"]
    compare("M main mutants", len(mutants), 20)
    compare("M main detected", sum(map(differs, mutants)), 12)
    compare("M main controls", len(controls), 2)
    compare("M main controls with a difference", sum(map(differs, controls)), 0)
    compare("M main Tamarin timeouts of the first run",
            sum(r["seed"] == "lms_s2" and r["tm_run"]["rc"] == 124 for r in first), 11)

    frozen = "runs/M/frozen_20261111"
    rows = read_json(f"{frozen}/results.json")
    tools = Counter(r["tool"] for r in rows)
    compare("M frozen ProVerif invocations", tools["PV"], 66)
    compare("M frozen ProVerif formulas", sum(len(r["results"]) for r in rows if r["tool"] == "PV"), 231)
    compare("M frozen Tamarin invocations", tools["TM"], 14)
    assessed = read_json(f"{frozen}/mutation_assessment.json")
    compare("M frozen mutants", len(assessed), 20)
    compare("M frozen detected with audit queries", sum(bool(x["detected"]) for x in assessed), 20)
    compare("M frozen detected with ordinary queries",
            sum(bool(x["ordinary_different_queries"]) for x in assessed), 18)


def scheduler(compare):
    result = read_json("scheduler/lemma1/results.json")
    log = (ROOT / "scheduler/lemma1/tests.log").read_text()
    compare("Lemma 1 tests", result["tests_run"], 21)
    compare("Lemma 1 failures and errors", result["failures"] + result["errors"], 0)
    compare("Lemma 1 passes in the stored log", len(re.findall(r"\.\.\. ok$", log, re.M)), 21)
    for key, target in (("atomic_states", 3), ("process_states", 13), ("abandoned_states", 3),
                        ("atomic_traces", 3), ("process_traces", 3)):
        compare(f"Lemma 1 {key.replace('_', ' ')}", result[key], target)


def main():
    checks = []

    def compare(name, observed, expected):
        equal = observed == expected
        checks.append(equal)
        print(f"{'ok' if equal else 'DIFFERS'}\t{name}\t{observed}\t{expected}")

    print("status\tcount\trecomputed\tpaper")
    for series in (screening, repetition, memory_ladder, generated_and_handwritten, exporter,
                   kudos_and_corpus, mutation, scheduler):
        series(compare)
    print(f"{len(checks)} counts recomputed, {checks.count(False)} differing.")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyError, OSError, ValueError) as error:
        sys.exit(str(error))
