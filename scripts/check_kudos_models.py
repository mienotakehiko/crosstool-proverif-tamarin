#!/usr/bin/env python3
"""Regenerate the 12 archived KUDOS schedules and compare all 24 inputs."""
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
            sys.exit(f"Archived KUDOS model hash differs: {path}")
        cases[row["case"]].append(path)

    regenerated = 0
    for row in read_tsv("runs/K/specification-index.tsv"):
        case = row["case"]
        generator, spec = ROOT / row["generator_path"], ROOT / row["specification_path"]
        with TemporaryDirectory() as directory:
            temporary = Path(directory)
            if spec.name == "spec.json":
                copyfile(spec, temporary / "spec.json")
                copyfile(generator, temporary / "generate.py")
                run([sys.executable, "-B", temporary / "generate.py"], check=True, capture_output=True)
                output = temporary / "models"
            else:
                output = temporary / "generated"
                run([sys.executable, "-B", generator, "--input", spec, "--out", output],
                    check=True, capture_output=True)
            for archived in cases.pop(case):
                if (output / archived.name).read_bytes() != archived.read_bytes():
                    sys.exit(f"Generated KUDOS model differs: {archived}")
                regenerated += 1

    if cases or regenerated != 24:
        sys.exit(f"Expected all 24 KUDOS inputs, checked {regenerated}")
    print("KUDOS model regeneration: 24/24 byte-identical")


if __name__ == "__main__":
    main()
