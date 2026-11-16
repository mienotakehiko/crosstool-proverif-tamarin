#!/usr/bin/env python3
"""Write or check the release file manifest."""
import csv
import hashlib
import io
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("registry/repository-files.tsv")


def release_paths():
    if (ROOT / ".git").exists():
        output = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
        )
        paths = {Path(name.decode()) for name in output.split(b"\x00") if name}
    else:
        paths = {
            path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file()
            and not {"__pycache__", ".venv"} & set(path.parts)
            and path.suffix not in {".pyc", ".pyo"}
        }
    return sorted(path for path in paths if path != MANIFEST and (ROOT / path).is_file())


def render_manifest():
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(("path", "bytes", "sha256"))
    for relative in release_paths():
        path = ROOT / relative
        if path.is_symlink():
            raise ValueError(f"Manifest input is a symlink: {relative}")
        with path.open("rb") as stream:
            writer.writerow((relative.as_posix(), path.stat().st_size,
                             hashlib.file_digest(stream, "sha256").hexdigest()))
    return output.getvalue().encode()


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--check"]):
        sys.exit("Usage: update_manifest.py [--check]")
    target = ROOT / MANIFEST
    rendered = render_manifest()
    if sys.argv[1:]:
        if target.read_bytes() != rendered:
            sys.exit("Manifest differs from the current files.")
        print("Repository manifest: current")
    else:
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(rendered)
        temporary.replace(target)
        print(f"Wrote {MANIFEST}")
