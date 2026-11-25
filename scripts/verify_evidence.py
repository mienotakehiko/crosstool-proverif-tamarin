#!/usr/bin/env python3
"""Check the files and records of this repository without starting a prover.

    python3 -B scripts/verify_evidence.py

The script compares every file with the inventory in
registry/repository-files.tsv, checks the table of normalized files, follows
the hash lists that the run directories contain, and tests the internal
consistency of the archived records. It reads local files only.
"""
from collections import Counter
import csv
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "registry/repository-files.tsv"
NORMALIZED = "registry/normalized-files.tsv"


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
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_file(parent, relative, digest, size=None):
    path = Path(parent) / relative
    require(path.resolve().is_relative_to(Path(parent).resolve()), f"Invalid path {path}")
    require(path.is_file(), f"Missing file {path}")
    if size is not None:
        require(path.stat().st_size == size, f"Size mismatch for {path}")
    require(file_digest(path) == digest, f"SHA-256 mismatch for {path}")


_normalized = None


def original_digest(relative):
    """Return the SHA-256 hash that the run records cite for a file.

    A few log files replace host names and local paths by placeholders, and
    one table carries translated notes. For these files the table of
    normalized files states the hash of the original, which is the value that
    result records and hash lists of the runs refer to.
    """
    global _normalized
    if _normalized is None:
        _normalized = {row["path"]: row for row in read_tsv(NORMALIZED)}
    relative = Path(relative).as_posix()
    row = _normalized.get(relative)
    return row["original_sha256"] if row else file_digest(ROOT / relative)


def check_inventory():
    manifest = read_tsv(MANIFEST)
    for row in manifest:
        checked_file(ROOT, row["path"], row["sha256"], int(row["bytes"]))
    listed = {row["path"] for row in manifest} | {MANIFEST}
    present = {
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
        if path.is_file() and not {".git", "__pycache__", ".venv"} & set(path.relative_to(ROOT).parts)
        and path.suffix not in {".pyc", ".pyo"}
    }
    require(present <= listed, f"Files without an inventory entry such as {sorted(present - listed)[:3]}")
    print(f"Inventory: {len(manifest)} files match their size and SHA-256 hash")
    rows = read_tsv(NORMALIZED)
    for row in rows:
        checked_file(ROOT, row["path"], row["published_sha256"])
        require(row["original_sha256"] != row["published_sha256"], row["path"])
    print(f"Normalized files: {len(rows)} published hashes match the table")
    series = read_tsv("registry/series.tsv")
    for row in series:
        require((ROOT / row["main_records"]).exists(), f"Missing records of series {row['series']}")
    print(f"Series index: the main records of {len(series)} series exist")


def check_hash_lists():
    """Follow every hash list that a run directory or the plan contains."""
    line = re.compile(r"^([0-9a-f]{64})\s+\*?(.+)$")
    names = [path for path in sorted(ROOT.rglob("*"))
             if path.is_file() and ".git" not in path.parts
             and (path.name == "SHA256SUMS" or path.name.endswith((".sha256", ".sha256.txt")))]
    count = Counter()
    for name in names:
        for raw in name.read_text(encoding="utf-8", errors="replace").splitlines():
            match = line.match(raw.strip())
            if not match:
                continue
            digest, target = match.groups()
            if target.startswith("/"):
                count["outside"] += 1
                continue
            path = (name.parent / target.strip()).resolve()
            if path.is_file() and path.is_relative_to(ROOT):
                require(original_digest(path.relative_to(ROOT)) == digest,
                        f"Hash list {name.relative_to(ROOT)} disagrees on {target}")
                count["match"] += 1
            else:
                count["outside"] += 1
    print(f"Hash lists: {len(names)} lists, {count['match']} entries match the original hashes, "
          f"{count['outside']} entries name tool binaries, archives or notes outside this repository")


def check_series_records():
    require(len(json_lines("runs/X0/original/triangulation.jsonl")) == 62, "X0 record count")
    require(len(json_lines("runs/G/proverif/pv_results.jsonl")) == 28, "G ProVerif record count")
    heap96 = json_lines("runs/L/heap96/records.jsonl")
    require(len(heap96) == len({r["job"] for r in heap96}) == 7, "Jobs at 96 GiB")
    kudos = read_tsv("runs/K/stage-d/stage_d_results.tsv")
    observed = Counter((r["cohort"], r["family"], r["status"]) for r in kudos)
    require(observed == {("original", "H1", "MATCH"): 24, ("original", "H1", "DIFFERENT"): 1,
                         ("original", "H2", "MATCH"): 24, ("diagnostic", "H1", "MATCH"): 12},
            "KUDOS cohort counts")
    chain = read_json("runs/chain/native-closeout/native_results.json")["properties"]
    require(len({r["original_lemma"] for r in chain}) == len(chain) == 7, "Chain properties")
    limited = read_tsv("runs/X0/resource-limited/correspondence_24.tsv")
    require(len({r["case_id"] for r in limited}) == len(limited) == 24, "Resource-limited runs")
    require(Counter(r["family"] for r in limited) == {"HSS": 4, "A": 15, "C1": 5},
            "Resource-limited runs by family")
    print("Series records: G, X0, K, L and the chain model have the expected shape")


def check_exporter_probes():
    rows = read_tsv("runs/X1/historical-probes/state_comparisons.tsv")
    require(len({(r["cohort_id"], r["case_id"], r["lemma"]) for r in rows}) == len(rows) == 64,
            "Keys of the probe table")
    for row in rows:
        agree = row["native_reference"] == row["right_verdict"]
        require(row["comparison_to_native"] == ("MATCH" if agree else "DIFFERENT"),
                f"Probe comparison {row['cohort_id']}/{row['case_id']}/{row['lemma']}")
    candidate = read_json("runs/X1/historical-probes/source/source-inspection/build_check.json")
    probe = "runs/X1/historical-probes/source/fixed/source_probe_ih07m7ga"
    runtime = read_json("env/fixed-ccs26/runtime.json")
    require(runtime["binary_rebuild_verified"] is candidate["binary_rebuild_verified"] is False,
            "Recorded rebuild status")
    require(runtime["commits"] == read_json(f"{probe}/commits.json"), "Pinned commits")
    require(runtime["sha256"] == {p: r["actual"] for p, r in read_json(f"{probe}/tools.json").items()},
            "Tool hashes of the pinned image")
    print("Exporter probes: 64 comparisons are consistent, and the pinned commits and tool hashes agree")


def check_mutation_inputs():
    base = "runs/M/historical"
    oct29 = f"{base}/oct29/mutation_extension_20261029"
    for row in read_json(f"{base}/oct28/pilot/results.json"):
        for tool, extension in (("pv", "pv"), ("tm", "spthy")):
            folder = f"{base}/oct28/pilot/{row['case']}"
            require(file_digest(ROOT / f"{folder}/model.{extension}") == row[f"{tool}_sha256"], folder)
    raw = read_json(f"{oct29}/results.json")
    completed = read_json(f"{oct29}/results_completed_reference.json")
    planned = read_json(f"{oct29}/manifest_before_runs.json")
    require(len(raw) == len(completed) == len(planned) == 23, "Cases of the main experiment")
    reference_input = f"{base}/oct29/shared_tamarin_reference/lms_s2/generated.spthy"
    reference_log = f"{base}/oct29/shared_tamarin_reference/lms_s2/tamarin.out"
    reused = {(r["seed"], r["operator"]): r["source_sha256"]
              for r in read_json(f"{base}/nov11_reference_model_hashes.json")["models"]}
    linked = set()
    for result, review, plan in zip(raw, completed, planned):
        case = result["directory"]
        require(review["directory"] == plan["directory"] == case, f"Case order {case}")
        key = result["seed"], result["operator"]
        if key in reused:
            require(result["pv_sha256"] == reused[key], f"Model reused by the frozen run {case}")
            linked.add(key)
        for tool, extension in (("pv", "pv"), ("tm", "spthy")):
            digest = result[f"{tool}_sha256"]
            require(digest == review[f"{tool}_sha256"] == plan[f"{tool}_sha256"], case)
            require(file_digest(ROOT / f"{oct29}/{case}/model.{extension}") == digest, case)
            log = original_digest(f"{oct29}/{case}/{tool.upper()}.out")
            require(log == result[f"{tool}_run"]["stdout_sha256"]
                    == review[f"{tool}_run"]["stdout_sha256"], case)
        if result["seed"] == "lms_s2":
            reference = review["reference_completion"]
            require(reference["model_sha256"] == result["tm_sha256"]
                    == file_digest(ROOT / reference_input), f"Shared reference input {case}")
            require(reference["stdout_sha256"] == original_digest(reference_log),
                    f"Shared reference log {case}")
    require(len(linked) == len(reused) == 22, "Models that the frozen run reuses")

    frozen = "runs/M/frozen_20261111"
    freeze = read_json(f"{frozen}/freeze.json")
    start = read_json(f"{frozen}/execution_started.json")
    finish = read_json(f"{frozen}/execution_finished.json")
    moment = datetime.fromisoformat
    require(moment(freeze["timestamp"]) < moment(start["timestamp"]) < moment(finish["timestamp"]),
            "Order of freeze, start and end")
    require(file_digest(ROOT / f"{frozen}/freeze.json") == start["freeze_sha256"]
            == (ROOT / f"{frozen}/freeze.sha256").read_text().split()[0], "Hash of the frozen plan")
    require(len(freeze["files"]) == 68, "Frozen input count")
    for relative, digest in freeze["files"].items():
        checked_file(ROOT / frozen, relative, digest)
    tree = file_digest(ROOT / "cimc/v0.1.1/cimc/diagnose.py")
    require(freeze["tree_version"] == "1.1" and tree == freeze["tree_sha256"], "Decision tree 1.1")
    seen = set()
    for row in read_json(f"{frozen}/results.json"):
        saved = row["run"]
        relative = saved["raw_file"]
        require(relative not in seen, f"Duplicate log {relative}")
        seen.add(relative)
        require(original_digest(f"{frozen}/{relative}") == saved["raw_sha256"], f"Log hash {relative}")
        require(read_json(str((Path(frozen) / relative).parent / "run.json")) == saved,
                f"Run metadata {relative}")
        begin = moment(saved["started_utc"])
        end = begin + timedelta(seconds=saved["elapsed_s"])
        require(moment(start["timestamp"]) <= begin <= end <= moment(finish["timestamp"]), relative)
    print("Mutation series M: models, logs and the frozen plan match their recorded hashes")


def check_generator():
    for version in ("0.1.0", "0.1.1", "0.1.2", "0.1.3"):
        text = (ROOT / f"cimc/v{version}/cimc/__init__.py").read_text()
        require(f'__version__ = "{version}"' in text, f"Version string of cimc {version}")
    tree = file_digest(ROOT / "cimc/v0.1.1/cimc/diagnose.py")
    for version in ("0.1.2", "0.1.3"):
        require(file_digest(ROOT / f"cimc/v{version}/cimc/diagnose.py") == tree,
                f"Decision tree of cimc {version}")
    pinned = (ROOT / "validation/plan/generator.txt").read_text().split("\n")
    require(pinned[0].strip() == "0.1.2", "Generator version of the validation plan")
    for line in pinned[1:]:
        if line.strip():
            digest, relative = line.split()
            checked_file(ROOT / "cimc/v0.1.2", relative, digest)
    for relative in ("al_assign.py", "diagnose.py", "evidence.py", "core.py", "checks.py", "backends.py"):
        require(file_digest(ROOT / f"cimc/v0.1.2/cimc/{relative}")
                == file_digest(ROOT / f"cimc/v0.1.3/cimc/{relative}"), f"cimc 0.1.3 changes {relative}")
    require(file_digest(ROOT / "diagnosis/v1.1/diagnose.py") == tree, "Separate copy of decision tree 1.1")
    print("Generator: four versions present, 0.1.2 matches the plan, 0.1.3 changes the input check only")


def check_validation_records():
    runners = {file_digest(ROOT / f"validation/common/{name}"): name
               for name in ("run_set.py", "run_set_monotonic.py")}
    used = Counter()
    for path in sorted((ROOT / "validation").rglob("results/environment.json")):
        digest = json.loads(path.read_text(encoding="utf-8"))["script_sha256"]
        require(digest in runners, f"Unknown runner hash in {path.relative_to(ROOT)}")
        used[runners[digest]] += 1
    sets = [path.parent.parent for path in (ROOT / "validation").rglob("results/pv_results.jsonl")]
    cited = 0
    for folder in sets:
        models = {path.stem: file_digest(path) for path in [*folder.glob("*.pv"), *folder.glob("*.spthy")]}
        for name in ("pv_results.jsonl", "tam_results.jsonl"):
            for row in json_lines(str((folder / "results" / name).relative_to(ROOT))):
                if "sha256" in row and row["model"] in models:
                    require(row["sha256"] == models[row["model"]],
                            f"Model hash in the records of {folder.relative_to(ROOT)}")
                    cited += 1
    print(f"Validation series: {sum(used.values())} environment records cite the archived runners "
          f"({used['run_set.py']} run_set.py, {used['run_set_monotonic.py']} run_set_monotonic.py), "
          f"and {cited} verdict records of {len(sets)} model sets cite the hashes of the archived models")


def main():
    check_inventory()
    check_hash_lists()
    check_series_records()
    check_exporter_probes()
    check_mutation_inputs()
    check_generator()
    check_validation_records()
    print("All checks passed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        sys.exit(str(error))
