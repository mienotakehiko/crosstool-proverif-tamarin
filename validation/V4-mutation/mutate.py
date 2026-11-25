#!/usr/bin/env python3
"""Inject one-sided faults into generated model sets (series V4).

    python3 -B mutate.py --cimc DIR CIM.toml OUTROOT [--ops all] [--sides pv,tam]
    python3 -B mutate.py --list

DIR is the directory that contains the package cimc, for example cimc/v0.1.2.
For every operator and side the script writes OUTROOT/<name>__<op>__<side>/
with the eight model files. The files of one tool come from a mutated copy of
the expanded model, and the files of the other tool come from the unchanged
model. OUTROOT/<name>__control/ holds the unchanged set. Each directory
contains mutation.json with the operator, its class, the side and the SHA-256
hashes of all files, a copy of the input (cim.toml) and the side-condition
report of the unchanged model, because the fault enters after the checks of
the generator.

--ops all       the seven encoding operators below (default)
--ops property  the property operator, which changes the text of a property
                for one tool only and serves series V3

The operators are disjoint from the ten operators of the first mutation
study of the paper (event arguments, input replication, disabled
signing or acceptance, stored identity, leak and signature flags).

  state_stall      the first step leaves the state unchanged
  state_skip       the first step advances the state by two updates
  check_shorten    the verifier applies one chain step fewer
  output_shift     a step outputs a chain value one position earlier
  domain_drop      the last case of the step is missing
  swap_components  two chain values of an output change places
  verifier_gap     the last case of the verifier is missing

The property operator has the class "property".

  spec_drop_disjunct  every correspondence loses its last alternative
"""
import argparse
import copy
import hashlib
import json
import os
import shutil
import sys


def is_chain(term):
    return term[0] == "fun" and len(term[2]) >= 1


def strip_first_link(term):
    """Remove one application from the first iterated application f(.., f(.., u))
    in pre-order, which shortens one chain by one step. Returns (term, changed?)."""
    if term[0] == "fun" and term[2] and term[2][-1][0] == "fun" and term[2][-1][1] == term[1]:
        return term[2][-1], True
    if term[0] == "pair":
        left, changed = strip_first_link(term[1])
        if changed:
            return ("pair", left, term[2]), True
        right, changed = strip_first_link(term[2])
        return ("pair", term[1], right), changed
    if term[0] == "fun":
        args = list(term[2])
        for index, arg in enumerate(args):
            new, changed = strip_first_link(arg)
            if changed:
                args[index] = new
                return ("fun", term[1], args), True
    return term, False


def swap_first_chain_pair(term):
    """Swap the first two adjacent tuple components that are both applications."""
    if term[0] != "pair":
        return term, False
    head, rest = term[1], term[2]
    if is_chain(head) and rest[0] == "pair" and is_chain(rest[1]) and head != rest[1]:
        return ("pair", rest[1], ("pair", head, rest[2])), True
    if is_chain(head) and is_chain(rest) and head != rest:
        return ("pair", rest, head), True
    new_rest, changed = swap_first_chain_pair(rest)
    return ("pair", head, new_rest), changed


def op_state_stall(model):
    for case in model.thread_cases:
        if case.state_in == model.init:
            case.state_out = case.state_in
            return True
    return False


def op_state_skip(model):
    successors = {}
    for case in model.thread_cases:
        successors.setdefault(case.state_in, case.state_out)
    for case in model.thread_cases:
        if case.state_in == model.init:
            after = successors.get(case.state_out)
            if after is not None and after != case.state_out:
                case.state_out = after
                return True
    return False


def op_check_shorten(model):
    changed = False
    for case in model.resp_cases:
        checks = []
        for name, term in case.checks:
            new, did = strip_first_link(term)
            checks.append((name, new))
            changed = changed or did
        case.checks = checks
    return changed


def op_output_shift(model):
    changed = False
    for case in model.thread_cases:
        if case.outputs:
            new, did = strip_first_link(case.outputs[0])
            case.outputs[0] = new
            changed = changed or did
    return changed


def op_domain_drop(model):
    if len(model.thread_cases) < 2:
        return False
    model.thread_cases.pop()
    return True


def op_swap_components(model):
    changed = False
    for case in model.thread_cases:
        if case.outputs:
            new, did = swap_first_chain_pair(case.outputs[0])
            case.outputs[0] = new
            changed = changed or did
    return changed


def op_verifier_gap(model):
    if len(model.resp_cases) < 2:
        return False
    model.resp_cases.pop()
    return True


def op_spec_drop_disjunct(model):
    changed = False
    for prop in model.properties:
        if prop["kind"] == "phi1" and len(prop["conclusion"]) >= 2:
            prop["conclusion"] = prop["conclusion"][:-1]
            changed = True
    return changed


OPERATORS = {
    "state_stall": op_state_stall, "state_skip": op_state_skip, "check_shorten": op_check_shorten,
    "output_shift": op_output_shift, "domain_drop": op_domain_drop,
    "swap_components": op_swap_components, "verifier_gap": op_verifier_gap,
}
PROPERTY_OPERATORS = {"spec_drop_disjunct": op_spec_drop_disjunct}


def render(cimc, model, source, depth):
    version = getattr(cimc, "__version__", "unknown")
    from cimc.backends import proverif, tamarin
    files = {}
    for variant in ("base", "cl1", "rb1", "omega"):
        files[f"{model.name}_T_{variant}.spthy"] = tamarin(model, variant, version, source)
    files[f"{model.name}_PV_U{depth}.pv"] = proverif(model, "U", depth, version, source)
    files[f"{model.name}_PV_Urb{depth}.pv"] = proverif(model, "Urb", depth, version, source)
    files[f"{model.name}_PV_lin.pv"] = proverif(model, "lin", depth, version, source)
    files[f"{model.name}_PV_rep.pv"] = proverif(model, "rep", depth, version, source)
    return files


def write_set(directory, files, report, meta, cim_path):
    os.makedirs(directory, exist_ok=True)
    shutil.copyfile(cim_path, os.path.join(directory, "cim.toml"))
    hashes = {}
    for name, text in files.items():
        with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
            handle.write(text)
        hashes[name] = hashlib.sha256(text.encode()).hexdigest()
    with open(os.path.join(directory, report[0]), "w", encoding="utf-8") as handle:
        handle.write(report[1])
    meta = dict(meta, sha256=hashes)
    with open(os.path.join(directory, "mutation.json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cim", nargs="?")
    parser.add_argument("outroot", nargs="?")
    parser.add_argument("--cimc", help="directory that contains the package cimc")
    parser.add_argument("--ops", default="all")
    parser.add_argument("--sides", default="pv,tam")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        print("\n".join(list(OPERATORS) + list(PROPERTY_OPERATORS)))
        return 0
    if not (args.cim and args.outroot and args.cimc):
        parser.error("CIM, OUTROOT and --cimc are required")
    sys.path.insert(0, os.path.abspath(args.cimc))
    import cimc
    from cimc import checks
    from cimc.core import Model
    original = Model(args.cim)
    depth = original.bound or 2
    source = os.path.basename(args.cim)
    lines = [f"# side conditions for {original.name} (unchanged model; the fault enters after the checks)"]
    lines += [f"{k:10s} {s:16s} {d}" for k, s, d in checks.run(original)]
    report = (f"{original.name}_checks.txt", "\n".join(lines) + "\n")
    clean = render(cimc, original, source, depth)
    cim_hash = hashlib.sha256(open(args.cim, "rb").read()).hexdigest()
    write_set(os.path.join(args.outroot, f"{original.name}__control"), clean, report,
              dict(cim=source, cim_sha256=cim_hash, operator=None, side=None, changed_files=[]), args.cim)
    every = dict(OPERATORS, **PROPERTY_OPERATORS)
    names = {"all": list(OPERATORS), "property": list(PROPERTY_OPERATORS)}.get(args.ops) or args.ops.split(",")
    written = skipped = 0
    for name in names:
        mutant = copy.deepcopy(original)
        kind = "property" if name in PROPERTY_OPERATORS else "encoding"
        if not every[name](mutant):
            print(f"{original.name}: operator {name} does not apply")
            skipped += 1
            continue
        mutated = render(cimc, mutant, source, depth)
        for side in args.sides.split(","):
            suffix = ".pv" if side == "pv" else ".spthy"
            files = {f: (mutated[f] if f.endswith(suffix) else clean[f]) for f in clean}
            changed = sorted(f for f in files if files[f] != clean[f])
            if not changed:
                print(f"{original.name}: operator {name} changes no {side} file")
                skipped += 1
                continue
            write_set(os.path.join(args.outroot, f"{original.name}__{name}__{side}"), files, report,
                      dict(cim=source, cim_sha256=cim_hash, operator=name, side=side, changed_files=changed,
                           **{"class": kind}), args.cim)
            written += 1
    print(f"{original.name}: control and {written} mutant set(s) written, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
