#!/usr/bin/env python3
"""Recheck the X1 release ledger and, when supplied, the six original archives."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import sys
import tarfile
from verify_evidence import ROOT, checked_file, read_json, read_tsv, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals", type=Path, help="directory containing step3.tar.gz through step8.tar.gz")
    args = parser.parse_args()
    cohorts = read_tsv("registry/x1_archive_review.tsv")
    provenance = read_json("runs/X1/provenance.json")["evidence"]
    require({r["step"] for r in cohorts} == set(provenance) and len(cohorts) == 6, "X1 archive index")
    ledger = read_tsv("registry/recovered-files.tsv")
    for row in cohorts:
        step = row["step"]
        sha = row["sha256"]
        require(sha == provenance[step]["sha256"] and row["archive"] == Path(provenance[step]["archive"]).name,
                f"{step} provenance")
        released = {e["source_member"].removeprefix("./"): e for e in ledger
                    if e["path"].startswith(f"runs/X1/{step}/") and e["archive_sha256"] == sha}
        require(len(released) == int(row["released_members"]), f"{step} released member count")
        for entry in released.values():
            checked_file(ROOT, entry["path"], entry["published_sha256"])
        source_manifest = released.get("SHA256SUMS")
        if source_manifest:
            require(len((ROOT / source_manifest["path"]).read_text().splitlines()) ==
                    int(row["member_hashes_verified"]), f"{step} source manifest row count")
        if args.originals:
            checked_file(args.originals, row["archive"], sha, int(row["bytes"]))
            with tarfile.open(args.originals / row["archive"]) as archive:
                members = {}
                for member in archive:
                    if member.isfile():
                        name = PurePosixPath(member.name)
                        require(not name.is_absolute() and ".." not in name.parts and str(name) not in members,
                                f"{step} invalid archive member")
                        with archive.extractfile(member) as source:
                            members[str(name)] = hashlib.file_digest(source, "sha256").hexdigest()
                require(len(members) == int(row["file_members"]), f"{step} member count")
                require(all(members[name] == entry["source_sha256"] for name, entry in released.items()),
                        f"{step} member source hash")
                if source_manifest:
                    for line in (ROOT / source_manifest["path"]).read_text().splitlines():
                        member_sha, name = line.split(None, 1)
                        require(members[name.lstrip("*").removeprefix("./")] == member_sha, f"{step} {name}")
        print(f"{step}: {len(released)} released members verified"
              + ("; original archive verified" if args.originals else ""))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, tarfile.TarError) as error:
        sys.exit(str(error))
