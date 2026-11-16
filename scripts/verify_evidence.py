#!/usr/bin/env python3
"""Check the packaged evidence, without running Tamarin or ProVerif."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_tsv(relative):
    with (ROOT / relative).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def json_lines(relative):
    with (ROOT / relative).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_file(parent, relative, digest, size=None):
    path = parent / relative
    require(path.resolve().is_relative_to(parent.resolve()), f"Invalid path: {path}")
    require(path.is_file(), f"Missing file: {path}")
    if size is not None:
        require(path.stat().st_size == size, f"Size mismatch: {path}")
    require(file_digest(path) == digest, f"SHA-256 mismatch: {path}")


def verify_inventory(archives, u5_a):
    known_cohorts = {row["cohort_id"] for row in read_tsv("registry/cohorts.tsv")}
    artifacts = read_tsv("registry/artifacts.tsv")
    digests = {row["sha256"] for row in artifacts}
    archive_refs = {
        (name, row["sha256"])
        for row in artifacts
        for name in [row["filename"], *row["same_bytes_aliases"].split(";")]
        if name
    }
    require(len(digests) == len(artifacts) == 207, "Inventory size or duplicate hashes")
    for row in artifacts:
        require(set(row["cohort_ids"].split(";")) <= known_cohorts, row["filename"])
        if row["availability"] == "evidence_bundle" and archives is not None:
            checked_file(archives, row["evidence_path"], row["sha256"], int(row["bytes"]))
    if u5_a is not None:
        rows = [
            row for row in artifacts
            if row["availability"] == "standalone_release_asset"
            and row["filename"] == "U5_A_models_results.tar.gz"
        ]
        require(len(rows) == 1, "U5 A-model asset missing from inventory")
        checked_file(u5_a.parent, u5_a.name, rows[0]["sha256"], int(rows[0]["bytes"]))
    print(f"Artifacts indexed: {len(artifacts)}")
    if archives:
        print("Evidence bundle: all indexed files match")
    if u5_a:
        print("U5 A-model archive: SHA-256 matches")
    return archive_refs


def verify_historical_results():
    u5 = json_lines("experiments/u5/translation/triangulation.jsonl")
    require(len(u5) == 62, "Legacy U5 record count")
    u6 = json_lines("experiments/u6/pv_results.jsonl")
    require(len(u6) == 28, "Direct ProVerif record count")
    p5 = json_lines("experiments/p5-r3/p5-checkpoint/results/records.jsonl")
    p5_counts = Counter(r["verdict"] for r in p5 if r["job"].startswith("P5_"))
    require(p5_counts == {"verified": 965, "falsified": 160}, "P5 repetition counts")
    u11 = json_lines("experiments/u11/final-return/results/records.jsonl")
    require(len(u11) == len({r["job"] for r in u11}) == 7, "U11 unique jobs")
    require(Counter(r["verdict"] for r in u11) == {"HEAP": 7}, "U11 outcomes")
    kudos = read_tsv("experiments/kudos-h1h2/stage-d/stage_d_results.tsv")
    observed = Counter((r["cohort"], r["family"], r["status"]) for r in kudos)
    expected = {
        ("original", "H1", "MATCH"): 24,
        ("original", "H1", "DIFFERENT"): 1,
        ("original", "H2", "MATCH"): 24,
        ("diagnostic", "H1", "MATCH"): 12,
    }
    require(observed == expected, "H1/H2 cohort counts")
    c1 = read_json("experiments/u5/c1/native-closeout/native_results.json")["properties"]
    require(len({r["original_lemma"] for r in c1}) == len(c1) == 7, "C1 original properties")
    c1_counts = Counter((r["kind"], r["verdict"]) for r in c1)
    require(c1_counts == {("all-traces", "verified"): 4, ("all-traces", "falsified"): 1,
                          ("exists-trace", "verified"): 2}, "C1 quantifiers and outcomes")
    rq5b = read_tsv("experiments/rq5b/correspondence/correspondence_24.tsv")
    require(len({r["case_id"] for r in rq5b}) == len(rq5b) == 24, "RQ5(b) denominator")
    require(Counter(r["family"] for r in rq5b) == {"HSS": 4, "A": 15, "C1": 5},
            "RQ5(b) family counts")
    require(all(r["numerator_contribution"].startswith("WITHHELD") for r in rq5b),
            "RQ5(b) must remain withheld in this snapshot")
    print("U5, U6, P5, U11, H1/H2, C1 and RQ5(b) archived counts: OK")


def verify_state_results(archive_refs):
    rows = read_tsv("registry/state_comparisons.tsv")
    require(len({(r["cohort_id"], r["case_id"], r["lemma"]) for r in rows}) == len(rows) == 64,
            "State comparison keys")
    for row in rows:
        require((row["archive"], row["archive_sha256"]) in archive_refs, row["archive"])
        left = row["native_reference"]
        right = row["right_verdict"]
        require(row["comparison_to_native"] == ("MATCH" if left == right else "DIFFERENT"),
                f"Comparison mismatch: {row['cohort_id']}/{row['case_id']}/{row['lemma']}")
    counts = Counter((r["cohort_id"], r["comparison_to_native"]) for r in rows)
    require(counts == {("probe-initial", "MATCH"): 16, ("probe-z0", "MATCH"): 10,
                        ("probe-z0", "DIFFERENT"): 6, ("probe-guard", "MATCH"): 16,
                        ("probe-source-fixed", "MATCH"): 13, ("probe-source-fixed", "DIFFERENT"): 3},
            "State cohort counts")
    candidate = read_json("experiments/state-translation/source/source-inspection/build_check.json")
    require(candidate["candidate_compiled"] is False, "Candidate build state")
    probe = "experiments/state-translation/source/fixed/source_probe_ih07m7ga"
    meta = read_json("environments/fixed-ccs26/runtime.json")
    require(meta["binary_rebuild_verified"] is candidate["binary_rebuild_verified"] is False,
            "Binary rebuild status")
    tools = read_json(f"{probe}/tools.json")
    require(meta["commits"] == read_json(f"{probe}/commits.json"), "Commit metadata")
    require(meta["sha256"] == {p: r["actual"] for p, r in tools.items()}, "Tool metadata")
    print("State cohorts and build provenance: OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, help="extracted cross-tool-evidence directory")
    parser.add_argument("--u5-a", type=Path, help="path to the separately stored U5 A-model archive")
    args = parser.parse_args()
    manifest = read_tsv("registry/repository-files.tsv")
    for row in manifest:
        checked_file(ROOT, row["path"], row["sha256"], int(row["bytes"]))
    print(f"Repository file hashes: {len(manifest)}")
    archive_refs = verify_inventory(args.archives, args.u5_a)
    verify_historical_results()
    verify_state_results(archive_refs)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        sys.exit(str(error))
