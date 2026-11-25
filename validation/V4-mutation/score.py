#!/usr/bin/env python3
"""Score the mutants of series V4.

    python3 -B score.py SETROOT [--out mutants.tsv]

SETROOT holds the directories that mutate.py wrote, each with the results/
directory of run_set.py. For every mutant the script reports two numbers.

  pairs    excluded verdict pairs (xcheck.py) that the control set of the
           same model does not show. The cross-tool comparison exposes such
           a fault without any reference run.
  changed  verdicts that differ from the control set of the same model. The
           chosen properties observe such a fault.

A mutant counts as detected if pairs > 0, as visible but undetected if
changed > 0 and pairs = 0, and as silent otherwise. The control sets must
show no excluded pair, and the script ends with status 1 if one does. The
summary counts the encoding operators. Mutants of the property operator
(series V3) appear in the table only.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import xcheck  # noqa: E402


def outcomes(setdir):
    _, records = xcheck.load(setdir)
    return {(r["model"], r["prop"]): r["outcome"] for r in records}


def pair_set(setdir):
    return {(p["property"], p["holds_on"], p["trace_on"]) for p in xcheck.check_set(setdir, {})["excluded_pairs"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("setroot")
    parser.add_argument("--out")
    args = parser.parse_args()
    names = sorted(d for d in os.listdir(args.setroot) if os.path.isfile(os.path.join(args.setroot, d, "mutation.json")))
    controls, control_pairs, rows, bad_control = {}, {}, [], 0
    for name in names:
        if name.endswith("__control"):
            directory = os.path.join(args.setroot, name)
            controls[name[:-len("__control")]] = outcomes(directory)
            control_pairs[name[:-len("__control")]] = pair_set(directory)
            pairs = len(control_pairs[name[:-len("__control")]])
            bad_control += pairs
            rows.append((name, "-", "-", pairs, 0, len(controls[name[:-len("__control")]]), "control"))
    for name in names:
        if name.endswith("__control"):
            continue
        directory = os.path.join(args.setroot, name)
        meta = json.load(open(os.path.join(directory, "mutation.json")))
        base = controls[name.split("__")[0]]
        got = outcomes(directory)
        changed = sum(1 for key, value in got.items() if key in base and base[key] != value)
        pairs = len(pair_set(directory) - control_pairs[name.split("__")[0]])
        status = "detected" if pairs else ("visible" if changed else "silent")
        rows.append((name, meta["operator"], meta["side"], pairs, changed, len(got), status,
                     meta.get("class", "encoding")))
    rows = [row if len(row) == 8 else row + ("-",) for row in rows]
    header = "mutant\toperator\tside\tpairs\tchanged\trecords\tstatus\tclass"
    text = header + "\n" + "\n".join("\t".join(str(x) for x in row) for row in rows) + "\n"
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text)
    print(text, end="")
    mutants = [r for r in rows if r[6] != "control" and r[7] == "encoding"]
    count = lambda status: sum(1 for r in mutants if r[6] == status)
    print(f"# mutants {len(mutants)}: detected {count('detected')}, visible but undetected {count('visible')}, "
          f"silent {count('silent')}; excluded pairs in controls {bad_control}")
    return 1 if bad_control else 0


if __name__ == "__main__":
    sys.exit(main())
