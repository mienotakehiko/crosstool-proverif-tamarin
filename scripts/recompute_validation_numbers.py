#!/usr/bin/env python3
"""Recompute the counts of the validation series V1 to V7 from the run records.

    python3 -B scripts/recompute_validation_numbers.py --check validation/expected_counts.tsv

The script prints one line "key<TAB>value" for every count. With --check it
compares the counts with a stored table and ends with status 1 if a value
differs. With --out it writes the table. The option --validation names the
directory of the series and defaults to validation. The option --cimc names
the generator whose program al_assign computes the Achievement Levels and
defaults to cimc/v0.1.2.

The cross-check of verdict pairs comes from validation/common/xcheck.py, the
script that produced the counts of the runs. This script starts no prover.
"""
import argparse
import collections
import csv
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "validation", "common"))
import xcheck  # noqa: E402

FACTS = collections.OrderedDict()


def fact(key, value):
    FACTS[key] = str(value)


def rows(path):
    return [json.loads(line) for line in open(path) if line.strip()] if os.path.exists(path) else []


def last(path, key):
    table = collections.OrderedDict()
    for record in rows(path):
        table[(record["model"], record[key])] = record
    return table


def first(path, key):
    table = collections.OrderedDict()
    for record in rows(path):
        table.setdefault((record["model"], record[key]), record)
    return table


def set_dirs(root, names=None):
    out = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(os.path.join(path, "results")) and (names is None or name in names):
            out.append(path)
    return out


def summarize(prefix, dirs, expected=None):
    """Count the records of a list of model sets and return the cross-check reports."""
    count = collections.Counter()
    reports = []
    for path in dirs:
        pv = last(os.path.join(path, "results", "pv_results.jsonl"), "query")
        tm = last(os.path.join(path, "results", "tam_results.jsonl"), "lemma")
        report = xcheck.check_set(path, expected or {})
        reports.append(report)
        count["sets"] += 1
        count["records"] += report["records"]
        count["conclusive"] += report["conclusive"]
        count["properties"] += report["properties"]
        count["agree_T"] += report["both_tools_agree_on_T"]
        count["differ_T"] += report["both_tools_differ_on_T"]
        count["excluded_pairs"] += len(report["excluded_pairs"])
        count["unexpected"] += len(report["unexpected"])
        count["predicted_without_verdict"] += len(report["unresolved"])
        count["pv_records"] += len(pv)
        count["tm_records"] += len(tm)
        for record in pv.values():
            count["pv_" + record["verdict"]] += 1
        for record in tm.values():
            count["tm_" + record["verdict"]] += 1
        count["negative_durations"] += sum(1 for r in list(pv.values()) + list(tm.values())
                                           if isinstance(r.get("seconds"), (int, float)) and r["seconds"] < 0)
    for key in ("sets", "records", "conclusive", "properties", "agree_T", "differ_T", "excluded_pairs",
                "unexpected", "predicted_without_verdict", "pv_records", "tm_records",
                "pv_true", "pv_false", "pv_cannot", "pv_TIMEOUT", "tm_verified", "tm_falsified",
                "tm_TIMEOUT", "tm_HEAP", "negative_durations"):
        fact(f"{prefix}.{key}", count[key])
    fact(f"{prefix}.pv_conclusive", count["pv_true"] + count["pv_false"])
    fact(f"{prefix}.tm_conclusive", count["tm_verified"] + count["tm_falsified"])
    return reports


def predictions(prefix, dirs, expected):
    """Count the predicted cells that the verdicts confirm, contradict or leave open."""
    confirmed = contradicted = open_ = 0
    for path in dirs:
        report = xcheck.check_set(path, expected)
        name = report["set"].lower()
        for prop, cells in report["rows"]:
            for short, cell in cells.items():
                allowed = expected.get((name, prop, short.rstrip("0123456789")))
                if not allowed:
                    continue
                outcome = cell[0]
                if outcome in allowed:
                    confirmed += 1
                elif outcome == "N":
                    open_ += 1
                else:
                    contradicted += 1
    fact(f"{prefix}.predicted_cells", confirmed + contradicted + open_)
    fact(f"{prefix}.predictions_confirmed", confirmed)
    fact(f"{prefix}.predictions_contradicted", contradicted)
    fact(f"{prefix}.predictions_open", open_)


def al_levels(prefix, dirs, cimc):
    """Compute the Achievement Levels of each system with al_assign of the generator."""
    levels = collections.defaultdict(collections.Counter)
    for path in dirs:
        checks = glob.glob(os.path.join(path, "*_checks.txt"))
        cim = os.path.join(path, "cim.toml")
        if not checks or not os.path.exists(cim):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            for name, key in (("pv_results.jsonl", "query"), ("tam_results.jsonl", "lemma")):
                with open(os.path.join(tmp, name), "w") as handle:
                    for record in last(os.path.join(path, "results", name), key).values():
                        handle.write(json.dumps(record) + "\n")
            code = "import sys; sys.path.insert(0, %r); from cimc.al_assign import main; main()" % cimc
            done = subprocess.run([sys.executable, "-I", "-B", "-c", code, os.path.abspath(cim), os.path.abspath(checks[0]),
                                   "-o", os.path.join(tmp, "al"), "--pv", os.path.join(tmp, "pv_results.jsonl"),
                                   "--tm", os.path.join(tmp, "tam_results.jsonl")],
                                  capture_output=True, text=True, cwd=tmp)
            if done.returncode != 0:
                sys.exit(f"al_assign failed for {path}: {done.stderr[-300:]}")
            report = json.load(open(os.path.join(tmp, "al.json")))
        for prop in report["properties"].values():
            for system in prop["systems"]:
                levels[system["system"]][system["level"]] += 1
    for system in ("T", "Trb", "Tcl", "Tom"):
        total = sum(levels[system].values())
        fact(f"{prefix}.al.{system}.cells", total)
        for level in range(5):
            fact(f"{prefix}.al.{system}.level{level}", levels[system][level])


def verdict_table(path):
    table = {}
    for (model, query), record in last(os.path.join(path, "results", "pv_results.jsonl"), "query").items():
        table[(model.split("_PV_")[-1], query)] = record["verdict"]
    for (model, lemma), record in last(os.path.join(path, "results", "tam_results.jsonl"), "lemma").items():
        table[(model.split("_T_")[-1], lemma)] = record["verdict"]
    return table


def lin_regularity(prefix, dirs):
    """Relate the answer "cannot be proved" on the linear encoding to state reuse."""
    count = collections.Counter()
    for path in dirs:
        for prop, cells in xcheck.check_set(path, {})["rows"]:
            if "lin" not in cells or "base" not in cells or "omega" not in cells:
                continue
            base, lin = cells["base"][0], cells["lin"]
            reuse = any(cells.get(short, "N")[0] == "W" for short in cells
                        if short in ("omega", "rep", "cl1", "rb1") or short.startswith("Urb"))
            separated = base == "H" and reuse
            if lin.startswith("N(cannot"):
                count["cannot"] += 1
                count["cannot_separated" if separated else "cannot_other"] += 1
            elif lin[0] in "HW":
                count["decided"] += 1
                count["decided_separated" if separated else "decided_other"] += 1
                count["decided_equal_to_base"] += lin[0] == base
    for key in ("cannot", "cannot_separated", "cannot_other", "decided", "decided_separated", "decided_other",
                "decided_equal_to_base"):
        fact(f"{prefix}.lin.{key}", count[key])


def family_sets(root):
    """Return the model sets of the three families of series V1."""
    sets = set_dirs(os.path.join(root, "V1-families", "sets"))
    return [[path for path in sets if os.path.basename(path).startswith(prefix)]
            for prefix in ("lmots_", "otp_", "lms_")]


def refused_inputs(root):
    path = os.path.join(root, "V1-families", "refused_by_0.1.2.txt")
    return [line.strip() for line in open(path) if line.strip()]


def series_v1(root, cimc):
    expected = xcheck.read_expected(os.path.join(root, "V1-families", "inputs", "fixed", "expected_e1.tsv"))
    lmots, otp, lms = family_sets(root)
    refused = refused_inputs(root)
    fact("V1.original_inputs", len(lmots) + len(refused))
    fact("V1.original_inputs_refused", len(refused))
    for prefix, dirs in (("V1.lmots", lmots), ("V1.otp", otp), ("V1.lms", lms), ("V1.all", lmots + otp + lms)):
        summarize(prefix, dirs, expected)
        predictions(prefix, dirs, expected)
        lin_regularity(prefix, dirs)
        if cimc:
            al_levels(prefix, dirs, cimc)
    # The first pass of the LMS family is the first record of every job.
    count = collections.Counter()
    for path in lms:
        for name, key in (("pv_results.jsonl", "query"), ("tam_results.jsonl", "lemma")):
            for record in first(os.path.join(path, "results", name), key).values():
                count["records"] += 1
                count["conclusive"] += record["verdict"] in ("true", "false", "verified", "falsified")
    fact("V1.lms.first_pass_records", count["records"])
    fact("V1.lms.first_pass_conclusive", count["conclusive"])
    # Tamarin jobs without a verdict in the first pass, and the outcome of their second attempt.
    outcome = collections.Counter()
    for path in lms:
        attempts = collections.defaultdict(list)
        for record in rows(os.path.join(path, "results", "tam_results.jsonl")):
            attempts[(record["model"], record["lemma"])].append(record)
        for job, records in attempts.items():
            if records[0]["verdict"] != "TIMEOUT":
                continue
            late, early = records[0].get("rss_growth_late_mb_per_min"), records[0].get("rss_growth_early_mb_per_min")
            flat = late is not None and early is not None and (late <= 0.10 * early or late <= 1.0)
            label = "TM-search" if flat else "TM-res"
            final = records[-1]
            if final["verdict"] in ("verified", "falsified"):
                kind = "verdict"
            elif final["verdict"] == "HEAP":
                kind = "heap"
            else:
                kind = "timeout"
            outcome["first_pass_timeouts"] += 1
            outcome[f"{label}"] += 1
            outcome[f"{label}.{kind}"] += 1
            outcome[f"retry.{kind}"] += 1
            if kind == "verdict":
                peak = final.get("rss_max_mb") or 0
                size = "rss_above_16g" if peak > 16 * 1024 else "rss_within_16g"
                outcome[f"retry.verdict.{size}"] += 1
                outcome[f"{label}.verdict.{size}"] += 1
    for key in ("first_pass_timeouts", "TM-search", "TM-res", "retry.verdict", "retry.heap", "retry.timeout",
                "TM-search.verdict", "TM-search.heap", "TM-search.timeout", "TM-res.verdict", "TM-res.heap",
                "TM-res.timeout", "retry.verdict.rss_within_16g", "retry.verdict.rss_above_16g",
                "TM-search.verdict.rss_within_16g", "TM-search.verdict.rss_above_16g",
                "TM-res.verdict.rss_within_16g", "TM-res.verdict.rss_above_16g"):
        fact(f"V1.lms.resource.{key}", outcome[key])
    # Cost of the standard variant as the number of leaves grows.
    for name in ("lms_h1w1", "lms_h2w1", "lms_h3w1", "lms_h1w2", "lms_h2w2"):
        path = os.path.join(root, "V1-families", "sets", name)
        tm = last(os.path.join(path, "results", "tam_results.jsonl"), "lemma")
        base = [r for (model, _), r in tm.items() if model.endswith("_T_base")]
        fact(f"V1.scaling.{name}.base_lemmas", len(base))
        fact(f"V1.scaling.{name}.base_conclusive", sum(r["verdict"] in ("verified", "falsified") for r in base))
        fact(f"V1.scaling.{name}.base_steps", sum(r.get("steps") or 0 for r in base))
        fact(f"V1.scaling.{name}.base_seconds", round(sum(r.get("seconds") or 0 for r in base), 2))
        peaks = [r.get("rss_max_mb") for r in base if r.get("rss_max_mb")]
        fact(f"V1.scaling.{name}.base_rss_max_mb", max(peaks) if peaks else 0)
        pv = last(os.path.join(path, "results", "pv_results.jsonl"), "query")
        for short in ("U", "Urb", "lin", "rep"):
            mine = [r for (model, _), r in pv.items()
                    if model.split("_PV_")[-1].rstrip("0123456789") == short]
            seconds = sorted({r.get("seconds") for r in mine})
            fact(f"V1.scaling.{name}.pv_{short}_seconds", seconds[-1] if seconds else "")
            fact(f"V1.scaling.{name}.pv_{short}_verdicts", sum(r["verdict"] in ("true", "false", "cannot") for r in mine))
        sizes = [os.path.getsize(p) for p in glob.glob(os.path.join(path, "*.pv"))]
        fact(f"V1.scaling.{name}.largest_pv_bytes", max(sizes) if sizes else 0)


def series_v2(root):
    dirs = set_dirs(os.path.join(root, "V2-random", "sets"))
    reports = summarize("V2.random", dirs)
    lin_regularity("V2.random", dirs)
    separation = collections.Counter()
    for path, report in zip(dirs, reports):
        for prop, cells in report["rows"]:
            base, omega, lin = cells.get("base", "N")[0], cells.get("omega", "N")[0], cells.get("lin", "N")[0]
            separation[f"base_{base}"] += 1
            reuse = any(cells.get(short, "N")[0] == "W" for short in cells
                        if short in ("omega", "rep", "cl1", "rb1") or short.startswith("Urb"))
            if base == "H" and reuse:
                separation["holds_on_T_fails_with_reuse"] += 1
            if lin == "N":
                separation["lin_without_verdict"] += 1
            if prop in ("accept", "auth", "forge"):
                separation[f"verifier_{base}"] += 1
    for key in ("base_H", "base_W", "base_N", "holds_on_T_fails_with_reuse", "lin_without_verdict",
                "verifier_H", "verifier_W"):
        fact(f"V2.random.{key}", separation[key])
    limits = collections.Counter()
    for path in dirs:
        for record in last(os.path.join(path, "results", "tam_results.jsonl"), "lemma").values():
            limits[(record.get("timeout_s"), record.get("heap_cap"))] += 1
            if record["verdict"] == "TIMEOUT":
                limits["timeout:" + record["model"].split("_T_")[-1]] += 1
    fact("V2.random.tm_limits", ";".join(f"{t}s/{h}:{n}" for (t, h), n in sorted(
        (k, v) for k, v in limits.items() if isinstance(k, tuple))))
    fact("V2.random.tm_timeouts_on_cl1", limits["timeout:cl1"])
    inputs = os.path.join(root, "V2-random", "inputs")
    originals = glob.glob(os.path.join(inputs, "fixed", "*.toml"))
    renamed = glob.glob(os.path.join(inputs, "renamed", "*.toml"))
    changed = 0
    for path in renamed:
        twin = os.path.join(inputs, "fixed", os.path.basename(path))
        if os.path.exists(twin) and open(twin).read() != open(path).read():
            changed += 1
    fact("V2.random.inputs", len(renamed))
    fact("V2.random.inputs_original", len(originals))
    fact("V2.random.inputs_changed_by_renaming", changed)
    # The boundary probes comprise twelve fixed probes, two renamed controls and four pair-shaped probes.
    boundary = os.path.join(root, "V2-boundary")
    fixed = os.path.join(boundary, "sets", "fixed")
    outcomes = list(csv.DictReader(open(os.path.join(fixed, "boundary_generator.tsv")), delimiter="\t"))
    fact("V2.boundary.probes", len(outcomes))
    fact("V2.boundary.probes_with_model_files",
         sum(bool(glob.glob(os.path.join(fixed, row["probe"], "*.pv"))) for row in outcomes))
    summarize("V2.boundary.det_fail", set_dirs(fixed))
    summarize("V2.boundary.controls", set_dirs(os.path.join(boundary, "sets", "controls")))
    pair = os.path.join(boundary, "sets", "pair")
    for probe, report in zip(set_dirs(pair), summarize("V2.boundary.pair", set_dirs(pair))):
        fact(f"V2.boundary.pair.{os.path.basename(probe)}.excluded_pairs", len(report["excluded_pairs"]))
    for label, table in (("0.1.2", os.path.join(pair, "boundary_generator.tsv")),
                         ("0.1.3", os.path.join(pair, "generator-0.1.3", "boundary_generator.tsv"))):
        refused = [row["probe"] for row in csv.DictReader(open(table), delimiter="\t") if row["generator"] == "reject"]
        fact(f"V2.boundary.pair.refused_by_{label}", len(refused))


def series_v3(root):
    folder = os.path.join(root, "V3-diagnosis")
    labels = list(csv.DictReader(open(os.path.join(folder, "labels.tsv")), delimiter="\t"))
    predicted = {r["item"]: r["cause"]
                 for r in csv.DictReader(open(os.path.join(folder, "predictions.tsv")), delimiter="\t")}
    fact("V3.items", len(labels))
    by = collections.Counter(r["cause"] for r in labels)
    for cause in ("ENC-map", "ENC-clone", "PV-abs", "PV-rec", "PV-term", "TM-res", "TM-search", "SPEC-expr"):
        fact(f"V3.items.{cause}", by[cause])
    fact("V3.correct", sum(predicted.get(r["item"]) == r["cause"] for r in labels))


def series_v4(validation):
    root = os.path.join(validation, "V4-mutation", "sets")
    dirs = set_dirs(root)
    summarize("V4.all", dirs)
    result = collections.Counter()
    per_operator = collections.defaultdict(collections.Counter)
    for base in ("LMOTS", "LMS_S2"):
        control_dir = os.path.join(root, base + "__control")
        control = verdict_table(control_dir)
        fact(f"V4.control.{base}.pv_verdicts", sum(1 for v in control.values() if v in ("true", "false", "cannot")))
        fact(f"V4.control.{base}.tm_verdicts", sum(1 for v in control.values() if v in ("verified", "falsified")))
        control_pairs = {(p["property"], p["holds_on"], p["trace_on"])
                         for p in xcheck.check_set(control_dir, {})["excluded_pairs"]}
        result["control_pairs"] += len(control_pairs)
        for path in dirs:
            name = os.path.basename(path)
            if not name.startswith(base + "__") or name.endswith("__control"):
                continue
            operator = name.split("__")[1]
            kind = "property" if operator.startswith("spec_") else "encoding"
            pairs = {(p["property"], p["holds_on"], p["trace_on"])
                     for p in xcheck.check_set(path, {})["excluded_pairs"]} - control_pairs
            table = verdict_table(path)
            changed = sum(1 for key, value in table.items() if control.get(key) != value
                          and value in ("true", "false", "verified", "falsified"))
            result[f"{kind}.mutants"] += 1
            if pairs:
                result[f"{kind}.detected"] += 1
                per_operator[operator]["detected"] += 1
            elif changed:
                result[f"{kind}.verdict_changed_without_pair"] += 1
                per_operator[operator]["changed"] += 1
            else:
                result[f"{kind}.no_verdict_changed"] += 1
                per_operator[operator]["silent"] += 1
    for key in ("encoding.mutants", "encoding.detected", "encoding.verdict_changed_without_pair",
                "encoding.no_verdict_changed", "property.mutants", "property.detected",
                "property.no_verdict_changed", "control_pairs"):
        fact(f"V4.{key}", result[key])
    for operator in sorted(per_operator):
        fact(f"V4.operator.{operator}", "detected %d, silent %d" % (per_operator[operator]["detected"],
                                                                     per_operator[operator]["silent"]))
    table = list(csv.DictReader(open(os.path.join(validation, "V4-mutation", "input-side", "cim_mutants.tsv")),
                                delimiter="\t"))
    fact("V4.input.mutants", len(table))
    fact("V4.input.refused", sum(r["generator"] == "reject" for r in table))
    refused_parents = set(refused_inputs(validation))
    own = [r for r in table if r["mutant"].split("__")[0] not in refused_parents]
    fact("V4.input.mutants_of_accepted_parents", len(own))
    fact("V4.input.refused_of_accepted_parents", sum(r["generator"] == "reject" for r in own))
    fact("V4.input.accepted_operators", ",".join(sorted({r["operator"] for r in own if r["generator"] != "reject"})))


def series_v7(root):
    table = list(csv.DictReader(open(os.path.join(root, "V7-time-limit", "status.tsv")), delimiter="\t"))
    fact("V7.jobs", len(table))
    fact("V7.timeouts", sum(r["verdict"] == "TIMEOUT" for r in table))
    fact("V7.verdicts", sum(r["verdict"] in ("verified", "falsified") for r in table))
    seconds = sorted(float(r["seconds"]) for r in table)
    fact("V7.seconds_min", seconds[0])
    fact("V7.seconds_max", seconds[-1])
    fact("V7.seconds_below_limit", sum(s < 14400 for s in seconds))


def main():
    root = os.path.abspath(os.path.join(HERE, ".."))
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--validation", default=os.path.join(root, "validation"))
    parser.add_argument("--cimc", default=os.path.join(root, "cimc", "v0.1.2"))
    parser.add_argument("--check")
    parser.add_argument("--out")
    args = parser.parse_args()
    if not os.path.isdir(os.path.join(args.cimc, "cimc")):
        sys.exit(f"{args.cimc} holds no generator")
    series_v1(args.validation, args.cimc)
    series_v2(args.validation)
    series_v3(args.validation)
    series_v4(args.validation)
    series_v7(args.validation)
    # The model sets without a failed side condition are the three families, the random models,
    # the two control probes and the two fixed signers.
    lmots, otp, lms = family_sets(args.validation)
    dirs = (lmots + otp + lms
            + set_dirs(os.path.join(args.validation, "V2-random", "sets"))
            + set_dirs(os.path.join(args.validation, "V2-boundary", "sets", "controls"))
            + [os.path.join(args.validation, "V4-mutation", "sets", name)
               for name in ("LMOTS__control", "LMS_S2__control")])
    summarize("ALL.no_fail", dirs)
    lin_regularity("ALL.no_fail", dirs)
    text = "".join(f"{key}\t{value}\n" for key, value in FACTS.items())
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text)
    elif not args.check:
        sys.stdout.write(text)
    if args.check:
        stored = dict(line.rstrip("\n").split("\t", 1) for line in open(args.check) if line.strip())
        differing = [key for key in stored if FACTS.get(key) != stored[key]]
        for key in differing:
            print(f"DIFFERS\t{key}\tstored {stored[key]}\trecomputed {FACTS.get(key)}")
        print(f"{len(stored)} stored counts, {len(differing)} differing.")
        sys.exit(1 if differing else 0)


if __name__ == "__main__":
    main()
