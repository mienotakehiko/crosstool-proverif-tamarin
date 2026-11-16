#!/usr/bin/env python3
"""Recompute published counts from archived records, without launching provers."""
import argparse
from collections import Counter, defaultdict
import re
from statistics import median
import sys

from verify_evidence import ROOT, file_digest, json_lines, read_json, read_tsv


def screening():
    source = json_lines("runs/screening/checkpoints/U4_P4_results/results/records.jsonl")
    latest = {}
    for row in source:
        job = row["job"]
        if re.match(r"P[1-4]_", job) and (job not in latest or row["time"] >= latest[job]["time"]):
            latest[job] = row
    return latest


def baseline(compare):
    phases = {
        "P1": (81, 42, 11, 26, 2, 0, 0),
        "P2": (102, 46, 7, 35, 5, 7, 2),
        "P3": (24, 11, 9, 3, 1, 0, 0),
        "P4": (88, 85, 1, 2, 0, 0, 0),
    }
    labels = ("jobs", "verified", "falsified", "TIMEOUT", "KILLED", "HEAP", "ERROR")
    latest = screening()
    total = Counter()
    for phase, expected in phases.items():
        group = {job: row for job, row in latest.items() if job.startswith(phase + "_")}
        released = {row["job"]: row for row in json_lines(f"runs/{phase}/records.jsonl")}
        if group != released:
            raise ValueError(f"{phase}: the phase projection differs from the cumulative checkpoint")
        counts = Counter(row["verdict"] for row in group.values())
        counts["jobs"] = len(group)
        total.update(counts)
        for label, target in zip(labels, expected):
            compare(f"{phase} {label}", counts[label], target)
    for label, target in zip(labels, (295, 184, 28, 66, 8, 7, 2)):
        compare(f"Screening {label}", total[label], target)
    conclusive = total["verified"] + total["falsified"]
    compare("Screening conclusive", conclusive, 212)
    compare("Screening unresolved", total["jobs"] - conclusive, 83)

    records = json_lines("runs/P5/checkpoint/results/records.jsonl")
    original = {row["job"]: row for row in records if not row["job"].startswith("P5_")}
    trials = defaultdict(list)
    for row in records:
        if row["job"].startswith("P5_"):
            job = re.sub(r"_r[1-5]$", "", row["job"][3:])
            trials[job].append(row)
    outcomes = Counter(row["verdict"] for group in trials.values() for row in group)
    compare("P5 jobs", len(trials), 225)
    compare("P5 trials", outcomes.total(), 1125)
    compare("P5 verified", outcomes["verified"], 965)
    compare("P5 falsified", outcomes["falsified"], 160)
    matched = sum(len(group) for job, group in trials.items()
                  if len(group) == 5 and len({row["job"] for row in group}) == 5
                  and all(row["rc"] == 0 and (row["sha256"], row["verdict"]) ==
                          (original[job]["sha256"], original[job]["verdict"]) for row in group))
    compare("P5 trials matching baseline", matched, 1125)
    top = {job.split("_TopAuth_")[-1]: group for job, group in trials.items()
           if re.match(r"P[13]_std_HSS_LS7_inj_", job) and "_TopAuth_" in job}
    for heuristic, target in (
        ("d_prove", 11.4), ("t_prove", 1861.5), ("C_prove", 493.7),
        ("s_prove", 11.5), ("S_prove", 11.2), ("I_prove", 11.3),
    ):
        compare(f"P5 TopAuth {heuristic} median",
                median(row["seconds"] for row in top[heuristic]), target)
    compare("L ladder HEAP", sum(r["verdict"] == "HEAP" for r in
                                json_lines("runs/L/ladder/results/records.jsonl") if r["job"].startswith("L_")), 9)
    compare("L 96 GiB HEAP", sum(r["verdict"] == "HEAP" for r in
                                 json_lines("runs/L/u11/final-return/results/records.jsonl")), 7)
    compare("G direct ProVerif verdict rows", len(json_lines("runs/G/proverif/pv_results.jsonl")), 28)
    x0 = json_lines("runs/X0/original/triangulation.jsonl")
    compare("X0 model–lemma pairs", len({(r["model"], r["lemma"]) for r in x0
                                        if not r["model"].startswith(("A_", "C1_"))}), 40)
    historical_probes = read_tsv("registry/state_comparisons.tsv")
    for name, count in (("initial", 16), ("z0", 10), ("source-fixed", 13), ("guard", 16)):
        compare(f"Historical probe {name} agreements",
                sum(r["cohort_id"] == f"probe-{name}" and r["comparison_to_native"] == "MATCH"
                    for r in historical_probes), count)
    kudos = [r for r in read_tsv("runs/K/stage-d/stage_d_results.tsv") if r["cohort"] == "original"]
    compare("K original agreements", sum(r["status"] == "MATCH" for r in kudos), 48)
    compare("K original comparisons", len(kudos), 49)
    chain = read_json("runs/chain/native-closeout/native_results.json")["properties"]
    chain_counts = Counter((r["kind"], r["verdict"]) for r in chain)
    for kind, verdict, count in (("all-traces", "verified", 4), ("all-traces", "falsified", 1),
                                 ("exists-trace", "verified", 2)):
        compare(f"C1 {kind} {verdict}", chain_counts[kind, verdict], count)


def extensions(compare):
    x0 = Counter(r["after"] for r in read_tsv("runs/X0/post-rename.tsv"))
    for label, target in (("true", 9), ("false", 1), ("cannot be proved", 26), ("TIMEOUT", 4)):
        compare(f"X0 post-rename {label}", x0[label], target)
    compare("X0 rerun input hashes", sum(file_digest(ROOT / "runs/X0/alpha-fix" /
                                                    f"{r['model']}__{r['lemma']}.pv") == r["patched_sha256"]
                                        for r in json_lines("runs/X0/alpha-fix/pvfix_results.jsonl")), 15)
    x1 = read_tsv("runs/X1/comparison.tsv")
    compare("X1 distinct theory cases", len({(r["suite"], r["case"]) for r in x1}), 21)
    compare("X1 distinct model–lemma pairs", len({(r["suite"], r["case"], r["lemma"]) for r in x1}), 60)
    for build, column, expected in (("B0", "baseline", 49), ("B1", "leafless", 59), ("B2", "row_guards", 60)):
        compare(f"X1 {build} agreements", sum(r[column] == r["native"] for r in x1), expected)
    stages = read_tsv("runs/X1/jobs.tsv")
    compare("X1 staged invocations", len({(r["build"], r["suite"], r["case"], r["lemma"], r["stage"])
                                         for r in stages}), 540)
    compare("X1 exit-zero invocations", sum(r["exit_code"] == "0" for r in stages), 540)
    compare("X1 stage metadata", sum((ROOT / r["metadata_path"]).is_file() for r in stages), 540)

    x2 = read_tsv("runs/X2/lms_hss_application_cndk8z5k/results/comparison.tsv")
    compare("X2 completed exports", sum(r[col] == "EXPORTED" for r in x2
                                        for col in ("baseline_status", "candidate_status")), 20)
    compare("X2 changed translation bodies", sum(r["body_equal"] == "False" for r in x2), 7)
    compare("X2 same query/declaration prefix", sum(r["declarations_query_prefix_equal"] == "True"
                                                   for r in x2), 10)
    for lemma, value in (("exec", 14), ("LS7", 408)):
        native = ROOT / f"runs/X2/hss_native_dginj/{lemma}/result-lines.txt"
        result = re.search(r"verified \((\d+) steps\)", native.read_text())
        compare(f"X2 native HSS {lemma} steps", int(result[1]) if result else None, value)
        compare(f"X2 HSS {lemma} translated input byte identity",
                (ROOT / f"runs/X2/hss_model_link/{lemma}/generated.pv").read_bytes()
                == (ROOT / f"runs/X2/hss_premises/{lemma}/dginj_only/input.pv").read_bytes(), True)
    kudos = read_tsv("runs/K/jobs.tsv")
    compare("K indexed model/tool slots", len({(r["case"], r["tool"]) for r in kudos}), 24)
    compare("K model input hashes", sum(file_digest(ROOT / r["model_path"]) == r["sha256"]
                                         for r in kudos), 24)
    morio = Counter(r["proverif_category"] for r in read_tsv("corpus/morio/subset41.tsv"))
    compare("Morio subset size", morio.total(), 41)
    for label, n in (("boolean", 1), ("out of memory", 17), ("timeout", 12),
                     ("error", 6), ("no verdict", 5)):
        compare(f"Morio subset ProVerif {label}", morio[label], n)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-only", action="store_true", help="limit the output to the 61 baseline checks")
    args = parser.parse_args()
    checks = []

    def compare(name, observed, expected):
        ok = observed == expected
        checks.append(ok)
        print(f"{'ok' if ok else 'FAIL'}\t{name}\t{observed}\t{expected}")

    print("status\tmetric\tobserved\texpected")
    baseline(compare)
    if not args.baseline_only:
        extensions(compare)
    print(f"{len(checks)} comparison(s), {checks.count(False)} comparison(s) failed.")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyError, OSError, ValueError) as error:
        sys.exit(str(error))
