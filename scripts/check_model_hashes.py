#!/usr/bin/env python3
"""Derive screening model variants in a temporary directory and check SHA-256."""
from pathlib import Path
from shutil import copytree
from subprocess import run
import sys
from tempfile import TemporaryDirectory
from collections import Counter
from verify_evidence import ROOT, file_digest, json_lines, read_tsv


def main():
    expected = {}
    jobs = Counter()
    for phase in ("P1", "P2", "P3", "P4"):
        for row in json_lines(f"runs/{phase}/records.jsonl"):
            name, sha = row["model"], row["sha256"]
            if expected.setdefault(name, sha) != sha:
                sys.exit(f"Conflicting screening hashes for {name}")
            jobs[name] += 1

    corpus_models = {row["record_model"]: row["record_sha256"]
                     for row in read_tsv("registry/corpus.tsv")}
    for name, sha in corpus_models.items():
        if expected.get(name) != sha:
            sys.exit(f"Corpus record mismatch: {name}")

    with TemporaryDirectory() as directory:
        temporary = Path(directory)
        copytree(ROOT / "models/handwritten", temporary / "handwritten",
                 ignore=lambda _d, names: [n for n in names if n == "__pycache__"])
        copytree(ROOT / "models/tamarin-kit-v3/tactics", temporary / "kit/tactics")
        run([sys.executable, "-B", temporary / "kit/tactics/make_variants.py"], check=True)
        variants = temporary / "kit/variants"

        missing, mismatched, matched = [], [], []
        for name, sha in expected.items():
            if name in corpus_models:
                continue
            model = variants / name
            if not model.is_file():
                missing.append(name)
            elif file_digest(model) != sha:
                mismatched.append(name)
            else:
                matched.append(name)

    print(f"Matching handwritten variant hashes: {len(matched)} ({sum(jobs[n] for n in matched)} jobs)")
    print(f"Corpus record hashes: {len(corpus_models)} ({sum(jobs[n] for n in corpus_models)} jobs)")
    print(f"Absent theories: {len({n.split('__T')[0] for n in missing})}")
    for name in sorted(missing + mismatched):
        print(f"{name}\t{expected[name]}\t{'missing' if name in missing else 'mismatch'}")
    if missing or mismatched:
        sys.exit(1)


if __name__ == "__main__":
    main()
