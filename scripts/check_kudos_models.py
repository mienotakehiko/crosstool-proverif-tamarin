#!/usr/bin/env python3
"""Regenerate the 24 model inputs of the KUDOS schedules and compare them.

    python3 -B scripts/check_kudos_models.py

The table runs/K/specification-index.tsv names one specification and one
generator for each of the 12 schedules. The script runs every generator in a
temporary directory and compares its ProVerif and Tamarin outputs byte by byte
with the model inputs that runs/K/jobs.tsv lists. It starts no prover.
"""
from collections import defaultdict
from pathlib import Path
from shutil import copyfile
from subprocess import run
import sys
from tempfile import TemporaryDirectory

from verify_evidence import ROOT, file_digest, read_tsv


def main():
    cases = defaultdict(list)
    for row in read_tsv("runs/K/jobs.tsv"):
        path = ROOT / row["model_path"]
        if file_digest(path) != row["sha256"]:
            sys.exit(f"The model {path} differs from its recorded hash")
        cases[row["case"]].append(path)

    equal = 0
    for row in read_tsv("runs/K/specification-index.tsv"):
        generator, specification = ROOT / row["generator_path"], ROOT / row["specification_path"]
        with TemporaryDirectory() as directory:
            work = Path(directory)
            if specification.name == "spec.json":
                copyfile(specification, work / "spec.json")
                copyfile(generator, work / "generate.py")
                run([sys.executable, "-B", work / "generate.py"], check=True, capture_output=True)
                output = work / "models"
            else:
                output = work / "generated"
                run([sys.executable, "-B", generator, "--input", specification, "--out", output],
                    check=True, capture_output=True)
            for stored in cases.pop(row["case"]):
                if (output / stored.name).read_bytes() != stored.read_bytes():
                    sys.exit(f"The regenerated model differs from {stored}")
                equal += 1

    if cases or equal != 24:
        sys.exit(f"Expected 24 model inputs and compared {equal}")
    print("KUDOS schedules: 24 of 24 regenerated model inputs are byte-identical")


if __name__ == "__main__":
    main()
