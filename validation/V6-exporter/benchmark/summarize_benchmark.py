#!/usr/bin/env python3
"""Summarize the benchmark comparison of the exporter builds B0 and B2 (series V6).

    python3 -B validation/V6-exporter/benchmark/summarize_benchmark.py [--examples DIR] [--facts]

The script reads B0/rows.jsonl and B2/rows.jsonl of this directory and the
published records corpus/morio/eval-results.jsonl of the translation artifact.
It classifies the outcome of every pair of theory and lemma, compares the two
builds with each other, with the published outcome of the translated route and
with the published outcome of native Tamarin, and prints the counts.

With --examples DIR, where DIR holds the directory examples/ of Tamarin at the
pinned commit, the script also checks the hashes of the 121 theories, lists the
theories with an input of a term without variables and names, and counts the
differences with native Tamarin in theories that declare exclusive-or.
With --facts, it prints the counts as lines of key and value.

The script reads recorded outcomes and runs no tool.
"""
import argparse
import collections
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CLASSES = ("true", "false", "oom", "timeout", "pv_error", "unresolved")
NAMES = {"true": "true", "false": "false", "oom": "memory exhausted", "timeout": "time limit",
         "pv_error": "error of ProVerif", "unresolved": "no result"}


def load(path):
    with open(path, encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    table = {(row["input_file"], row["lemma"]): row for row in rows}
    assert len(table) == len(rows), f"duplicate pair in {path}"
    return table


def outcome(row):
    """Class of one row of the translated route, as in provenance/pair_report.py."""
    value = row["proverif_result"]
    if value is True or value is False:
        return "true" if value else "false"
    for flag, name in (("translate_error", "export_error"), ("proverif_timeout", "timeout"), ("proverif_oom", "oom")):
        if row[flag]:
            return name
    if row["proverif_error"]:
        return "pv_error"
    return "unresolved"


def native(row):
    value = row["tamarin_result"]
    return ("true" if value else "false") if value is True or value is False else "unresolved"


def ground_inputs(text):
    """Arguments of In(...) that consist of declared function symbols only."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    functions = {}
    for block in re.finditer(r"functions\s*:(.*?)(?=\n\s*\n|\n[a-z]+\s*:|\nrule|\nequations|\nbuiltins|\nlet |\npredicates"
                             r"|\nrestriction|\nlemma|\nprocess|\nsection|\ntext|\noptions)", text, flags=re.S):
        for name, arity in re.findall(r"([A-Za-z0-9_]+)\s*/\s*(\d+)", block.group(1)):
            functions[name] = int(arity)
    if 0 not in functions.values():
        return []
    found = []
    for match in re.finditer(r"\bIn\(", text):
        depth, end = 1, match.end()
        while end < len(text) and depth:
            depth += (text[end] == "(") - (text[end] == ")")
            end += 1
        argument = text[match.end():end - 1]
        symbols = re.findall(r"[~$']?[A-Za-z0-9_.]+'?", argument)
        if symbols and all(s in functions for s in symbols) and not re.search(r"[<>~$'+*^]", argument):
            found.append(" ".join(argument.split()))
    return sorted(set(found))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--examples")
    parser.add_argument("--facts", action="store_true")
    args = parser.parse_args()

    published = load(os.path.join(REPOSITORY, "corpus", "morio", "eval-results.jsonl"))
    builds = {name: load(os.path.join(HERE, name, "rows.jsonl")) for name in ("B0", "B2")}
    pairs = sorted(published)
    for name, rows in builds.items():
        assert sorted(rows) == pairs, f"{name} covers other pairs than the published records"
        assert all(rows[k]["trace_quantifier"] == published[k]["trace_quantifier"] for k in pairs)
    theories = sorted({k[0] for k in pairs})
    b0 = {k: outcome(builds["B0"][k]) for k in pairs}
    b2 = {k: outcome(builds["B2"][k]) for k in pairs}
    pub = {k: outcome(published[k]) for k in pairs}
    nat = {k: native(published[k]) for k in pairs}
    definite = ("true", "false")
    facts = collections.OrderedDict()
    out = []

    facts["theories"], facts["pairs"] = len(theories), len(pairs)
    quantifiers = collections.Counter(published[k]["trace_quantifier"] for k in pairs)
    out.append(f"theories: {len(theories)}, pairs of theory and lemma: {len(pairs)} "
               f"({quantifiers['all-traces']} all-traces, {quantifiers['exists-trace']} exists-trace)")
    out.append("")
    out.append("class               B0    B2")
    for name in CLASSES:
        n0, n2 = sum(v == name for v in b0.values()), sum(v == name for v in b2.values())
        facts[f"B0.{name}"], facts[f"B2.{name}"] = n0, n2
        out.append(f"{NAMES[name]:18s} {n0:4d}  {n2:4d}")
    assert set(b0.values()) | set(b2.values()) <= set(CLASSES), "a row has an outcome outside the six classes"
    both = [k for k in pairs if b0[k] in definite and b2[k] in definite]
    one = [k for k in pairs if (b0[k] in definite) != (b2[k] in definite)]
    equal = [k for k in both if b0[k] == b2[k]]
    facts["definite_both"], facts["definite_equal"], facts["definite_one_build_only"] = len(both), len(equal), len(one)
    out.append("")
    out.append(f"definitive outcome under both builds: {len(both)}, equal: {len(equal)}, under one build only: {len(one)}")
    others = [k for k in pairs if k not in both]
    same_class = [k for k in others if b0[k] == b2[k]]
    changed = [k for k in pairs if b0[k] != b2[k]]
    facts["other_pairs"], facts["other_same_class"], facts["changed"] = len(others), len(same_class), len(changed)
    facts["changed_theories"] = len({k[0] for k in changed})
    out.append(f"other pairs: {len(others)}, same class under both builds: {len(same_class)}, changed: {len(changed)}")
    for k in changed:
        row = builds["B2"][k]
        out.append(f"  changed: {k[0]} {k[1]} ({NAMES[b0[k]]} -> {NAMES[b2[k]]}: {row['proverif_error']}, "
                   f"{row['proverif_time']} s, published: {NAMES[pub[k]]})")
    facts["changed_decided_in_published_run"] = sum(pub[k] in definite for k in changed)
    out.append("")
    for name, table in (("B0", b0), ("B2", b2)):
        common = [k for k in pairs if table[k] in definite and pub[k] in definite]
        agree = [k for k in common if table[k] == pub[k]]
        only_published = [k for k in pairs if table[k] not in definite and pub[k] in definite]
        only_local = [k for k in pairs if table[k] in definite and pub[k] not in definite]
        facts[f"{name}.published_common"], facts[f"{name}.published_equal"] = len(common), len(agree)
        facts[f"{name}.published_only"], facts[f"{name}.local_only"] = len(only_published), len(only_local)
        out.append(f"{name} against the published translated route: {len(agree)} of {len(common)} equal, "
                   f"definitive in the published run only: {len(only_published)}, in the local run only: {len(only_local)}")
    facts["published.definite"] = sum(v in definite for v in pub.values())
    slow = [published[k]["proverif_time"] for k in pairs if pub[k] in definite and b0[k] not in definite]
    out.append(f"published translated route: {facts['published.definite']} definitive outcomes, "
               f"times of the pairs that only the published run decides: {min(slow)} s to {max(slow)} s")
    out.append("")
    differences = {}
    for name, table in (("B0", b0), ("B2", b2), ("published", pub)):
        common = [k for k in pairs if table[k] in definite and nat[k] in definite]
        differ = [k for k in common if table[k] != nat[k]]
        differences[name] = set(differ)
        facts[f"{name}.native_common"], facts[f"{name}.native_equal"] = len(common), len(common) - len(differ)
        facts[f"{name}.native_differ"], facts[f"{name}.native_differ_theories"] = len(differ), len({k[0] for k in differ})
        out.append(f"{name} against native Tamarin: {len(common) - len(differ)} of {len(common)} equal, "
                   f"{len(differ)} differ in {len({k[0] for k in differ})} theories")
    same_set = differences["B0"] == differences["B2"] == differences["published"]
    facts["native_differences_same_set"] = int(same_set)
    out.append(f"the differences with native Tamarin are the same pairs in B0, B2 and the published run: {'yes' if same_set else 'no'}")

    if args.examples:
        out.append("")
        listed = {}
        with open(os.path.join(HERE, "provenance", "models.sha256"), encoding="utf-8") as handle:
            for line in handle:
                digest, path = line.split(None, 1)
                listed[path.strip().lstrip("*")] = digest
        assert sorted(listed) == theories, "the hash list names other theories than the records"
        texts = {}
        for path, digest in listed.items():
            with open(os.path.join(args.examples, path), "rb") as handle:
                data = handle.read()
            assert hashlib.sha256(data).hexdigest() == digest, f"{path} differs from the benchmark file"
            texts[path] = data.decode("utf-8", errors="replace")
        out.append(f"theory files that equal the hash list: {len(texts)} of {len(listed)}")
        hits = {path: ground_inputs(text) for path, text in texts.items()}
        hits = {path: terms for path, terms in hits.items() if terms}
        facts["ground_input_theories"] = len(hits)
        out.append(f"theories with an input of a term without variables and names: {len(hits)}")
        for path, terms in sorted(hits.items()):
            out.append(f"  {path}: {', '.join(terms)}")
        assert set(hits) == {k[0] for k in changed}, "the scan and the changed pairs name different theories"
        xor = {path for path, text in texts.items() if re.search(r"builtins\s*:[^\n]*\bxor\b", text)}
        in_xor = [k for k in differences["B2"] if k[0] in xor]
        facts["native_differ_xor"] = len(in_xor)
        facts["native_differ_xor_theories"] = len({k[0] for k in in_xor})
        rest = sorted({k[0] for k in differences["B2"]} - xor)
        out.append(f"differences with native Tamarin in theories that declare exclusive-or: {len(in_xor)} of "
                   f"{len(differences['B2'])} (in {len({k[0] for k in in_xor})} theories), other theories: {', '.join(rest)}")

    if args.facts:
        for key, value in facts.items():
            print(f"V6.bench.{key}\t{value}")
    else:
        print("\n".join(out))


if __name__ == "__main__":
    main()
