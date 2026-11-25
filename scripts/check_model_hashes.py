#!/usr/bin/env python3
"""Derive the tactic variants of the hand-written theories and compare their hashes.

    python3 -B scripts/check_model_hashes.py

The records of the series P1 to P4 state the SHA-256 hash of every model. This
script copies the hand-written theories to a temporary directory, derives their
variants with models/tamarin-kit-v3/tactics/make_variants.py and compares the
hashes. For the eight corpus theories it compares the recorded hashes with
corpus/corpus.tsv. The script starts no prover.
"""
from collections import Counter
from pathlib import Path
from shutil import copytree
from subprocess import run
import sys
from tempfile import TemporaryDirectory

from verify_evidence import ROOT, file_digest, json_lines, read_tsv


def main():
    expected = {}
    jobs = Counter()
    for phase in ("P1", "P2", "P3", "P4"):
        for row in json_lines(f"runs/{phase}/records.jsonl"):
            name, digest = row["model"], row["sha256"]
            if expected.setdefault(name, digest) != digest:
                sys.exit(f"Two hashes for the model {name}")
            jobs[name] += 1

    corpus = {row["record_model"]: row["record_sha256"] for row in read_tsv("corpus/corpus.tsv")}
    for name, digest in corpus.items():
        if expected.get(name) != digest:
            sys.exit(f"The corpus table and the records disagree on {name}")

    with TemporaryDirectory() as directory:
        work = Path(directory)
        copytree(ROOT / "models/handwritten", work / "handwritten",
                 ignore=lambda _folder, names: [n for n in names if n == "__pycache__"])
        copytree(ROOT / "models/tamarin-kit-v3/tactics", work / "kit/tactics")
        run([sys.executable, "-B", work / "kit/tactics/make_variants.py"], check=True)
        variants = work / "kit/variants"
        missing, different, equal = [], [], []
        for name, digest in expected.items():
            if name in corpus:
                continue
            model = variants / name
            if not model.is_file():
                missing.append(name)
            elif file_digest(model) != digest:
                different.append(name)
            else:
                equal.append(name)

    print(f"Derived variants with the recorded hash: {len(equal)} ({sum(jobs[n] for n in equal)} jobs)")
    print(f"Corpus theories with the recorded hash: {len(corpus)} ({sum(jobs[n] for n in corpus)} jobs)")
    for name in sorted(missing + different):
        print(f"{name}\t{expected[name]}\t{'missing' if name in missing else 'different'}")
    if missing or different:
        sys.exit(1)


if __name__ == "__main__":
    main()
