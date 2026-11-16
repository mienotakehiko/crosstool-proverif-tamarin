"""Generate the finite RB5 state model in ProVerif and Tamarin."""

import argparse
import json
import re
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
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


def observed_variables(prop, constants):
    return [identifier(arg) for arg in dict.fromkeys(prop["observe"][1:]) if arg not in constants]


def pv_process(spec, states, events):
    constants = {name: name for name in spec["constants"]}
    lines = [
        "(* Generated finite RB5 model. No network inputs. *)",
        f"free {', '.join('ch_' + name for name in states)}: channel [private].",
        f"free {', '.join(constants)}: bitstring.",
        "",
        *(f"event {name}({', '.join(['bitstring'] * arity)})." for name, arity in events.items()),
        "",
    ]
    for prop in spec["properties"]:
        variables = observed_variables(prop, constants)
        scope = {name: name for name in variables} | constants
        binders = ", ".join(f"{name}:bitstring" for name in variables)
        statement = f"event({atom(prop['observe'], scope)})"
        if prop["kind"] == "correspondence":
            statement += " ==> " + " && ".join(f"event({atom(row, scope)})" for row in prop["before"])
        lines += [f"query {binders};", f"  {statement}.", ""]

    init = spec["init"]
    initial = {name: identifier(name) for name in init["fresh"]} | constants
    lines += ["process", *(f"  new {name}:bitstring;" for name in init["fresh"])]
    lines += [f"  event {atom(row, initial)};" for row in init["emit"]]

    def outputs(rows, scope):
        return [f"out(ch_{name},({','.join(scope[arg] for arg in args)}));" for name, *args in rows]

    branches = [outputs([row], initial) + ["0"] for row in init["produce"]]
    for step in spec["steps"]:
        branch, scope = [], constants.copy()
        for name, *args in step["consume"]:
            pattern = []
            for arg in args:
                identifier(arg)
                if arg in scope:
                    pattern.append(f"={scope[arg]}")
                else:
                    # `phase` is reserved in ProVerif process syntax.
                    variable = "current_phase" if arg == "phase" else arg
                    scope[arg] = variable
                    pattern.append(f"{variable}:bitstring")
            branch.append(f"in(ch_{name},({','.join(pattern)}));")
        branch += [f"event {atom(row, scope)};" for row in step.get("emit", [])]
        branches.append(branch + outputs(step["produce"], scope) + ["0"])
    lines += ["  (", "\n    |\n".join("    (" + "\n     ".join(b) + ")" for b in branches), "  )", ""]
    return "\n".join(lines)


def tm_theory(spec):
    constants = {name: f"'{name}'" for name in spec["constants"]}
    lines = [
        "// Generated finite RB5 model. No network inputs.",
        f"theory {identifier(spec['theory'])}",
        "begin",
        "",
    ]
    for step in [{"id": "Init", **spec["init"]}, *spec["steps"]]:
        name = identifier(step["id"])
        fresh, consume = step.get("fresh", []), step.get("consume", [])
        scope = {arg: identifier(arg) for _, *args in consume for arg in args}
        scope |= {arg: f"~{identifier(arg)}" for arg in fresh} | constants
        inputs = [f"Fr({scope[arg]})" for arg in fresh] + [atom(row, scope) for row in consume]
        actions = [atom(row, scope) for row in step.get("emit", [])]
        if name == "Init":
            actions.insert(0, "Init()")
        outputs = [atom(row, scope) for row in step["produce"]]
        lines += [
            f"rule {name}:",
            f"  [ {', '.join(inputs)} ]",
            f"  --[ {', '.join(actions)} ]->",
            f"  [ {', '.join(outputs)} ]",
            "",
        ]
    lines += ["restriction SingleInit:", '  "All #i #j. Init()@i & Init()@j ==> #i = #j"', ""]
    for prop in spec["properties"]:
        variables = observed_variables(prop, constants)
        scope = {name: name for name in variables} | constants
        observed = atom(prop["observe"], scope) + "@k"
        lemma = f"lemma rb5_{identifier(prop['id'])}:"
        binders = " ".join(variables + ["#k"])
        kind = prop["kind"]
        if kind == "exists":
            lines += [lemma + " exists-trace", f'  "Ex {binders}. {observed}"', ""]
        elif kind == "unreachable":
            lines += [lemma, f'  "not (Ex {binders}. {observed})"', ""]
        else:
            start, end = (atom(row, scope) for row in prop["before"])
            lines += [
                lemma,
                f'  "All {binders}. {observed} ==>',
                f'    Ex #i #j. {start}@i & {end}@j & #i < #j & #j < #k"',
                "",
            ]
    return "\n".join(lines + ["end", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("cim.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        for constant in spec["constants"]:
            identifier(constant)
        init, steps = spec["init"], spec["steps"]
        states = signatures(
            init["produce"] + [row for step in steps for mode in ("consume", "produce") for row in step[mode]]
        )
        events = signatures(init["emit"] + [row for step in steps for row in step.get("emit", [])])
        sources = {"rb5.pv": pv_process(spec, states, events), "rb5.spthy": tm_theory(spec)}
        args.out.mkdir(parents=True, exist_ok=False)
        for name, source in sources.items():
            (args.out / name).write_text(source, encoding="utf-8", newline="\n")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"Generation failed: {exc}\n")


if __name__ == "__main__":
    main()
