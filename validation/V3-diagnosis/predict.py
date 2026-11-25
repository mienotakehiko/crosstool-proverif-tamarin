#!/usr/bin/env python3
"""Collect the causes that the decision tree assigns (series V3, step 2).

    python3 -B predict.py --cimc CIMC_DIR --labels labels.tsv --out predictions.tsv SETROOT [SETROOT ...]

For every set directory below a SETROOT (with cim.toml, *_checks.txt and the
results/ directory of run_set.py), the script calls the program al_assign of
the generator in CIMC_DIR and reads the findings of its report
results/al.json. It writes one prediction per labeled item.

  <set>|<property>|<model>   the cause of the finding for this model
  <set>|<property>|*         the cause of the finding that names several models
                             (SPEC-expr before ENC-map before ENC-clone)
  none                       the tree reports no finding for the item

The script also records the version and the hash of the decision tree.
Run it only after the publication of the hash of labels.tsv.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import xcheck  # noqa: E402

GROUP = ("SPEC-expr", "ENC-map", "ENC-clone")


def short(model):
    return re.sub(r"(?<=U)\d+$|(?<=Urb)\d+$", "", xcheck.placement(model)[3])


def findings(cimc_dir, setdir):
    cim = os.path.join(setdir, "cim.toml")
    checks = glob.glob(os.path.join(setdir, "*_checks.txt"))
    results = os.path.join(setdir, "results")
    if not (os.path.exists(cim) and checks and os.path.isdir(results)):
        return None, None
    command = [sys.executable, "-B", "-m", "cimc.al_assign", os.path.abspath(cim), os.path.abspath(checks[0]),
               "-o", os.path.abspath(os.path.join(results, "al"))]
    for flag, name in (("--pv", "pv_results.jsonl"), ("--tm", "tam_results.jsonl")):
        path = os.path.join(results, name)
        if os.path.exists(path):
            command += [flag, os.path.abspath(path)]
    done = subprocess.run(command, cwd=cimc_dir, capture_output=True, text=True)
    if done.returncode != 0:
        print(f"al_assign failed for {setdir}: {done.stderr.strip().splitlines()[-1:]}", file=sys.stderr)
        return None, None
    report = json.load(open(os.path.join(results, "al.json")))
    table = {}
    name = os.path.basename(os.path.normpath(setdir))
    for prop, entry in report["properties"].items():
        for finding in entry.get("findings", []):
            cause = finding["cause"]
            if cause in GROUP:
                key = f"{name}|{prop}|*"
                if key not in table or GROUP.index(cause) < GROUP.index(table[key]):
                    table[key] = cause
            else:
                for model in finding.get("records", []):
                    table[f"{name}|{prop}|{short(model)}"] = cause
    tree = (report.get("diagnosis_tree"), report.get("diagnosis_sha256"))
    return table, tree


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("setroots", nargs="+")
    parser.add_argument("--cimc", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    items = [line.split("\t")[0] for line in open(args.labels, encoding="utf-8").read().splitlines()[1:] if line.strip()]
    wanted = {item.split("|")[0] for item in items}
    table, trees = {}, set()
    for root in args.setroots:
        for name in sorted(os.listdir(root)):
            if name in wanted:
                found, tree = findings(args.cimc, os.path.join(root, name))
                if found is not None:
                    table.update(found)
                    trees.add(tree)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write("item\tcause\n")
        for item in items:
            handle.write(f"{item}\t{table.get(item, 'none')}\n")
    print(f"{len(items)} predictions written to {args.out}; decision tree: "
          + "; ".join(f"version {v}, sha256 {h}" for v, h in sorted(trees, key=str)))


if __name__ == "__main__":
    main()
