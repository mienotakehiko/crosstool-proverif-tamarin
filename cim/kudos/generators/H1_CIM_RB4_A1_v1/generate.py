"""Render the bounded RB4 request/response flow in both tools."""

import argparse
import json
import re
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value) is None:
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def term(value, scope, constructor):
    if isinstance(value, str):
        return scope[value]
    name, *args = value
    if (name, len(args)) != constructor:
        raise ValueError(f"Unexpected constructor: {value!r}")
    return f"{name}({','.join(term(arg, scope, constructor) for arg in args)})"


def atom(row, scope, constructor):
    name, *args = row
    return f"{identifier(name)}({','.join(term(arg, scope, constructor) for arg in args)})"


def signatures(rows):
    result = {}
    for name, *args in rows:
        if result.setdefault(identifier(name), len(args)) != len(args):
            raise ValueError(f"Inconsistent arity for {name}")
    return result


def pv_process(spec, states, events, constructor):
    constants = {identifier(name): name for name in spec["constants"]}
    function, arity = constructor
    lines = [
        "(* Bounded RB4: KUDOS draft 14, Appendix A.1, through response #1. *)",
        f"free {', '.join('ch_' + name for name in states)}: channel [private].",
        f"free {', '.join(constants)}: bitstring.",
        f"fun {function}({', '.join(['bitstring'] * arity)}): bitstring.",
        "",
        *(f"event {name}({', '.join(['bitstring'] * count)})." for name, count in events.items()),
        "",
    ]
    observed, before = spec["observe"], spec["before"]
    for index in range(1, 4):
        scope = {name: f"q{index}_{identifier(name)}" for name in observed[1:]} | constants
        binders = ", ".join(f"{scope[name]}:bitstring" for name in observed[1:])
        target = atom(observed, scope, constructor)
        if index == 1:
            statement = f"event({target})"
        elif index == 2:
            prior = " && ".join(f"event({atom(row, scope, constructor)})" for row in before)
            statement = f"event({target}) ==> {prior}"
        else:
            statement = f"inj-event({target}) ==> inj-event({atom(before[0], scope, constructor)})"
        lines += [f"query {binders};", f"  {statement}.", ""]

    def output(row, scope):
        name, *args = row
        payload = ','.join(term(arg, scope, constructor) for arg in args)
        return f"out(ch_{name},({payload}));"

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
        body = [f"event {atom(step['emit'], scope, constructor)};"]
        body += [output(row, scope) for row in step["produce"]] + ["0"]
        if "require_equal" in step:
            left, right = (term(value, scope, constructor) for value in step["require_equal"])
            prefix.append(f"if {left} = {right} then")
            body = ["  (" + body[0], *("   " + item for item in body[1:])]
            body[-1] += ")"
        branches.append(prefix + body)
    lines += ["  (", "\n    |\n".join("    (" + "\n     ".join(branch) + ")" for branch in branches), "  )", ""]
    return "\n".join(lines)


def tm_theory(spec, constructor):
    constants = {identifier(name): f"'{name}'" for name in spec["constants"]}
    function, arity = constructor
    lines = [
        "// Bounded RB4: KUDOS draft 14, Appendix A.1, through response #1.",
        f"theory {identifier(spec['theory'])}", "begin", "",
        f"functions: {function}/{arity}", "",
    ]
    for step in [{"id": "Init", **spec["init"]}, *spec["steps"]]:
        consume, fresh = step.get("consume", []), step.get("fresh", [])
        scope = {arg: identifier(arg) for _, *args in consume for arg in args}
        scope |= {arg: f"~{identifier(arg)}" for arg in fresh} | constants
        premises = [f"Fr({scope[arg]})" for arg in fresh] + [atom(row, scope, constructor) for row in consume]
        actions = [atom(step["emit"], scope, constructor)] if "emit" in step else ["Init()"]
        if "require_equal" in step:
            left, right = (term(value, scope, constructor) for value in step["require_equal"])
            actions.append(f"ContextMatch({left},{right})")
        conclusions = [atom(row, scope, constructor) for row in step["produce"]]
        lines += [
            f"rule {identifier(step['id'])}:", f"  [ {', '.join(premises)} ]",
            f"  --[ {', '.join(actions)} ]->", f"  [ {', '.join(conclusions)} ]", "",
        ]

    observed, before = spec["observe"], spec["before"]
    args = observed[1:]
    scope = {name: identifier(name) for name in args} | constants
    variables = " ".join(args)
    commit = atom(observed, scope, constructor)
    times = [f"t{number}" for number, _ in enumerate(before, 1)]
    prior = [f"{atom(row, scope, constructor)}@{time}" for row, time in zip(before, times)]
    order = [f"#{left} < #{right}" for left, right in zip(times, times[1:] + ["k"])]
    binders = " ".join(f"#{time}" for time in times)
    other = {name: f"{name}_other" for name in args if name not in before[0][1:]}
    other_commit = atom(observed, scope | other, constructor)
    lines += [
        "restriction SingleInit:",
        '  "All #i #j. Init()@i & Init()@j ==> #i = #j"', "",
        "restriction EqualContext:",
        '  "All a b #i. ContextMatch(a,b)@i ==> a = b"', "",
        "lemma rb4_commit_reachable: exists-trace",
        f'  "Ex {variables} #k. {commit}@k"', "",
        "lemma rb4_request_response_binding:",
        f'  "All {variables} #k. {commit}@k ==>',
        f'    Ex {binders}. {" & ".join(prior + order)}"', "",
        "lemma rb4_unique_commit_per_request:",
        f'  "All {variables} {" ".join(other.values())} #i #j.',
        f'    {commit}@i & {other_commit}@j ==> #i = #j"', "", "end", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("cim.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        constructor = (identifier(spec["function"]), spec["arity"])
        steps = spec["steps"]
        states = signatures(spec["init"]["produce"] + [row for step in steps for key in ("consume", "produce") for row in step[key]])
        events = signatures([step["emit"] for step in steps])
        outputs = {
            "rb4.pv": pv_process(spec, states, events, constructor),
            "rb4.spthy": tm_theory(spec, constructor),
        }
        args.out.mkdir(parents=True, exist_ok=False)
        for name, model in outputs.items():
            (args.out / name).write_text(model, encoding="utf-8", newline="\n")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"Generation failed: {exc}\n")


if __name__ == "__main__":
    main()
