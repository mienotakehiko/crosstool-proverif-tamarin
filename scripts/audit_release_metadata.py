#!/usr/bin/env python3
"""Screen release files for machine-local identifiers, credentials and opaque files."""
import argparse
from collections import Counter
import csv
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "local-user-path": rb"(?i)/(?:home|Users)/[a-z0-9_.-]+|/mnt/[a-z]/Users/|[a-z]:[\\/]+Users[\\/]+|/workspace/(?:scratch|root)/[a-z0-9_.-]+|/root/(?:\.ssh|\.aws|cryptography-experiments)",
    "local-host": rb"(?i)\b(?:[a-z0-9]+-){2,3}(?:pc|ws)\b|\b(?:desktop|laptop)-[a-z0-9]{5,}\b|\bip-(?:\d{1,3}-){3}\d{1,3}\b",
    "internal-network": rb"(?i)\b(?:hostname|private[_ -]?ip|internal[_ -]?ip|host)\b[\s\x22:=]{1,12}(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b",
    "private-key": rb"-----BEGIN (?:[A-Z0-9]+ ){0,5}PRIVATE KEY-----",
    "provider-token": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{45,}\b|\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b|\b(?:xox[baprs]-[A-Za-z0-9-]{18,}|glpat-[A-Za-z0-9_-]{18,}|AIza[A-Za-z0-9_-]{30,})\b",
    "authorization": rb"(?im)\bauthorization[\x22\x27 ]*:[ \x22\x27]*(?:bearer|basic)[ \t]+[A-Za-z0-9_./=+\-]{15,}|https?://[^/@\s]{1,80}:[^/@\s]{3,120}@",
    "secret-assignment": rb"(?im)\b(?:aws_secret_access_key|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|password)\b[\x22\x27 \t]*[:=][\x22\x27 \t]*[A-Za-z0-9_/+=.\-]{16,}",
}
PATTERNS = {kind: re.compile(rule) for kind, rule in RULES.items()}
SENSITIVE_NAMES = {".env", ".git-credentials", ".netrc", "_netrc", "authorized_keys",
                   "id_rsa", "id_ed25519", "id_ecdsa", "credentials", "htpasswd"}
OPAQUE = (".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".pdf", ".pem", ".key", ".pfx", ".p12", ".exe")


def scan(content, relative):
    findings = []
    name = Path(relative).name.lower()
    parts = {part.lower() for part in Path(relative).parts}
    if (name in SENSITIVE_NAMES or name.startswith(".env.")
            or parts & {".aws", ".ssh", ".kube", ".gnupg"}
            or (name == "config.json" and ".docker" in parts)):
        findings.append("authentication-file")
    if name.endswith(OPAQUE) or b"\0" in content:
        findings.append("opaque-file")
    for kind, expression in PATTERNS.items():
        if expression.search(content):
            findings.append(kind)
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", action="store_true", help="print category and relative path only")
    args = parser.parse_args()
    manifest = ROOT / "registry/repository-files.tsv"
    with manifest.open(encoding="utf-8", newline="") as stream:
        paths = [r["path"] for r in csv.DictReader(stream, delimiter="\t")]
    paths.append(manifest.relative_to(ROOT).as_posix())
    totals = Counter()
    for name in paths:
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            sys.exit(f"Invalid release path: {name}")
        if path == Path(__file__).resolve():
            continue  # The scanner contains matching patterns by design.
        results = scan(path.read_bytes(), name)
        totals.update(results)
        if args.findings:
            for result in results:
                print(f"{result}\t{name}")
    print(f"Release metadata scan: {len(paths) - 1} files, {totals.total()} findings")
    return int(bool(totals))


if __name__ == "__main__":
    sys.exit(main())
