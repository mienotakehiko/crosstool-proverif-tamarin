#!/usr/bin/env python3
"""Cross-check the verdicts of generated model sets against the inclusion chain.

    python3 -B xcheck.py SETDIR [SETDIR ...] [--expected FILE] [--json OUT]

Each SETDIR holds the eight generated models of one Common Iterative Model,
the side-condition report (*_checks.txt) and the files
results/pv_results.jsonl and results/tam_results.jsonl of run_set.py.

The script is independent of the generator. It normalizes every verdict to
  H  the model has no trace of the kind that the property describes,
  W  the model has such a trace (an attack, or a witness of reachability),
  N  no outcome,
places every model between two systems of the chain
  T<=n  <=  T  <=  T_cl, T_rb  <=  T_omega,
and reports each pair "H on model A, W on model B" in which every trace of B
is a trace of A. Such a pair cannot occur if the correspondence hypothesis
holds and both tools are sound (Corollary 1 of the paper).

The script ends with status 1 if an excluded pair or an unexpected outcome
occurs.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

ORDER = {("Tle", "T"), ("T", "Tcl"), ("T", "Trb"), ("Tcl", "Tom"), ("Trb", "Tom")}
SYSTEMS = ("Tle", "T", "Tcl", "Trb", "Tom")


def closure(edges):
    relation = {(s, s) for s in SYSTEMS} | set(edges)
    changed = True
    while changed:
        changed = False
        for a, b in list(relation):
            for c, d in list(relation):
                if b == c and (a, d) not in relation:
                    relation.add((a, d))
                    changed = True
    return relation


def placement(model):
    """Return (tool, lower system, upper system, short name) of a generated model."""
    match = re.search(r"_PV_(Urb|U)(\d+)$", model)
    if match and match.group(1) == "U":
        return "PV", "Tle", "Tle", "U" + match.group(2)
    if match:
        return "PV", None, "Trb", "Urb" + match.group(2)      # under-approximation
    if model.endswith("_PV_lin"):
        return "PV", "T", "T", "lin"
    if model.endswith("_PV_rep"):
        return "PV", "Tom", "Tom", "rep"
    match = re.search(r"_T_(base|cl1|rb1|omega)$", model)
    if match:
        system = {"base": "T", "cl1": "Tcl", "rb1": "Trb", "omega": "Tom"}[match.group(1)]
        return "TM", system, system, match.group(1)
    raise ValueError(f"unknown model: {model}")


def lemma_table(setdir):
    """Map each lemma and variant to two flags, exists-trace and misuse event in the formula."""
    table = collections.defaultdict(dict)
    for path in glob.glob(os.path.join(setdir, "*_T_*.spthy")):
        variant = re.search(r"_T_(\w+)\.spthy$", path).group(1)
        text = open(path).read()
        for match in re.finditer(r"^lemma (\w+)(?: \[[^\]]*\])?:( exists-trace)?\s*\n\s*\"([^\"]*)\"", text, re.M):
            formula = match.group(3)
            table[match.group(1)][variant] = (bool(match.group(2)), "Clone(" in formula or "Rollback(" in formula)
    return table


def bound_holds(setdir):
    for path in glob.glob(os.path.join(setdir, "*_checks.txt")):
        for line in open(path):
            if line.startswith("Bound"):
                return line.split()[1] == "OK"
    return False


def last_records(path, key):
    """Return the records of a result file. If a job has several records, the last one counts."""
    last = {}
    if os.path.exists(path):
        for line in open(path):
            if line.strip():
                record = json.loads(line)
                last[(record["model"], record[key])] = record
    return list(last.values())


def load(setdir):
    lemmas = lemma_table(setdir)
    records = []
    results = os.path.join(setdir, "results")
    for r in last_records(os.path.join(results, "pv_results.jsonl"), "query"):
        outcome = {"true": "H", "false": "W"}.get(r["verdict"], "N")
        records.append(dict(model=r["model"], prop=r["query"], outcome=outcome, raw=r["verdict"]))
    for r in last_records(os.path.join(results, "tam_results.jsonl"), "lemma"):
        variant = placement(r["model"])[3]
        exists = lemmas.get(r["lemma"], {}).get(variant, (False, False))[0]
        if r["verdict"] == "verified":
            outcome = "W" if exists else "H"
        elif r["verdict"] == "falsified":
            outcome = "H" if exists else "W"
        else:
            outcome = "N"
        records.append(dict(model=r["model"], prop=r["lemma"], outcome=outcome, raw=r["verdict"]))
    return lemmas, records


def check_set(setdir, expected):
    lemmas, records = load(setdir)
    edges = set(ORDER)
    if bound_holds(setdir):
        edges.add(("T", "Tle"))                  # With a finite update bound, T<=n equals T.
    leq = closure(edges)
    name = os.path.basename(os.path.normpath(setdir))
    by_prop = collections.defaultdict(list)
    for record in records:
        record["tool"], record["lo"], record["hi"], record["short"] = placement(record["model"])
        by_prop[record["prop"]].append(record)
    pairs, unexpected, unresolved, rows = [], [], [], []
    for prop in sorted(by_prop):
        group = by_prop[prop]
        # A formula that names the misuse event differs between the variants, so
        # its verdicts on T_cl and T_rb enter no comparison with another model.
        special = {v for v, (_, misuse) in lemmas.get(prop, {}).items() if misuse}
        usable = [r for r in group if r["short"] not in special]
        for a in usable:
            for b in usable:
                if a["outcome"] == "H" and b["outcome"] == "W" and a["lo"] is not None \
                        and (b["hi"], a["lo"]) in leq:
                    pairs.append(dict(set=name, property=prop, holds_on=a["model"], trace_on=b["model"]))
        cells = {r["short"]: r["outcome"] + ("" if r["outcome"] != "N" else f"({r['raw']})") for r in group}
        rows.append((prop, cells))
        for record in group:
            allowed = expected.get((name.lower(), prop, record["short"].rstrip("0123456789")))
            if allowed and record["outcome"] not in allowed:
                item = dict(set=name, property=prop, model=record["model"],
                            outcome=record["outcome"], expected="|".join(sorted(allowed)))
                # A missing outcome contradicts no prediction, and the report lists it separately.
                (unresolved if record["outcome"] == "N" else unexpected).append(item)
    conclusive = sum(1 for r in records if r["outcome"] != "N")
    # agreement of the two tools on the standard system T
    agree = disagree = 0
    for prop, group in by_prop.items():
        pv = {r["outcome"] for r in group if r["tool"] == "PV" and r["lo"] is not None and r["outcome"] != "N"
              and (r["lo"], "T") in leq and ("T", r["hi"]) in leq}
        tm = {r["outcome"] for r in group if r["short"] == "base" and r["outcome"] != "N"}
        if pv and tm:
            if pv == tm:
                agree += 1
            else:
                disagree += 1
    return dict(set=name, records=len(records), conclusive=conclusive, properties=len(by_prop),
                both_tools_agree_on_T=agree, both_tools_differ_on_T=disagree,
                excluded_pairs=pairs, unexpected=unexpected, unresolved=unresolved, rows=rows)


def read_expected(path):
    """Read a TSV file with the columns set, property, model and allowed outcomes (H|W|N)."""
    table = {}
    if not path:
        return table
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        name, prop, model, allowed = line.rstrip("\n").split("\t")[:4]
        model = {"cl": "cl", "rb": "rb"}.get(model, model)
        table[(name.lower(), prop, model)] = set(allowed.split("|"))
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("setdirs", nargs="+")
    parser.add_argument("--expected")
    parser.add_argument("--json")
    args = parser.parse_args()
    expected = read_expected(args.expected)
    reports = [check_set(d, expected) for d in args.setdirs]
    columns = ("U", "Urb", "lin", "rep", "base", "rb1", "cl1", "omega")
    for report in reports:
        print(f"== {report['set']}: {report['conclusive']} of {report['records']} verdicts conclusive, "
              f"{len(report['excluded_pairs'])} excluded pair(s), {len(report['unexpected'])} unexpected outcome(s), "
              f"{len(report['unresolved'])} predicted outcome(s) without a verdict")
        print("   " + "property".ljust(16) + "".join(c.ljust(13) for c in columns))
        for prop, cells in report["rows"]:
            by_column = {re.sub(r"(?<=[Ub])\d+$", "", k) if k.startswith("U") else k: v for k, v in cells.items()}
            print("   " + prop.ljust(16) + "".join(by_column.get(c, "-").ljust(13) for c in columns))
        for pair in report["excluded_pairs"]:
            print(f"   EXCLUDED PAIR {pair['property']}: holds on {pair['holds_on']}, trace on {pair['trace_on']}")
        for item in report["unexpected"]:
            print(f"   UNEXPECTED {item['property']} on {item['model']}: {item['outcome']} (expected {item['expected']})")
    total = dict(sets=len(reports), properties=sum(r["properties"] for r in reports),
                 records=sum(r["records"] for r in reports), conclusive=sum(r["conclusive"] for r in reports),
                 both_tools_agree_on_T=sum(r["both_tools_agree_on_T"] for r in reports),
                 both_tools_differ_on_T=sum(r["both_tools_differ_on_T"] for r in reports),
                 excluded_pairs=sum(len(r["excluded_pairs"]) for r in reports),
                 unexpected=sum(len(r["unexpected"]) for r in reports),
                 predicted_without_verdict=sum(len(r["unresolved"]) for r in reports))
    print("== total:", json.dumps(total))
    if args.json:
        for report in reports:
            report["rows"] = [[prop, cells] for prop, cells in report["rows"]]
        with open(args.json, "w") as handle:
            json.dump(dict(total=total, sets=reports), handle, indent=1)
    sys.exit(1 if total["excluded_pairs"] or total["unexpected"] else 0)


if __name__ == "__main__":
    main()
