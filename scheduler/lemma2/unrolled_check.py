#!/usr/bin/env python3
"""Compare the two schedulers of the unrolled scheduler lemma (Appendix B of the paper).

    python3 -B unrolled_check.py --cimc CIMC_DIR [--threads 1] [--length 4] CIM.toml [CIM.toml ...]

For every Common Iterative Model, the script enumerates two transition systems
up to a bound on the number of threads and on the length of the observed word.

  atomic    one step per rule instance (Init, Step, Leak and Respond), with at
            most n state updates per thread
  unrolled  the steps of the process that the generator prints for the
            unrolled ProVerif encoding of depth n, namely allocation, table
            storage, publication, receipt of one message, tests of all cases
            of the current position, event, outputs one by one, leak blocks
            that run once, and responder copies

The attacker is a knowledge set with its deductive closure over a free term
algebra with pairing. The script compares the two sets of observable words.
Repeated reveal events count once, and the comparison renames threads in the
order of their first occurrence. The script starts no prover and decides no
property.

The unrolled system follows the printed process also where a model violates a
side condition. If two cases of one state accept one message, both continue,
exactly as the parallel composition of the process does, and the comparison
then shows words that the atomic system lacks.

Three bounds apply. Variables of an input pattern that no table check
determines take one fixed public value, each case carries at most one event,
and each Leak fires at most twice in the atomic system. The script ends with
status 1 if the sets differ for a model, unless --expect-difference names that
model.
"""
import argparse
import os
import sys

JUNK = ("const", "_no_case_matches")
ANY = ("num", 0)


def inst(term, env):
    kind = term[0]
    if kind == "var":
        return env.get(term[1], term)
    if kind == "fun":
        return ("fun", term[1], [inst(a, env) for a in term[2]])
    if kind == "pair":
        return ("pair", inst(term[1], env), inst(term[2], env))
    return term


def freeze(term):
    if term[0] == "fun":
        return ("fun", term[1], tuple(freeze(a) for a in term[2]))
    if term[0] == "pair":
        return ("pair", freeze(term[1]), freeze(term[2]))
    return tuple(term)


def variables(term, acc):
    if term[0] == "var":
        acc.add(term[1])
    elif term[0] == "fun":
        for a in term[2]:
            variables(a, acc)
    elif term[0] == "pair":
        variables(term[1], acc)
        variables(term[2], acc)
    return acc


def match(pattern, ground, env):
    """Match a pattern against a ground term in one direction and return the extended binding or None."""
    kind = pattern[0]
    if kind == "var":
        if pattern[1] in env:
            return env if freeze(env[pattern[1]]) == freeze(ground) else None
        new = dict(env)
        new[pattern[1]] = ground
        return new
    if kind != ground[0]:
        return None
    if kind == "pair":
        env = match(pattern[1], ground[1], env)
        return None if env is None else match(pattern[2], ground[2], env)
    if kind == "fun":
        if pattern[1] != ground[1] or len(pattern[2]) != len(ground[2]):
            return None
        for a, b in zip(pattern[2], ground[2]):
            env = match(a, b, env)
            if env is None:
                return None
        return env
    return env if freeze(pattern) == freeze(ground) else None


def show(term):
    kind = term[0]
    if kind == "num":
        return str(term[1])
    if kind in ("const", "name"):
        return term[1]
    if kind == "var":
        return "?" + term[1]
    if kind == "fun":
        return f"{term[1]}({','.join(show(a) for a in term[2])})"
    return f"<{show(term[1])},{show(term[2])}>"


class System:
    """Shared parts of the two transition systems for one model."""

    def __init__(self, model, depth):
        self.m = model
        self.n = depth
        self.private = {f for f, (_, private) in model.functions.items() if private}
        self.leak_names = {name for name, _ in model.leak_events}
        for case in model.thread_cases + model.resp_cases:
            if len(case.events) > 1:
                raise SystemExit(f"{model.name}: case {case.label} carries several events; outside this check")

    def names(self, index):
        return {x: ("name", f"{x}#{index}") for x in self.m.fresh}

    def closure(self, knowledge):
        seen, todo = set(), list(knowledge)
        while todo:
            term = todo.pop()
            if term in seen:
                continue
            seen.add(term)
            if term[0] == "pair":
                todo += [term[1], term[2]]
        return seen

    def derivable(self, term, analyzed):
        term = freeze(term)
        if term in analyzed:
            return True
        kind = term[0]
        if kind in ("num", "const"):
            return True
        if kind == "pair":
            return self.derivable(term[1], analyzed) and self.derivable(term[2], analyzed)
        if kind == "fun":
            return term[1] not in self.private and all(self.derivable(a, analyzed) for a in term[2])
        return False

    def ground(self, pattern, env):
        """Bind the variables that nothing determines to one fixed public value."""
        free = variables(inst(pattern, env), set())
        full = dict(env)
        for name in free:
            full[name] = ANY
        return full

    def step_inputs(self, case, env, analyzed):
        """Bindings under which the attacker can supply the input of a step case."""
        if case.inp is None:
            return [dict(env)]
        full = self.ground(case.inp, env)
        return [full] if self.derivable(inst(case.inp, full), analyzed) else []

    def responder_inputs(self, case, table, analyzed):
        """Bindings under which a responder case fires. Table entries fix the checked variables."""
        identity = self.m.fresh[0]
        envs = [{}]
        for name, term in case.checks:
            nxt = []
            for env in envs:
                for entry_name, key, value in table:
                    if entry_name != name:
                        continue
                    start = dict(env)
                    if identity in start and freeze(start[identity]) != key:
                        continue
                    start[identity] = key
                    bound = match(term, value, start)
                    if bound is not None:
                        nxt.append(bound)
            envs = nxt
        out = []
        for env in envs:
            full = self.ground(case.inp, env)
            if self.derivable(inst(case.inp, full), analyzed):
                out.append(full)
        return out

    def event(self, case, env):
        if not case.events:
            return None
        name, args = case.events[0]
        return f"{name}({','.join(show(inst(a, env)) for a in args)})"

    def leak_event(self, index, env):
        name, args = self.m.leak_events[index]
        return f"{name}({','.join(show(inst(a, env)) for a in args)})"

    def entries(self, env):
        key = freeze(env[self.m.fresh[0]])
        return frozenset((name, key, freeze(inst(term, env))) for name, term in self.m.persist_vals)

    def cases_of(self, state):
        return [c for c in self.m.thread_cases if c.state_in == state]

    def observe(self, word):
        """Repeated reveal events count once, and thread names follow their first occurrence."""
        seen, kept = set(), []
        for item in word:
            if item.split("(")[0] in self.leak_names:
                if item in seen:
                    continue
                seen.add(item)
            kept.append(item)
        order, text = {}, " ".join(kept)
        out = []
        position = 0
        while position < len(text):
            if text[position] == "#":
                end = position + 1
                while end < len(text) and text[end].isdigit():
                    end += 1
                index = text[position + 1:end]
                order.setdefault(index, str(len(order) + 1))
                out.append("#" + order[index])
                position = end
            else:
                out.append(text[position])
                position += 1
        return "".join(out)


def explore(start, successors, system, length):
    words, seen, todo = set(), {start}, [start]
    while todo:
        config = todo.pop()
        words.add(system.observe(config[-1]))
        for nxt in successors(config):
            if len(nxt[-1]) <= length and nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return words, len(seen)


def atomic(system, threads, length):
    m, n = system.m, system.n

    def successors(config):
        active, knowledge, table, fired, word = config
        analyzed = system.closure(knowledge)
        if len(active) < threads:
            index = len(active) + 1
            env = system.names(index)
            more = {freeze(inst(m.publish_val, env))} if m.publish_val else set()
            yield (active + ((index, freeze(m.init), 0),), knowledge | frozenset(more), table | system.entries(env),
                   fired, word)
        for position, (index, state, updates) in enumerate(active):
            env = system.names(index)
            if updates < n:
                for case in m.thread_cases:
                    if freeze(case.state_in) != state:
                        continue
                    for bound in system.step_inputs(case, env, analyzed):
                        outputs = frozenset(freeze(inst(o, bound)) for o in case.outputs)
                        event = system.event(case, bound)
                        moved = active[:position] + ((index, freeze(case.state_out), updates + 1),) + active[position + 1:]
                        yield (moved, knowledge | outputs, table, fired, word + ((event,) if event else ()))
            for leak_index, leak in enumerate(m.leaks):
                count = dict(fired).get((index, leak_index), 0)
                if count < 2:
                    again = dict(fired)
                    again[(index, leak_index)] = count + 1
                    secret = freeze(env[leak["output"]])
                    yield (active, knowledge | {secret}, table, frozenset(again.items()),
                           word + (system.leak_event(leak_index, env),))
        for case in m.resp_cases:
            for bound in system.responder_inputs(case, table, analyzed):
                event = system.event(case, bound)
                if event:
                    yield (active, knowledge, table, fired, word + (event,))

    start = ((), frozenset(), frozenset(), frozenset(), ())
    return explore(start, successors, system, length)


def unrolled(system, threads, length):
    m, n = system.m, system.n

    def position(state, depth):
        """A position exists only below the depth n and for a state with cases."""
        return ("pos", state, depth) if depth < n and system.cases_of_frozen(state) else None

    def successors(config):
        procs, knowledge, table, word = config
        analyzed = system.closure(knowledge)
        if len(procs) < threads:
            yield (procs + ((len(procs) + 1, "allocated", (), ()),), knowledge, table, word)
        for at, (index, phase, components, leaks) in enumerate(procs):
            env = system.names(index)

            def put(new_phase, new_components, new_leaks):
                return procs[:at] + ((index, new_phase, tuple(sorted(new_components, key=repr)), new_leaks),) + procs[at + 1:]

            if phase == "allocated":
                yield (put("stored", (), ()), knowledge, table | system.entries(env), word)
                continue
            if phase == "stored":
                more = {freeze(inst(m.publish_val, env))} if m.publish_val else set()
                first = position(freeze(m.init), 0)
                yield (put("published", (first,) if first else (), tuple("wait" for _ in m.leaks)),
                       knowledge | frozenset(more), table, word)
                continue
            for number, component in enumerate(components):
                rest = components[:number] + components[number + 1:]
                if component[0] == "pos":
                    _, state, depth = component
                    cases = system.cases_of_frozen(state)
                    messages = {JUNK}
                    for case in cases:
                        for bound in system.step_inputs(case, env, analyzed):
                            messages.add(freeze(inst(case.inp, bound)) if case.inp is not None else freeze(ANY))
                    for message in messages:
                        started = []
                        for label, case in enumerate(cases):
                            if case.inp is None:
                                started.append(("emit", state, label, (), depth))
                            else:
                                bound = match(inst(case.inp, env), message, {})
                                if bound is not None:
                                    started.append(("emit", state, label, tuple(sorted((k, freeze(v)) for k, v in bound.items())), depth))
                        # The receipt consumes the position, and every matching case continues.
                        yield (put(phase, rest + tuple(started), leaks), knowledge, table, word)
                elif component[0] == "emit":
                    _, state, label, binding, depth = component
                    case = system.cases_of_frozen(state)[label]
                    bound = dict(env)
                    bound.update(dict(binding))
                    event = system.event(case, bound)
                    yield (put(phase, rest + (("deliver", state, label, binding, 0, depth),), leaks), knowledge, table,
                           word + ((event,) if event else ()))
                else:
                    _, state, label, binding, delivered, depth = component
                    case = system.cases_of_frozen(state)[label]
                    bound = dict(env)
                    bound.update(dict(binding))
                    if delivered < len(case.outputs):
                        output = freeze(inst(case.outputs[delivered], bound))
                        yield (put(phase, rest + (("deliver", state, label, binding, delivered + 1, depth),), leaks),
                               knowledge | {output}, table, word)
                    else:
                        following = position(freeze(case.state_out), depth + 1)
                        yield (put(phase, rest + ((following,) if following else ()), leaks), knowledge, table, word)
            for leak_index, status in enumerate(leaks):
                def with_status(value):
                    return leaks[:leak_index] + (value,) + leaks[leak_index + 1:]
                if status == "wait":
                    yield (put(phase, components, with_status("stopped")), knowledge, table, word)
                    if system.derivable(env[m.fresh[0]], analyzed):
                        yield (put(phase, components, with_status("emit")), knowledge, table, word)
                elif status == "emit":
                    yield (put(phase, components, with_status("deliver")), knowledge, table,
                           word + (system.leak_event(leak_index, env),))
                elif status == "deliver":
                    secret = freeze(env[m.leaks[leak_index]["output"]])
                    yield (put(phase, components, with_status("done")), knowledge | {secret}, table, word)
        for case in m.resp_cases:
            for bound in system.responder_inputs(case, table, analyzed):
                event = system.event(case, bound)
                if event:
                    yield (procs, knowledge, table, word + (event,))

    start = ((), frozenset(), frozenset(), ())
    return explore(start, successors, system, length)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cims", nargs="+")
    parser.add_argument("--cimc", required=True, help="directory that contains the package cimc")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--length", type=int, default=4)
    parser.add_argument("--expect-difference", default="", help="comma-separated model names whose sets must differ")
    args = parser.parse_args()
    sys.path.insert(0, os.path.abspath(args.cimc))
    from cimc.core import Model
    expected = {name for name in args.expect_difference.split(",") if name}
    failures = 0
    for path in args.cims:
        model = Model(path)
        system = System(model, model.bound or 2)
        frozen_cases = {}
        for case in model.thread_cases:
            frozen_cases.setdefault(freeze(case.state_in), []).append(case)
        system.cases_of_frozen = lambda state, table=frozen_cases: table.get(state, [])
        left, left_states = atomic(system, args.threads, args.length)
        right, right_states = unrolled(system, args.threads, args.length)
        same = left == right
        wanted = model.name not in expected
        verdict = "equal" if same else "DIFFERENT"
        mark = "ok" if same == wanted else "UNEXPECTED"
        failures += mark != "ok"
        print(f"{mark:10s} {model.name:12s} depth {system.n}: atomic {len(left)} words ({left_states} states), "
              f"unrolled {len(right)} words ({right_states} states): {verdict}")
        if not same:
            for label, words in (("only unrolled", sorted(right - left)), ("only atomic", sorted(left - right))):
                for word in words[:3]:
                    print(f"             {label}: {word or '(empty)'}")
    print(f"== {len(args.cims)} model(s), {failures} unexpected result(s); bounds: {args.threads} thread(s), "
          f"words of at most {args.length} events")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
