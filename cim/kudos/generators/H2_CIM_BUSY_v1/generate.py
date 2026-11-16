"""Generate one finite BUSY case for ProVerif and Tamarin."""

import argparse
import json
import re
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def term(value, scope, function):
    if isinstance(value, str):
        return scope[value]
    name, *args = value
    if (name, len(args)) != function:
        raise ValueError(f"Unknown constructor: {name}")
    return f"{name}({','.join(term(arg, scope, function) for arg in args)})"


def atom(row, scope, function):
    name, *args = row
    return f"{identifier(name)}({','.join(term(arg, scope, function) for arg in args)})"


def signatures(rows):
    result = {}
    for name, *args in rows:
        if result.setdefault(identifier(name), len(args)) != len(args):
            raise ValueError(f"Inconsistent arity for {name}")
    return result


def pv_payload(fields):
    return fields[0] if len(fields) == 1 else f"({','.join(fields)})"


def pv_process(spec, states, events):
    function = tuple(spec["function"])
    name, arity = function
    chunks = [
        f"(* Generated {identifier(spec['model'])} case. CTX_TEMP usability is a local premise. *)",
        f"free {', '.join('ch_' + name for name in states)}: channel [private].",
        f"fun {name}({', '.join(['bitstring'] * arity)}): bitstring.",
        "",
        *(f"event {name}({', '.join(['bitstring'] * arity)})." for name, arity in events.items()),
        "",
    ]
    observed = spec["observed"]
    for prop in spec["properties"]:
        kind = prop["kind"]
        target = observed
        if kind == "different":
            left, right = prop["fields"]
            target = [right if field == left else field for field in observed]
        variables = dict.fromkeys(target[1:] + prop.get("witness", []))
        scope = {name: identifier(name) for name in variables}
        binders = ", ".join(f"{name}:bitstring" for name in variables)
        statement = f"event({atom(target, scope, function)})"
        if kind == "correspondence":
            conditions = [
                f"event({atom(row, scope, function)})" for row in prop.get("before", [])
            ]
            conditions.extend(
                f"{term(a, scope, function)} = {term(b, scope, function)}"
                for a, b in prop.get("equal", [])
            )
            statement += " ==> " + " && ".join(conditions)
        chunks += [f"query {binders};", f"  {statement}.", ""]

    init = spec["init"]
    init_scope = {name: identifier(name) for name in init["fresh"]}
    chunks.append("process")
    chunks += [f"  new {name}:bitstring;" for name in init["fresh"]]
    chunks += [f"  event {atom(row, init_scope, function)};" for row in init["emit"]]

    def outputs(rows, scope):
        result = []
        for name, *args in rows:
            values = [term(arg, scope, function) for arg in args]
            result.append(f"out(ch_{name},{pv_payload(values)});")
        return result

    branches = [outputs([row], init_scope) + ["0"] for row in init["produce"]]
    for step in spec["steps"]:
        prefix, scope = [], {}
        for name, *args in step["consume"]:
            patterns = []
            for arg in args:
                identifier(arg)
                if arg in scope:
                    patterns.append(f"={arg}")
                else:
                    scope[arg] = arg
                    patterns.append(f"{arg}:bitstring")
            prefix.append(f"in(ch_{name},{pv_payload(patterns)});")
        for name in step.get("fresh", []):
            if name in scope:
                raise ValueError(f"Fresh identifier already bound: {name}")
            scope[name] = identifier(name)
            prefix.append(f"new {name}:bitstring;")
        body = [f"event {atom(row, scope, function)};" for row in step.get("emit", [])]
        body += outputs(step["produce"], scope) + ["0"]
        branches.append(prefix + body)
    chunks += ["  (", "\n    |\n".join("    (" + "\n     ".join(b) + ")" for b in branches), "  )", ""]
    return "\n".join(chunks)


def tm_theory(spec):
    function = tuple(spec["function"])
    constructor, arity = function
    chunks = [
        f"// Generated {identifier(spec['model'])} case. CTX_TEMP usability is a local premise.",
        f"theory {identifier(spec['theory'])}",
        "begin",
        "",
        f"functions: {constructor}/{arity}",
        "",
    ]
    for step in [{"id": "Init", **spec["init"]}, *spec["steps"]]:
        name = identifier(step["id"])
        fresh = step.get("fresh", [])
        consume = step.get("consume", [])
        scope = {arg: identifier(arg) for _, *args in consume for arg in args}
        scope |= {arg: f"~{identifier(arg)}" for arg in fresh}
        prem = [f"Fr({scope[arg]})" for arg in fresh] + [
            atom(row, scope, function) for row in consume
        ]
        actions = [atom(row, scope, function) for row in step.get("emit", [])]
        if name == "Init":
            actions.insert(0, "Init()")
        conclusions = [atom(row, scope, function) for row in step["produce"]]
        chunks += [
            f"rule {name}:",
            f"  [ {', '.join(prem)} ]",
            f"  --[ {', '.join(actions)} ]->",
            f"  [ {', '.join(conclusions)} ]",
            "",
        ]
    chunks += [
        "restriction SingleInit:",
        '  "All #i #j. Init()@i & Init()@j ==> #i = #j"',
        "",
    ]
    observed = spec["observed"]
    variables = " ".join(observed[1:])
    observed_scope = {name: identifier(name) for name in observed[1:]}
    premise = atom(observed, observed_scope, function) + "@k"
    for prop in spec["properties"]:
        lemma = f"lemma {spec['lemma_prefix']}_{identifier(prop['id'])}:"
        kind = prop["kind"]
        if kind == "exists":
            chunks += [lemma + " exists-trace", f'  "Ex {variables} #k. {premise}"', ""]
            continue
        chunks.append(lemma)
        statement = f"All {variables} #k. {premise} ==>"
        if kind == "different":
            a, b = prop["fields"]
            chunks += [f'  "{statement} not({observed_scope[a]} = {observed_scope[b]})"', ""]
            continue
        witness = [identifier(name) for name in prop.get("witness", [])]
        scope = observed_scope | {name: name for name in witness}
        before = prop.get("before", [])
        times = [f"#t{i}" for i, _ in enumerate(before, start=1)]
        conditions = [
            f"{atom(row, scope, function)}@{time[1:]}" for row, time in zip(before, times)
        ]
        conditions += [f"{time} < #k" for time in times]
        conditions.extend(
            f"{term(a, scope, function)} = {term(b, scope, function)}"
            for a, b in prop.get("equal", [])
        )
        result = " & ".join(conditions)
        if witness or times:
            result = f"Ex {' '.join(witness + times)}. {result}"
        chunks += [f'  "{statement}', f'    {result}"', ""]
    return "\n".join(chunks + ["end", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        model = identifier(spec["model"])
        identifier(spec["lemma_prefix"])
        constructor, arity = spec["function"]
        identifier(constructor)
        if arity not in (1, 2):
            raise ValueError(f"Unsupported constructor arity: {arity}")
        init = spec["init"]
        steps = spec["steps"]
        states = signatures(
            init["produce"] + [row for step in steps for mode in ("consume", "produce") for row in step[mode]]
        )
        events = signatures(init["emit"] + [row for step in steps for row in step.get("emit", [])])
        rendered = {
            f"{model}.pv": pv_process(spec, states, events),
            f"{model}.spthy": tm_theory(spec),
        }
        args.out.mkdir(parents=True, exist_ok=False)
        for name, source in rendered.items():
            (args.out / name).write_text(source, encoding="utf-8", newline="\n")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"Generation failed: {exc}\n")


if __name__ == "__main__":
    main()
