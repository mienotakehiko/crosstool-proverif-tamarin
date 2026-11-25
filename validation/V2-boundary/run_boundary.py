#!/usr/bin/env python3
"""Run the boundary probes for the side-condition checks of the generator (series V2).

    python3 -B run_boundary.py --cimc CIMC_DIR [--out OUT] [--provers]
                               [--pv-timeout 120] [--tm-timeout 300] [--heap 4g]

The directory probes/ holds twelve small Common Iterative Models. Two controls
stay inside the fragment of the generator, and ten models leave it in one
respect each. The table expected.tsv states for every probe whether the
generator has to accept it.

Step 1 always runs. It compiles every probe with the generator in CIMC_DIR and
compares the outcome with expected.tsv. A probe counts as refused if the
generator ends with a nonzero status, that is, if a side condition fails or
the generator rejects the input. This step writes OUT/boundary_generator.tsv.

Step 2 runs with --provers. It starts ProVerif and Tamarin on every probe
whose model files exist, including refused probes, and counts the excluded
verdict pairs. This step measures what the cross-tool comparison detects
without the checks, and it writes OUT/boundary_pairs.tsv.

The script ends with status 1 if the generator accepts a probe outside the
fragment or refuses a control.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.join(HERE, "..", "common")


def read_expected(path):
    table = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        probe, fragment, outcome, kind, difference = line.rstrip("\n").split("\t")
        table[probe] = dict(fragment=fragment, expected=outcome, kind=kind, difference=difference)
    return table


def compile_probe(cimc_dir, toml, out):
    os.makedirs(out, exist_ok=True)
    done = subprocess.run([sys.executable, "-B", "-m", "cimc", os.path.abspath(toml), os.path.abspath(out)],
                          cwd=cimc_dir, capture_output=True, text=True)
    with open(os.path.join(out, "_gen.log"), "w", encoding="utf-8") as handle:
        handle.write(done.stdout + done.stderr)
    failed = re.findall(r"^(\S+)\s+FAIL\b", done.stdout, re.M)
    if done.returncode == 0:
        return "accept", ""
    if failed:
        return "reject", "FAIL " + ", ".join(failed)
    last = [line for line in done.stderr.strip().splitlines() if line.strip()]
    return "reject", (last[-1] if last else f"exit status {done.returncode}")[:160]


def count_errors(setdir):
    errors = 0
    for name, key in (("pv_results.jsonl", "query"), ("tam_results.jsonl", "lemma")):
        last = {}
        path = os.path.join(setdir, "results", name)
        if os.path.exists(path):
            for line in open(path):
                if line.strip():
                    record = json.loads(line)
                    last[(record["model"], record[key])] = record["verdict"]
        errors += sum(1 for verdict in last.values() if verdict == "ERROR")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cimc", required=True, help="directory that contains the package cimc")
    parser.add_argument("--probes", default=os.path.join(HERE, "probes"))
    parser.add_argument("--expected", default=os.path.join(HERE, "expected.tsv"))
    parser.add_argument("--out", default="boundary_out")
    parser.add_argument("--provers", action="store_true")
    parser.add_argument("--pv-timeout", default="120")
    parser.add_argument("--tm-timeout", default="300")
    parser.add_argument("--heap", default="4g")
    args = parser.parse_args()
    expected = read_expected(args.expected)
    os.makedirs(args.out, exist_ok=True)

    rows, mismatches = [], 0
    for toml in sorted(glob.glob(os.path.join(args.probes, "*.toml"))):
        probe = os.path.basename(toml)[:-5]
        outcome, reason = compile_probe(args.cimc, toml, os.path.join(args.out, probe))
        want = expected[probe]["expected"]
        match = outcome == want
        mismatches += not match
        rows.append((probe, expected[probe]["fragment"], want, outcome, reason, "ok" if match else "MISMATCH"))
    with open(os.path.join(args.out, "boundary_generator.tsv"), "w", encoding="utf-8") as handle:
        handle.write("probe\tfragment\texpected\tgenerator\treason\tresult\n")
        handle.writelines("\t".join(row) + "\n" for row in rows)
    for row in rows:
        print(f"{row[0]:26s} {row[1]:8s} expected {row[2]:7s} generator {row[3]:7s} {row[5]:9s} {row[4]}")
    outside = [row for row in rows if row[1] == "outside"]
    refused = sum(1 for row in outside if row[3] == "reject")
    print(f"== generator: {refused} of {len(outside)} probes outside the fragment refused; "
          f"{sum(1 for row in rows if row[1] == 'inside' and row[3] == 'accept')} of "
          f"{sum(1 for row in rows if row[1] == 'inside')} controls accepted; {mismatches} mismatch(es)")

    if args.provers:
        sets = []
        for probe, *_ in rows:
            setdir = os.path.join(args.out, probe)
            if glob.glob(os.path.join(setdir, "*.spthy")) or glob.glob(os.path.join(setdir, "*.pv")):
                subprocess.run([sys.executable, "-B", os.path.join(COMMON, "run_set.py"), setdir,
                                "--pv-timeout", args.pv_timeout, "--tm-timeout", args.tm_timeout,
                                "--heap", args.heap], check=False)
                sets.append(setdir)
        report = os.path.join(args.out, "boundary_xcheck.json")
        with open(os.path.join(args.out, "boundary_xcheck.txt"), "w", encoding="utf-8") as handle:
            subprocess.run([sys.executable, "-B", os.path.join(COMMON, "xcheck.py"), *sets, "--json", report],
                           stdout=handle, check=False)
        by_set = {entry["set"]: entry for entry in json.load(open(report))["sets"]}
        lines = ["probe\tfragment\tgenerator\trecords\tconclusive\texcluded_pairs\ttool_errors\tcross_check"]
        pair_probes = error_probes = silent = 0
        for probe, fragment, _, outcome, _, _ in rows:
            entry = by_set.get(probe)
            if entry is None:
                lines.append(f"{probe}\t{fragment}\t{outcome}\t0\t0\t0\t0\tno model files")
                continue
            pairs, errors = len(entry["excluded_pairs"]), count_errors(os.path.join(args.out, probe))
            verdict = "excluded pair" if pairs else ("tool error" if errors else "no difference")
            if fragment == "outside":
                pair_probes += bool(pairs)
                error_probes += bool(errors and not pairs)
                silent += not (pairs or errors)
            lines.append(f"{probe}\t{fragment}\t{outcome}\t{entry['records']}\t{entry['conclusive']}\t{pairs}\t{errors}\t{verdict}")
        with open(os.path.join(args.out, "boundary_pairs.tsv"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        print(f"== cross-check without the side conditions: {pair_probes} of {len(outside)} probes outside the fragment "
              f"yield an excluded pair, {error_probes} a tool error only, {silent} no visible difference")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
