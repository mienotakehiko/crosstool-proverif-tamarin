"""Render the two sequential request/response exchanges in both tools."""

import argparse
import json
import re
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value) is None:
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def atom(row, scope):
    name, *args = row
    return f"{identifier(name)}({','.join(scope[arg] for arg in args)})"


def signatures(rows):
    result = {}
    for name, *args in rows:
        if result.setdefault(identifier(name), len(args)) != len(args):
            raise ValueError(f"Inconsistent arity for {name}")
    return result


def variables(prop, constants):
    return [arg for arg in dict.fromkeys(prop["observe"][1:]) if arg not in constants]


def pv_process(spec, states, events):
    constants = {identifier(name): name for name in spec["constants"]}
    lines = [
        "(* Bounded RB2: two sequential authenticated exchanges. *)",
        f"free {', '.join('ch_' + name for name in states)}: channel [private].",
        f"free {', '.join(constants)}: bitstring.",
        "",
        *(f"event {name}({', '.join(['bitstring'] * count)})." for name, count in events.items()),
        "",
    ]
    for number, prop in enumerate(spec["properties"], 1):
        fields = variables(prop, constants)
        scope = {arg: f"q{number}_{identifier(arg)}" for arg in fields} | constants
        binders = ", ".join(f"{scope[arg]}:bitstring" for arg in fields)
        wrapper = "inj-event" if prop["kind"] == "injective" else "event"
        statement = f"{wrapper}({atom(prop['observe'], scope)})"
        if "before" in prop:
            prior = [f"{wrapper}({atom(row, scope)})" for row in prop["before"]]
            statement += " ==> " + " && ".join(prior)
        lines += [f"query {binders};", f"  {statement}.", ""]

    def output(row, scope):
        name, *args = row
        return f"out(ch_{name},({','.join(scope[arg] for arg in args)}));"

    init = spec["init"]
    scope = {identifier(name): name for name in init["fresh"]} | constants
    lines += ["process", *(f"  new {name}:bitstring;" for name in init["fresh"])]
    branches = [[output(row, scope), "0"] for row in init["produce"]]
    for number, step in enumerate(spec["steps"], 1):
        suffix = f"_step{number}"
        scope, prefix = constants.copy(), []
        for name, *args in step["consume"]:
            pattern = []
            for arg in args:
                if arg in scope:
                    pattern.append(f"={scope[arg]}")
                else:
                    scope[arg] = identifier(arg) + suffix
                    pattern.append(f"{scope[arg]}:bitstring")
            prefix.append(f"in(ch_{name},({','.join(pattern)}));")
        for name in step.get("fresh", []):
            if name in scope:
                raise ValueError(f"Fresh identifier already bound: {name}")
            scope[name] = identifier(name) + suffix
            prefix.append(f"new {scope[name]}:bitstring;")
        body = [f"event {atom(row, scope)};" for row in step.get("emit", [])]
        body += [output(row, scope) for row in step["produce"]] + ["0"]
        branches.append(prefix + body)
    lines += ["  (", "\n    |\n".join("    (" + "\n     ".join(b) + ")" for b in branches), "  )", ""]
    return "\n".join(lines)


def tm_theory(spec):
    constants = {identifier(name): f"'{name}'" for name in spec["constants"]}
    lines = [
        "// Bounded RB2: two sequential authenticated exchanges.",
        f"theory {identifier(spec['theory'])}", "begin", "",
    ]
    for step in [{"id": "Init", **spec["init"]}, *spec["steps"]]:
        consume, fresh = step.get("consume", []), step.get("fresh", [])
        scope = {arg: identifier(arg) for _, *args in consume for arg in args}
        scope |= {arg: f"~{identifier(arg)}" for arg in fresh} | constants
        premises = [f"Fr({scope[arg]})" for arg in fresh] + [atom(row, scope) for row in consume]
        actions = [atom(row, scope) for row in step.get("emit", [])]
        if step["id"] == "Init":
            actions.append("Init()")
        conclusions = [atom(row, scope) for row in step["produce"]]
        lines += [
            f"rule {identifier(step['id'])}:", f"  [ {', '.join(premises)} ]",
            f"  --[ {', '.join(actions)} ]->", f"  [ {', '.join(conclusions)} ]", "",
        ]
    lines += [
        "restriction SingleInit:",
        '  "All #i #j. Init()@i & Init()@j ==> #i = #j"', "",
    ]
    for prop in spec["properties"]:
        fields = variables(prop, constants)
        scope = {arg: identifier(arg) for arg in fields} | constants
        binders = " ".join(fields)
        observed = atom(prop["observe"], scope) + "@k"
        lemma = f"lemma rb2_{identifier(prop['id'])}:"
        kind = prop["kind"]
        if kind == "exists":
            statement = f"Ex {binders} #k. {observed}"
            lines += [lemma + " exists-trace", f'  "{statement}"', ""]
        elif kind == "injective":
            independent = {arg: f"{arg}_other" for arg in fields if arg not in prop["unique"]}
            duplicate = atom(prop["observe"], scope | independent) + "@j"
            all_fields = " ".join(fields + list(independent.values()))
            lines += [lemma, f'  "All {all_fields} #k #j. {observed} & {duplicate} ==> #k = #j"', ""]
        else:
            times = [f"i{index}" for index in range(1, len(prop["before"]) + 1)]
            prior = [f"{atom(row, scope)}@{time}" for row, time in zip(prop["before"], times)]
            order = [f"#{left} < #{right}" for left, right in zip(times, times[1:] + ["k"])]
            time_fields = " ".join(f"#{time}" for time in times)
            condition = " & ".join(prior + order)
            lines += [lemma, f'  "All {binders} #k. {observed} ==> Ex {time_fields}. {condition}"', ""]
    return "\n".join(lines + ["end", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("cim.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        steps = spec["steps"]
        states = signatures(spec["init"]["produce"] + [row for step in steps for key in ("consume", "produce") for row in step[key]])
        events = signatures([row for step in steps for row in step.get("emit", [])])
        models = {"rb2.pv": pv_process(spec, states, events), "rb2.spthy": tm_theory(spec)}
        args.out.mkdir(parents=True, exist_ok=False)
        for name, model in models.items():
            (args.out / name).write_text(model, encoding="utf-8", newline="\n")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"Generation failed: {exc}\n")


if __name__ == "__main__":
    main()
