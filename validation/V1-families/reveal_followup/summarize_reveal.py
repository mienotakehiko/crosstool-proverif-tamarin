#!/usr/bin/env python3
"""Cross-check and summarize the reveal follow-up of series V1.

    python3 -B validation/V1-families/reveal_followup/summarize_reveal.py [--raw DIR] [--no-write]

The script reads the records under sets/<set>/results/, applies the
cross-check of the validation series with the predictions of
inputs/expected_reveal.tsv and compares the two unchanged properties with the
records of series V1. It writes records/xcheck.txt, records/xcheck.json and
records/summary.txt. With --raw DIR it also writes
records/raw-verdict-lines.tsv from the tool outputs under DIR/<set>/out/, with
the verdict line and the SHA-256 hash of the complete output of every job.
With --no-write it prints the summary and writes no file. The script starts
no prover.

The summary ends with one of three lines.

  CONFIRMED      both tools decide all four properties on the standard system
                 of both members, the property with the reveal alternative
                 holds, the property without it has a trace, and no verdict
                 contradicts a prediction or the inclusion chain
  INCOMPLETE     a verdict that the first line needs is missing
  NOT CONFIRMED  a verdict contradicts a prediction or the inclusion chain

The exit status is 0 for the first line and 1 otherwise.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.normpath(os.path.join(HERE, "..", "..", "common"))
V1_SETS = os.path.normpath(os.path.join(HERE, "..", "sets"))
SETS = ("otp_n2_reveal", "otp_n3_reveal")
PROPERTIES = ("Auth", "Forge", "Auth_noreveal", "Forge_noreveal")
COLUMNS = ("U", "Urb", "lin", "rep", "base", "rb1", "cl1", "omega")
# Outcomes that the conclusion needs on the standard system T: Tamarin on the
# base theory and ProVerif on the unrolled encoding, whose traces are those of T
# because the update bound holds.
NEEDED = {"Auth": "H", "Forge": "H", "Auth_noreveal": "W", "Forge_noreveal": "W"}

sys.path.insert(0, COMMON)
import xcheck  # noqa: E402  (the cross-check of the validation series)


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def column(short):
    """Column of a model in the tables: the unrolled encodings drop their depth."""
    return re.sub(r"\d+$", "", short) if short.startswith("U") else short


def outcomes(setdir):
    """Map (property, column) to (outcome, raw verdict, proof steps) with the last record of each job."""
    table = {}
    _, records = xcheck.load(setdir)
    steps = {}
    path = os.path.join(setdir, "results", "tam_results.jsonl")
    for record in xcheck.last_records(path, "lemma"):
        steps[(record["model"], record["lemma"])] = record.get("steps")
    for record in records:
        short = column(xcheck.placement(record["model"])[3])
        table[(record["prop"], short)] = (record["outcome"], record["raw"],
                                          steps.get((record["model"], record["prop"])))
    return table


def tool_lines(setdir):
    path = os.path.join(setdir, "results", "environment.json")
    if not os.path.exists(path):
        return ["environment record: missing"]
    env = json.load(open(path, encoding="utf-8"))
    tamarin = env.get("tamarin", "")
    maude = re.search(r"Maude version ([\d.]+)", tamarin)
    lines = [
        f"run of {env.get('date_utc')} on {env.get('system')}, {env.get('processors')} processors",
        f"ProVerif: {env.get('proverif', '').split(' | ')[0].split('. ')[0]}",
        f"Tamarin: {tamarin.split(',')[0]}" + (f", Maude {maude.group(1)}" if maude else ""),
        f"limits of the last call: {json.dumps(env.get('limits'))}",
        f"runner hash: {env.get('script_sha256')}",
    ]
    return lines


def raw_lines(raw_root, name, setdir):
    """Rows of raw-verdict-lines.tsv for one set, and the jobs whose record differs from the output."""
    rows, differing = [], []
    out = os.path.join(raw_root, name, "out")
    last_pv = {(r["model"], r["query"]): r["verdict"]
               for r in xcheck.last_records(os.path.join(setdir, "results", "pv_results.jsonl"), "query")}
    last_tm = {(r["model"], r["lemma"]): r["verdict"]
               for r in xcheck.last_records(os.path.join(setdir, "results", "tam_results.jsonl"), "lemma")}
    for path in sorted(p for p in os.listdir(setdir) if p.endswith(".pv")):
        model = path[:-3]
        source = os.path.join(out, model + ".pvout")
        if not os.path.exists(source):
            continue
        names = re.findall(r"^\(\* (\w+) \*\)\nquery", open(os.path.join(setdir, path)).read(), re.M)
        text = open(source, errors="replace").read()
        found = re.findall(r"^(RESULT .* (is true|is false|cannot be proved)\.)$", text, re.M)
        digest = sha256(source)
        for index, (line, result) in enumerate(found):
            prop = names[index] if index < len(names) else f"q{index}"
            verdict = {"is true": "true", "is false": "false", "cannot be proved": "cannot"}[result]
            rows.append((name, "PV", model, prop, verdict, f"results/{name}/out/{model}.pvout", digest, line))
            if last_pv.get((model, prop)) != verdict:
                differing.append(f"{model} {prop}")
    for path in sorted(p for p in os.listdir(setdir) if p.endswith(".spthy")):
        model = path[:-6]
        lemmas = re.findall(r"^lemma ([A-Za-z0-9_]+)", open(os.path.join(setdir, path)).read(), re.M)
        for lemma in lemmas:
            source = os.path.join(out, f"{model}__{lemma}.out")
            if not os.path.exists(source):
                continue
            text = open(source, errors="replace").read()
            match = re.search(rf"^\s*{re.escape(lemma)} \((all-traces|exists-trace)\): (.*)$", text, re.M)
            line = match.group(0).strip() if match else ""
            verdict = ("verified" if match and match.group(2).startswith("verified") else
                       "falsified" if match and match.group(2).startswith("falsified") else "none")
            rows.append((name, "TM", model, lemma, verdict, f"results/{name}/out/{model}__{lemma}.out",
                         sha256(source), line))
            recorded = last_tm.get((model, lemma))
            if (recorded if recorded in ("verified", "falsified") else "none") != verdict:
                differing.append(f"{model} {lemma}")
    return rows, differing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", help="directory with <set>/out/ of the runs, for raw-verdict-lines.tsv")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    setdirs = [os.path.join(HERE, "sets", name) for name in SETS]
    missing = [d for d in setdirs if not os.path.exists(os.path.join(d, "results", "tam_results.jsonl"))
               or not os.path.exists(os.path.join(d, "results", "pv_results.jsonl"))]
    if missing:
        sys.exit("No records yet under " + ", ".join(os.path.relpath(d, HERE) for d in missing)
                 + ". Run run_reveal.sh first.")

    expected_path = os.path.join(HERE, "inputs", "expected_reveal.tsv")
    expected = xcheck.read_expected(expected_path)
    out = ["Reveal follow-up of series V1: one-time password family with and without the reveal alternative",
           "Outcomes: H = no such trace, W = such a trace exists, N = no outcome", ""]
    out += tool_lines(setdirs[0]) + [""]

    total = dict(records=0, conclusive=0, pairs=0, unexpected=0, unresolved=0, agree=0, differ=0)
    needed_missing, needed_wrong = [], []
    v1_equal = v1_compared = steps_equal = steps_compared = 0
    for name, setdir in zip(SETS, setdirs):
        report = xcheck.check_set(setdir, expected)
        table = outcomes(setdir)
        out.append(f"== {name}")
        out.append("   " + "property".ljust(16) + "".join(c.ljust(7) for c in COLUMNS))
        for prop in PROPERTIES:
            out.append("   " + prop.ljust(16)
                       + "".join(table.get((prop, c), ("-",))[0].ljust(7) for c in COLUMNS))
        out.append(f"   records with a verdict: {report['conclusive']} of {report['records']}")
        out.append(f"   excluded pairs: {len(report['excluded_pairs'])}, outcomes against the prediction: "
                   f"{len(report['unexpected'])}, predicted outcomes without a verdict: {len(report['unresolved'])}")
        out.append(f"   properties on which both tools decide and agree on T: {report['both_tools_agree_on_T']} of "
                   f"{report['properties']} (they differ on {report['both_tools_differ_on_T']})")
        for item in report["excluded_pairs"]:
            out.append(f"   EXCLUDED PAIR {item['property']}: holds on {item['holds_on']}, trace on {item['trace_on']}")
        for item in report["unexpected"]:
            out.append(f"   AGAINST THE PREDICTION {item['property']} on {item['model']}: "
                       f"{item['outcome']} (predicted {item['expected']})")
        for item in report["unresolved"]:
            out.append(f"   NO VERDICT {item['property']} on {item['model']} (predicted {item['expected']})")
        total["records"] += report["records"]
        total["conclusive"] += report["conclusive"]
        total["pairs"] += len(report["excluded_pairs"])
        total["unexpected"] += len(report["unexpected"])
        total["unresolved"] += len(report["unresolved"])
        total["agree"] += report["both_tools_agree_on_T"]
        total["differ"] += report["both_tools_differ_on_T"]
        for prop, wanted in NEEDED.items():
            for col in ("base", "U"):
                got = table.get((prop, col), ("N",))[0]
                if got == "N":
                    needed_missing.append(f"{name} {prop} on {col}")
                elif got != wanted:
                    needed_wrong.append(f"{name} {prop} on {col}: {got}")
        # The two unchanged properties against the last records of series V1.
        old = outcomes(os.path.join(V1_SETS, name.replace("_reveal", "")))
        lines = []
        for prop in ("Auth", "Forge"):
            for col in COLUMNS:
                new_cell, old_cell = table.get((prop, col)), old.get((prop, col))
                if not new_cell or not old_cell or "N" in (new_cell[0], old_cell[0]):
                    continue
                v1_compared += 1
                v1_equal += new_cell[0] == old_cell[0]
                if new_cell[0] != old_cell[0]:
                    lines.append(f"   DIFFERENT FROM V1 {prop} on {col}: {new_cell[0]} here, {old_cell[0]} in V1")
                if new_cell[2] is not None and old_cell[2] is not None:
                    steps_compared += 1
                    steps_equal += new_cell[2] == old_cell[2]
                    if new_cell[2] != old_cell[2]:
                        lines.append(f"   other proof size than V1 for {prop} on {col}: "
                                     f"{new_cell[2]} steps here, {old_cell[2]} in V1")
        out += lines + [""]

    out.append("== total")
    out.append(f"   records with a verdict: {total['conclusive']} of {total['records']}")
    out.append(f"   excluded pairs: {total['pairs']}, outcomes against the prediction: {total['unexpected']}, "
               f"predicted outcomes without a verdict: {total['unresolved']}")
    out.append(f"   properties on which both tools decide and agree on T: {total['agree']} "
               f"(they differ on {total['differ']})")
    out.append(f"   unchanged properties Auth and Forge against series V1: {v1_equal} of {v1_compared} "
               f"comparable outcomes equal, {steps_equal} of {steps_compared} Tamarin proofs with the same number of steps")

    raw_rows, raw_differing = [], []
    if args.raw:
        for name, setdir in zip(SETS, setdirs):
            rows, differing = raw_lines(args.raw, name, setdir)
            raw_rows += rows
            raw_differing += differing
        out.append(f"   tool outputs read for raw-verdict-lines.tsv: {len(raw_rows)} verdict lines, "
                   f"{len(raw_differing)} of them differ from the records")
        out += [f"   RECORD DIFFERS FROM OUTPUT {item}" for item in raw_differing]

    if total["pairs"] or total["unexpected"] or total["differ"] or needed_wrong or raw_differing \
            or v1_equal != v1_compared:
        verdict = "NOT CONFIRMED: " + "; ".join(needed_wrong or ["see the lines in capital letters above"])
        status = 1
    elif needed_missing:
        verdict = "INCOMPLETE: no verdict for " + "; ".join(needed_missing)
        status = 1
    else:
        verdict = ("CONFIRMED: on the standard system of both members, both tools prove the authentication "
                   "property with the reveal alternative and find a trace against the property without it")
        status = 0
    out += ["", verdict]
    text = "\n".join(out) + "\n"
    print(text, end="")

    if not args.no_write:
        records = os.path.join(HERE, "records")
        os.makedirs(records, exist_ok=True)
        done = subprocess.run([sys.executable, "-B", os.path.join(COMMON, "xcheck.py"), *setdirs,
                               "--expected", expected_path, "--json", os.path.join(records, "xcheck.json")],
                              capture_output=True, text=True)
        with open(os.path.join(records, "xcheck.txt"), "w", encoding="utf-8") as handle:
            handle.write(done.stdout)
        with open(os.path.join(records, "summary.txt"), "w", encoding="utf-8") as handle:
            handle.write(text)
        if args.raw:
            header = ("set", "tool", "model", "property", "verdict", "source_path_in_work_directory",
                      "source_sha256", "result_line")
            with open(os.path.join(records, "raw-verdict-lines.tsv"), "w", encoding="utf-8") as handle:
                handle.write("\n".join("\t".join(row) for row in [header] + raw_rows) + "\n")
    sys.exit(status)


if __name__ == "__main__":
    main()
