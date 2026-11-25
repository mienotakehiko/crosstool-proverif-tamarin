#!/usr/bin/env python3
"""Inject faults into the input of the generator (series V4, input side).

    python3 -B mutate_cim.py --cimc CIMC_DIR OUTDIR CIM.toml [CIM.toml ...]

Each operator edits the text of a Common Iterative Model so that the model
leaves the fragment of the generator in one respect. Both back ends would
print the faulty model, so the cross-tool comparison plays no role here. The
question is whether the side-condition checks refuse the input. The script
writes every mutant to OUTDIR/<name>__<operator>.toml, compiles it with the
generator in CIMC_DIR and records the outcome in OUTDIR/cim_mutants.tsv. It
starts no prover.

Each operator applies only where its precondition holds.

  drop_publish     the thread publishes nothing although it has a leak
  literal_numeral  a string literal of an input becomes 'n1', the name that
                   Tamarin gives the numeral 1
  leak_state       the leak outputs a state variable
  unbound_output   an output names a variable that nothing binds
  overlap_input    a pattern variable replaces the digit of the input, so the
                   cases of one state accept the same messages
  drop_input       the step loses its input, so several cases of one state
                   accept every message
  mixed_dispatch   a new step without input shares the initial state with
                   the steps that read an input

The script ends with status 1 if the generator accepts a mutant.
"""
import argparse
import os
import re
import subprocess
import sys
import tomllib


def first_step(spec):
    return spec["thread"]["step"][0]


def free_digit(spec):
    """Does the first step have a domain variable outside the state with two or more values?"""
    state = set(spec["thread"]["state"])
    return any(k not in state and len(v) >= 2 for k, v in first_step(spec).get("domain", {}).items())


def op_drop_publish(text, spec):
    if not spec["thread"].get("leak") or "publish" not in spec["thread"]:
        return None
    return re.sub(r"^publish\s*=.*\n", "", text, count=1, flags=re.M)


def op_literal_numeral(text, spec):
    match = re.search(r"^input\s*=\s*\".*?'([A-Za-z_]\w*)'", text, flags=re.M)
    if not match or re.fullmatch(r"n\d+", match.group(1)):
        return None
    return text.replace(f"'{match.group(1)}'", "'n1'")


def op_leak_state(text, spec):
    if not spec["thread"].get("leak"):
        return None
    variable = spec["thread"]["state"][0]
    return re.sub(r"^output\s*=\s*\"[^\"]*\"", f'output = "{variable}"', text, count=1, flags=re.M)


def op_unbound_output(text, spec):
    if not re.search(r"^outputs\s*=\s*\[\"tup\(", text, flags=re.M):
        return None
    return re.sub(r"^(outputs\s*=\s*\[\"tup\()", r"\1zz, ", text, count=1, flags=re.M)


def op_overlap_input(text, spec):
    step = first_step(spec)
    if "input" not in step or not free_digit(spec):
        return None
    state = set(spec["thread"]["state"])
    digits = [k for k, v in step["domain"].items() if k not in state and len(v) >= 2]
    line = re.search(r"^input\s*=\s*\"(.*)\"\s*$", text, flags=re.M)
    for digit in digits:
        changed = re.sub(rf"\b{re.escape(digit)}\b", "zz", line.group(1))
        if changed != line.group(1):
            return text[:line.start(1)] + changed + text[line.end(1):]
    return None


def op_drop_input(text, spec):
    if "input" not in first_step(spec) or not free_digit(spec):
        return None
    return re.sub(r"^input\s*=.*\n", "", text, count=1, flags=re.M)


def op_mixed_dispatch(text, spec):
    thread = spec["thread"]
    if not any("input" in step for step in thread["step"]):
        return None
    domain = ", ".join(f"{name} = [{thread['init'][name]}]" for name in thread["state"])
    first = thread["state"][0]
    block = (f'\n[[thread.step]]\nname    = "Silent"\ndomain  = {{ {domain} }}\n'
             f'update  = {{ {first} = "{first} + 1" }}\nevents  = ["Silent({thread["fresh"][0]})"]\n')
    marker = re.search(r"^\[\[(responder|property)\]\]", text, flags=re.M)
    position = marker.start() if marker else len(text)
    return text[:position] + block.lstrip("\n") + "\n" + text[position:]


OPERATORS = {
    "drop_publish": op_drop_publish, "literal_numeral": op_literal_numeral, "leak_state": op_leak_state,
    "unbound_output": op_unbound_output, "overlap_input": op_overlap_input, "drop_input": op_drop_input,
    "mixed_dispatch": op_mixed_dispatch,
}


def compile_cim(cimc_dir, toml, out):
    os.makedirs(out, exist_ok=True)
    done = subprocess.run([sys.executable, "-B", "-m", "cimc", os.path.abspath(toml), os.path.abspath(out)],
                          cwd=cimc_dir, capture_output=True, text=True)
    failed = re.findall(r"^(\S+)\s+FAIL\b", done.stdout, re.M)
    if done.returncode == 0:
        return "accept", ""
    if failed:
        return "reject", "FAIL " + ", ".join(failed)
    last = [line for line in done.stderr.strip().splitlines() if line.strip()]
    return "reject", (last[-1] if last else f"exit status {done.returncode}")[:160]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("outdir")
    parser.add_argument("cims", nargs="+")
    parser.add_argument("--cimc", required=True)
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    rows = []
    for path in args.cims:
        text = open(path, encoding="utf-8").read()
        spec = tomllib.loads(text)
        name = os.path.basename(path)[:-5]
        for operator, function in OPERATORS.items():
            mutated = function(text, spec)
            if mutated is None or mutated == text:
                continue
            target = os.path.join(args.outdir, f"{name}__{operator}.toml")
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(mutated)
            outcome, reason = compile_cim(args.cimc, target, os.path.join(args.outdir, "sets", f"{name}__{operator}"))
            rows.append((f"{name}__{operator}", operator, outcome, reason))
    with open(os.path.join(args.outdir, "cim_mutants.tsv"), "w", encoding="utf-8") as handle:
        handle.write("mutant\toperator\tgenerator\treason\n")
        handle.writelines("\t".join(row) + "\n" for row in rows)
    by_operator = {}
    for _, operator, outcome, _ in rows:
        total, refused = by_operator.get(operator, (0, 0))
        by_operator[operator] = (total + 1, refused + (outcome == "reject"))
    for operator, (total, refused) in by_operator.items():
        print(f"{operator:16s} refused {refused} of {total}")
    refused = sum(1 for row in rows if row[2] == "reject")
    print(f"== {refused} of {len(rows)} input mutants refused by the generator")
    return 1 if refused < len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
