#!/usr/bin/env python3
"""Summarize the records of the exporter build B3 (follow-up of series V6).

    python3 -B validation/V6-exporter/b3_followup/summarize_b3.py [--facts]

The script reads the records of this directory, the rows of the benchmark
comparison and the stored regression evidence of B2 under runs/X1/step8.
It locates the rejected line of the export of B2, compares the exports of B2
and B3, recomputes the outcomes of the five pairs under B3 and recomputes the
regression of series X1 under B3 from the stored stage outputs. It also counts
why the other pairs of the benchmark need no run under B3.
With --facts, it prints the counts as lines of key and value.

The script reads recorded files and runs no tool.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
BENCHMARK = os.path.join(REPOSITORY, "validation", "V6-exporter", "benchmark")
THEORY = "examples/related_work/YubiSecure_KS_STM12/Yubikey.spthy"


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def text(*parts):
    with open(os.path.join(HERE, *parts), encoding="utf-8") as handle:
        return handle.read()


def hash_list(path):
    table = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                digest, name = line.split(None, 1)
                table[name.strip().lstrip("*")] = digest
    return table


def original(relative):
    """Hash of the run for a file whose published bytes differ from it."""
    with open(os.path.join(REPOSITORY, "registry", "normalized-files.tsv"), encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["path"] == relative:
                return row["original_sha256"]
    return sha(os.path.join(REPOSITORY, relative))


def outcome(row):
    """Class of one row of the translated route, as in the benchmark comparison."""
    value = row["proverif_result"]
    if value is True or value is False:
        return "true" if value else "false"
    for flag, name in (("translate_error", "export_error"), ("proverif_timeout", "timeout"), ("proverif_oom", "oom")):
        if row[flag]:
            return name
    return "pv_error" if row["proverif_error"] else "unresolved"


def rows(path):
    with open(path, encoding="utf-8") as handle:
        return {json.loads(line)["index"]: json.loads(line) for line in handle if line.strip()}


def body(path):
    with open(path, encoding="utf-8") as handle:
        return [line for line in handle.read().split("\n") if not line.startswith("Compiled at:")]


def single(out, facts):
    models = hash_list(os.path.join(BENCHMARK, "provenance", "models.sha256"))
    binaries = hash_list(os.path.join(BENCHMARK, "provenance", "b2", "files.sha256"))
    b2 = {name: digest for digest, name in (line.split() for line in text("single", "b2", "hashes.txt").splitlines())}
    b3 = {name: digest for digest, name in (line.split() for line in text("single", "b3", "hashes.txt").splitlines())}
    assert b2["/opt/eval/" + THEORY] == b3["/opt/eval/" + THEORY] == models[THEORY]
    assert b2["/usr/local/bin/proverif"] == b3["/usr/local/bin/proverif"] == binaries["/usr/local/bin/proverif"]
    assert b2["/opt/rev013/exporter"] == binaries["/opt/rev013/exporter"]
    candidate = text("build", "candidate", "tamarin-prover.sha256").split()[0]
    assert b3["/opt/section8-b3"] == candidate
    assert sha(os.path.join(HERE, "build", "input.patch")) == text("build", "input.patch.sha256").split()[0] \
        == sha(os.path.join(REPOSITORY, "exporter", "patches", "input-equality-pattern.patch"))
    out.append(f"exporter of B2: {b2['/opt/rev013/exporter']}")
    out.append(f"exporter of B3: {candidate}")
    out.append(f"patched source of B3: {text('build', 'candidate', 'Rule.hs.sha256').split()[0]} at commit {text('build', 'metadata', 'source.commit').strip()}")
    log = text("single", "b2", "proverif.log")
    match = re.search(r'line (\d+), character (\d+):\s*\nError: Syntax error\.', log)
    assert match and text("single", "b2", "proverif.rc").strip() == "2" and text("single", "b2", "export.rc").strip() == "0"
    line, character = int(match.group(1)), int(match.group(2))
    export2 = text("single", "b2", "yubikey_b2.pv").split("\n")
    export3 = text("single", "b3", "yubikey_b3.pv").split("\n")
    rejected = export2[line - 1]
    assert rejected[character - 1] == ":" and rejected.strip() == "in(publicChannel, =myzero(): bitstring);"
    out.append(f"B2, lemma Login_reachable: ProVerif reports a syntax error at line {line}, character {character}, which is the colon of")
    out.append(f"    {rejected.strip()}")
    assert text("single", "b3", "proverif.rc").strip() == "0" and text("single", "b3", "export.rc").strip() == "0"
    assert "-parse-only" in text("single", "b3", "proverif.command") and "rror" not in text("single", "b3", "proverif.log")
    assert len(export2) == len(export3)
    changed = [i + 1 for i, (a, b) in enumerate(zip(export2, export3)) if a != b and not a.startswith("Compiled at:")]
    assert all(export3[i - 1] == export2[i - 1].replace(": bitstring);", ");") for i in changed)
    out.append(f"B3, same lemma: ProVerif parses the export (option -parse-only, exit code 0)")
    out.append(f"lines that differ between the two exports apart from the build time: {changed}")
    for i in changed:
        out.append(f"    {export3[i - 1].strip()}")
    facts["single.error_line"], facts["single.error_character"] = line, character
    facts["single.changed_lines"] = len(changed)
    return export3


def five_pairs(out, facts, export3):
    conditions = json.loads(text("five_pairs", "conditions.json"))
    assert conditions["timeout"] == 300 and conditions["memory_MB"] == 8192
    assert conditions["files"]["b3"]["/opt/rev013/exporter"] == text("build", "candidate", "tamarin-prover.sha256").split()[0]
    same = [k for k in conditions["files"]["b2"] if conditions["files"]["b2"][k] == conditions["files"]["b3"][k]]
    assert len(same) == len(conditions["files"]["b2"]) - 1
    scripts = os.path.join("validation", "V6-exporter", "b3_followup", "scripts", "five_pairs")
    for name, digest in conditions["kit"].items():
        assert original(os.path.join(scripts, name).replace(os.sep, "/")) == digest, name
    b0, b2 = rows(os.path.join(BENCHMARK, "B0", "rows.jsonl")), rows(os.path.join(BENCHMARK, "B2", "rows.jsonl"))
    table = list(csv.DictReader(text("five_pairs", "summary.tsv").splitlines(), delimiter="\t"))
    counts, parsed, same_class, seconds = collections.Counter(), 0, 0, 0.0
    out.append("")
    out.append("index  lemma                               B0          B2        B3 parse  B3 ordinary run")
    for entry in table:
        index = int(entry["index"])
        parse = json.loads(text("five_pairs", str(index), "parse", "done.json"))
        full = json.loads(text("five_pairs", str(index), "full", "done.json"))
        audit = os.path.join(HERE, "five_pairs", str(index), "parse", parse["trial"], "audit")
        export = os.path.join(audit, "translated.pv")
        lines = open(export, encoding="utf-8").read().split("\n")
        assert sha(export) == parse["generated_sha256"] == entry["parsed_pv_sha256"]
        assert sum(line.strip() in ("in(publicChannel, =myzero());", "in(publicChannel, =S(myzero()));") for line in lines) == 2
        assert not any(re.search(r"in\(publicChannel, *=[^;]*: *bitstring\)", line) for line in lines)
        accepted = open(os.path.join(audit, "parse.rc")).read().strip() == "0" and "rror" not in open(os.path.join(audit, "parse.log")).read()
        official = json.loads(text("five_pairs", str(index), "full", full["trial"], "official-result.json"))
        assert official == full["row"] and official["input_file"] == THEORY and official["lemma"] == entry["lemma"]
        assert b2[index]["proverif_error"] == "Syntax error" and b0[index]["lemma"] == entry["lemma"]
        for phase, trial in (("parse", parse["trial"]), ("full", full["trial"])):
            calls = [json.loads(line) for line in text("five_pairs", str(index), phase, trial, "audit", "docker.jsonl").splitlines()]
            assert len(calls) == 1 and conditions["image"] in calls[0] and calls[0][calls[0].index("--index") + 1] == str(index)
            assert calls[0][calls[0].index("--timeout") + 1] == "300" and calls[0][calls[0].index("--memory-limit") + 1] == "8192"
            assert sum("dst=/opt/rev013/exporter,readonly" in a and conditions["binary"] in a for a in calls[0]) == 1
        if index == 433:
            assert lines == export3
        parsed += accepted
        same_class += outcome(official) == outcome(b0[index])
        counts[outcome(official)] += 1
        seconds += official["proverif_time"]
        assert official["restriction_missing"] and b0[index]["restriction_missing"] and b2[index]["restriction_missing"]
        assert any("Restriction `smaller_implies_unequal`: was not emitted" in line for line in lines)
        out.append(f"{index}    {entry['lemma']:35s} {outcome(b0[index]):11s} {outcome(b2[index]):9s} "
                   f"{'accepted' if accepted else 'rejected':9s} {outcome(official)} ({official['proverif_time']} s)")
    out.append(f"exports of B3 that ProVerif parses: {parsed} of {len(table)}")
    out.append(f"ordinary runs of B3: {counts['timeout']} at the time limit, {counts['unresolved']} without a result, "
               f"{counts['true'] + counts['false']} with a definitive outcome, same class as B0: {same_class} of {len(table)}")
    out.append(f"sum of the ProVerif times of the ordinary runs: {seconds:.3f} s")
    out.append("the exporter omits the restriction smaller_implies_unequal of the theory under B0, B2 and B3")
    facts["five.pairs"], facts["five.parsed"], facts["five.same_class_as_B0"] = len(table), parsed, same_class
    facts["five.timeout"], facts["five.unresolved"] = counts["timeout"], counts["unresolved"]
    facts["five.definitive"] = counts["true"] + counts["false"]


def regression(out, facts):
    base = os.path.join(HERE, "regression")
    stored = os.path.join(REPOSITORY, "runs", "X1", "step8")
    summary = json.loads(text("regression", "summary.json"))
    reference = {(r["origin"], r["suite"], r["case"], r["lemma"]): r for r in json.load(open(os.path.join(stored, "summary.json"), encoding="utf-8"))}
    assert text("regression", "candidate-binary.sha256").split()[0] == text("build", "candidate", "tamarin-prover.sha256").split()[0]
    assert text("regression", "fixed-image.txt") == open(os.path.join(stored, "fixed-image.txt"), encoding="utf-8").read()
    agree, stages, same_export, same_fields = 0, 0, 0, 0
    kinds = collections.Counter()
    for row in summary:
        key = (row["origin"], row["suite"], row["case"], row["lemma"])
        folder = os.path.join(base, *key)
        for stage in ("native", "export", "pv"):
            meta = json.load(open(os.path.join(folder, f"{stage}.meta.json"), encoding="utf-8"))
            assert open(os.path.join(folder, f"{stage}.exit_code.txt")).read().strip() == "0" and meta["rc"] == 0 and not meta["timeout"]
            stages += 1
        native = re.search(rf"^\s*{re.escape(row['lemma'])} \((exists-trace|all-traces)\): (verified|falsified)",
                           open(os.path.join(folder, "native.stdout.txt"), encoding="utf-8").read(), re.M)
        results = re.findall(r"^RESULT (.*) is (true|false)\.", open(os.path.join(folder, "pv.stdout.txt"), encoding="utf-8").read(), re.M)
        assert native and len(results) == 1
        quantifier, verdict = native.groups()
        if quantifier == "exists-trace":
            assert results[0][0].startswith("not ")
            native_outcome = "reachable" if verdict == "verified" else "unreachable"
            translated = "reachable" if results[0][1] == "false" else "unreachable"
        else:
            native_outcome = "holds" if verdict == "verified" else "fails"
            translated = "holds" if results[0][1] == "true" else "fails"
        assert (native_outcome, translated, results[0][1]) == (row["native"], row["translated"], row["pv_raw"])
        agree += native_outcome == translated
        kinds[translated] += 1
        same_fields += all(row[f] == reference[key][f] for f in ("native", "translated", "pv_raw", "status", "model_sha256"))
        same_export += body(os.path.join(folder, "translated.pv")) == body(os.path.join(stored, *key, "translated.pv"))
    decision = json.loads(text("regression", "decision.json"))
    assert decision["decision"] == "PASS" and decision["MATCH"] == len(summary) == len(reference) and decision["DIFFERENT"] == 0
    models = len({(r["suite"], r["case"]) for r in summary})
    out.append("")
    out.append(f"regression of series X1 under B3: {len(summary)} pairs of {models} models, {stages} stages with exit code 0 and within their limit")
    out.append(f"agreement of the translated route with native Tamarin: {agree} of {len(summary)} "
               f"({kinds['reachable']} reachable, {kinds['unreachable']} unreachable, {kinds['holds']} hold)")
    out.append(f"pairs with the outcomes of B2: {same_fields} of {len(summary)}")
    out.append(f"exports equal to the exports of B2 apart from the build time: {same_export} of {len(summary)}")
    facts["x1.pairs"], facts["x1.models"], facts["x1.stages"] = len(summary), models, stages
    facts["x1.agree"], facts["x1.same_outcome_as_B2"], facts["x1.same_export_as_B2"] = agree, same_fields, same_export


def other_pairs(out, facts):
    """The pairs of the benchmark outside the five pairs, read from the rows of B0 and B2.

    The third patch changes an export only where B2 writes a type after an equality
    pattern of an input, and ProVerif rejects such a file at its parser. A pair whose
    outcome under B2 follows the parser therefore has the same export under B3. The
    other pairs are lemmas that the formula translation of the exporter declines.
    """
    b0, b2 = rows(os.path.join(BENCHMARK, "B0", "rows.jsonl")), rows(os.path.join(BENCHMARK, "B2", "rows.jsonl"))
    assert sorted(b0) == sorted(b2)
    syntax = sorted(i for i, row in b2.items() if "yntax error" in str(row["proverif_error"]))
    assert all(b2[i]["input_file"] == THEORY for i in syntax) and len(syntax) == sum(row["input_file"] == THEORY for row in b2.values())
    assert not any("yntax error" in str(row["proverif_error"]) for row in b0.values())
    others = [i for i in b2 if b2[i]["input_file"] != THEORY]
    after_parser, declined = collections.Counter(), collections.Counter()
    for i in others:
        row, kind, message = b2[i], outcome(b2[i]), str(b2[i]["proverif_error"])
        assert not row["translate_error"]
        if kind in ("true", "false", "oom", "timeout", "unresolved"):
            after_parser[kind] += 1
        elif message.startswith("Non-convergent equations"):
            after_parser["equations"] += 1
        else:
            assert message.startswith(("Formula contains KU fact", "Exists-trace formula contains K fact")), message
            assert str(b0[i]["proverif_error"]) == message, i
            declined["KU fact" if "KU fact" in message else "K fact in an exists-trace lemma"] += 1
    patches = os.path.join(REPOSITORY, "exporter", "patches")
    changed = set()
    for name in ("leafless_ground_candidate.patch", "row-id-guards.patch", "input-equality-pattern.patch"):
        with open(os.path.join(patches, name), encoding="utf-8") as handle:
            changed |= {line.split()[1].split("/", 1)[1] for line in handle if line.startswith("+++ ")}
    assert changed == {"lib/export/src/Export/ProVerif/Rule.hs"}, changed
    parsed, refused = sum(after_parser.values()), sum(declined.values())
    assert parsed + refused == len(others)
    out.append("")
    out.append(f"pairs of the benchmark with a syntax error of ProVerif under B2: {len(syntax)}, all of the YubiKey theory, and none under B0")
    out.append(f"other pairs of the benchmark: {len(others)}")
    out.append(f"  outcome under B2 that follows the parser of ProVerif: {parsed} "
               f"({after_parser['true']} true, {after_parser['false']} false, {after_parser['oom']} memory exhausted, "
               f"{after_parser['timeout']} time limit, {after_parser['unresolved']} no result, {after_parser['equations']} equations without a termination proof)")
    out.append(f"  lemma that the formula translation declines, with the same message under B0: {refused} "
               f"({declined['KU fact']} with a KU fact, {declined['K fact in an exists-trace lemma']} exists-trace lemmas with a K fact)")
    out.append("  source file that the three patches change: " + ", ".join(sorted(changed)))
    facts["other.pairs"], facts["other.after_parser"], facts["other.declined"] = len(others), parsed, refused
    facts["other.declined_ku"], facts["other.declined_k"] = declined["KU fact"], declined["K fact in an exists-trace lemma"]
    facts["other.syntax_errors_B2"], facts["patched_source_files"] = len(syntax) - sum(1 for i in syntax if b2[i]["input_file"] == THEORY), len(changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--facts", action="store_true")
    args = parser.parse_args()
    out, facts = [], collections.OrderedDict()
    export3 = single(out, facts)
    five_pairs(out, facts, export3)
    regression(out, facts)
    other_pairs(out, facts)
    if args.facts:
        for key, value in facts.items():
            print(f"V6.b3.{key}\t{value}")
    else:
        print("\n".join(out))


if __name__ == "__main__":
    main()
