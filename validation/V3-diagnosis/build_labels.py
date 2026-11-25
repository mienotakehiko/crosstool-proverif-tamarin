#!/usr/bin/env python3
"""Label diagnosis items by construction (series V3, step 1).

    python3 -B build_labels.py --out labels.tsv
        [--e1 SETROOT --expected EXPECTED.tsv]   sets of series V1
        [--e4 SETROOT]                           mutant sets of series V4
        [--resource SETROOT=LABEL ...]           runs under a limit chosen on purpose

A label states the cause that the construction of an item fixes. The script
reads the verdict records to see which items exist and never reads the output
of the decision tree. It applies the following rules.

  ENC-map    a mutant of an encoding operator whose verdicts on one property
             differ from the control set (the seeded fault is the cause)
  SPEC-expr  the same for a mutant of the property operator
  ENC-clone  a property of an unchanged set that holds on the standard system
             and fails with a reused state value according to the predictions
             of the plan, if the verdicts show both outcomes
  PV-abs     ProVerif answers "cannot be proved" where the predictions say
             that the property holds on that model
  PV-rec     ProVerif answers "cannot be proved" where the predictions say
             that the property fails on that model
  PV-term    ProVerif reaches its time limit
  TM-res, TM-search
             Tamarin ends without a verdict in a run whose limit serves
             exactly this purpose (--resource SETROOT=TM-res for a small
             heap, --resource SETROOT=TM-search for a short time limit on
             jobs that finish with flat memory under a longer one)

An item identifier has the form <set>|<property>|* for a disagreement between
models and <set>|<property>|<model> for a missing verdict, with the short
model names U, Urb, lin, rep, base, cl1, rb1 and omega.

Publish the SHA-256 hash of labels.tsv before predict.py runs.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import xcheck  # noqa: E402

STATE_REUSE = ("Urb", "rep", "rb", "cl", "omega")


def short(model):
    return re.sub(r"(?<=U)\d+$|(?<=Urb)\d+$", "", xcheck.placement(model)[3])


def set_dirs(root):
    return sorted(os.path.join(root, d) for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d, "results")))


def cells(setdir):
    """Map (property, short model) to (outcome H, W or N, raw verdict)."""
    _, records = xcheck.load(setdir)
    return {(r["prop"], short(r["model"])): (r["outcome"], r["raw"]) for r in records}


def expected_key(model):
    return {"cl1": "cl", "rb1": "rb"}.get(model, model)


def label_e1(root, expected, rows):
    for setdir in set_dirs(root):
        name = os.path.basename(setdir)
        table = cells(setdir)
        by_prop = collections.defaultdict(dict)
        for (prop, model), value in table.items():
            by_prop[prop][model] = value
        for prop, models in sorted(by_prop.items()):
            base = expected.get((name.lower(), prop, "base"), set())
            reuse = any(expected.get((name.lower(), prop, m)) == {"W"} for m in STATE_REUSE)
            holds = any(models.get(m, ("N",))[0] == "H" for m in ("U", "lin", "base"))
            fails = any(models.get(m, ("N",))[0] == "W" for m in ("Urb", "rep", "rb1", "cl1", "omega"))
            if base == {"H"} and reuse and holds and fails:
                rows.append((f"{name}|{prop}|*", "ENC-clone", "E1: predicted to fail with a reused state value only"))
            for model, (outcome, raw) in sorted(models.items()):
                allowed = expected.get((name.lower(), prop, expected_key(model)), set())
                if raw == "cannot" and allowed:
                    if "H" in allowed and "W" not in allowed:
                        rows.append((f"{name}|{prop}|{model}", "PV-abs", "E1: predicted to hold on this model"))
                    elif "W" in allowed and "H" not in allowed:
                        rows.append((f"{name}|{prop}|{model}", "PV-rec", "E1: predicted to fail on this model"))
                elif raw == "TIMEOUT" and model in ("U", "Urb", "lin", "rep"):
                    rows.append((f"{name}|{prop}|{model}", "PV-term", "E1: ProVerif time limit"))


def label_e4(root, rows):
    controls = {}
    for setdir in set_dirs(root):
        name = os.path.basename(setdir)
        if name.endswith("__control"):
            controls[name[:-len("__control")]] = cells(setdir)
    for setdir in set_dirs(root):
        name = os.path.basename(setdir)
        meta_path = os.path.join(setdir, "mutation.json")
        if name.endswith("__control") or not os.path.exists(meta_path):
            continue
        meta = json.load(open(meta_path))
        control = controls.get(name.split("__")[0])
        if control is None:
            continue
        table = cells(setdir)
        label = "SPEC-expr" if meta.get("class") == "property" else "ENC-map"
        changed = collections.defaultdict(list)
        for key, (outcome, _) in table.items():
            before = control.get(key, ("N",))[0]
            if outcome != before and "N" not in (outcome, before):
                changed[key[0]].append(key[1])
        for prop, models in sorted(changed.items()):
            rows.append((f"{name}|{prop}|*", label,
                         f"E4: operator {meta['operator']} on side {meta['side']} changes {', '.join(sorted(models))}"))


def label_resource(root, label, rows):
    for setdir in set_dirs(root):
        name = os.path.basename(setdir)
        for (prop, model), (outcome, raw) in sorted(cells(setdir).items()):
            if outcome != "N":
                continue
            if model in ("base", "cl1", "rb1", "omega") and raw in ("TIMEOUT", "HEAP", "KILLED"):
                rows.append((f"{name}|{prop}|{model}", label, f"resource run: limit chosen to cause {label}"))
            elif model in ("U", "Urb", "lin", "rep") and raw == "TIMEOUT":
                rows.append((f"{name}|{prop}|{model}", "PV-term", "resource run: ProVerif time limit"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--e1")
    parser.add_argument("--expected")
    parser.add_argument("--e4")
    parser.add_argument("--resource", action="append", default=[], metavar="SETROOT=LABEL")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = []
    if args.e1:
        label_e1(args.e1, xcheck.read_expected(args.expected), rows)
    if args.e4:
        label_e4(args.e4, rows)
    for item in args.resource:
        root, label = item.rsplit("=", 1)
        if label not in ("TM-res", "TM-search"):
            parser.error("--resource expects SETROOT=TM-res or SETROOT=TM-search")
        label_resource(root, label, rows)
    seen, unique = set(), []
    for row in rows:
        if row[0] not in seen:
            seen.add(row[0])
            unique.append(row)
    text = "item\tcause\tsource\n" + "".join("\t".join(row) + "\n" for row in unique)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(text)
    counts = collections.Counter(row[1] for row in unique)
    print(f"{len(unique)} labeled items: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"sha256 {hashlib.sha256(text.encode()).hexdigest()}  {args.out}")


if __name__ == "__main__":
    main()
