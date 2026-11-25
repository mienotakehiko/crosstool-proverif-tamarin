#!/usr/bin/env python3
"""Write or check the file inventory registry/repository-files.tsv.

    python3 -B scripts/update_manifest.py            writes the inventory
    python3 -B scripts/update_manifest.py --check    compares it with the files

The inventory lists the path, the size in bytes and the SHA-256 hash of every
file except itself. Inside a Git working tree the script takes the file list
from Git, so files that .gitignore excludes stay out of the inventory.
"""
import csv
import hashlib
import io
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("registry/repository-files.tsv")


def listed_paths():
    if (ROOT / ".git").exists():
        output = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
        paths = {Path(name.decode()) for name in output.split(b"\x00") if name}
    else:
        paths = {
            path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file()
            and not {"__pycache__", ".venv"} & set(path.parts)
            and path.suffix not in {".pyc", ".pyo"}
        }
    return sorted(path for path in paths if path != MANIFEST and (ROOT / path).is_file())


def render():
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(("path", "bytes", "sha256"))
    for relative in listed_paths():
        path = ROOT / relative
        if path.is_symlink():
            raise ValueError(f"The inventory accepts no symbolic link such as {relative}")
        with path.open("rb") as stream:
            writer.writerow((relative.as_posix(), path.stat().st_size,
                             hashlib.file_digest(stream, "sha256").hexdigest()))
    return output.getvalue().encode()


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--check"]):
        sys.exit("Usage: update_manifest.py [--check]")
    target = ROOT / MANIFEST
    rendered = render()
    if sys.argv[1:]:
        if target.read_bytes() != rendered:
            sys.exit("The inventory differs from the current files.")
        print("The inventory matches the current files.")
    else:
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(rendered)
        temporary.replace(target)
        print(f"Wrote {MANIFEST}")
