"""Run inside the original benchmark image; Python 3 standard library."""
import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

EXPECTED_MODEL = "d43d55e62da0222eaa7e0f433b9b6d4131969ace3f534e19c7ba411dfc4fb196"
EXPECTED_PV = "f6b5e9606e639350085167f150e6bca7adfcdac0b34614b890e72f7f9e0c1c28"
EXPORTERS = {
    "b0": "3a6ca4b3f023d206043119671b47db40e318f71dd5616dd35f0e6c212aa44ad1",
    "b2": "a07b24ef01cbd12b3eba99491d9b980f1561ec2df41a8137d0fe2f4744dbd6f5",
}
MODEL = Path("examples/related_work/YubiSecure_KS_STM12/Yubikey.spthy")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_model():
    preferred = Path("/opt/eval") / MODEL
    if preferred.is_file():
        return preferred
    for root, dirs, files in os.walk("/"):
        if root == "/":
            dirs[:] = [d for d in dirs if d not in {"proc", "sys", "dev", "out"}]
        candidate = Path(root) / MODEL.name
        if MODEL.name in files and str(candidate).endswith("/" + str(MODE)) and digest(candidate) == EXPECTED_MODEL:
            return candidate
    raise SystemExit("Model not found. Compare the image and provenance/models.sha256.")


def run(stage, cmd, out):
    full = ["timeout", "--kill-after=5s", "300s"] + [str(x) for x in cmd]
    (out / (stage + ".command")).write_text(" ".join(shlex.quote(x) for x in full) + "\n")
    with (out / (stage + ".log")).open("wb") as stream:
        rc = subprocess.call(full, stdout=stream, stderr=subprocess.STDOUT)
    (out / (stage + ".rc")).write_text(str(rc) + "\n")
    return rc


def inspect(pvfile, log, out):
    lines = pvfile.read_text(errors="replace").splitlines()
    candidates = {}
    eq = re.compile(r"\bin\s*\(\s*publicChannel\s*,\s*=")
    typed = re.compile(r"\bin\s*\(\s*publicChannel\s*,\s*=[^;]*?:\s*bitstring\s*\)")
    helper = re.compile(r"\bin\s*\(\s*publicChannel\s*,\s*helperVar")
    for i, s in enumerate(lines, 1):
        kinds = [k for k, p in (("equality", eq), ("typed-equality", typed), ("helperVar", helper)) if p.search(s)]
        if kinds:
            candidates[i] = ",".join(kinds)
    (out / "inputs.txt").write_text("".join("%d\t%s\t%s\n" % (i, k, lines[i-1]) for i, k in candidates.items()))
    text = log.read_text(errors="replace")
    first = re.search(r"\bsyntax error\b", text, re.I)
    locations = list(re.finditer(r'File\s+"([^"]+)"\s*,\s*line\s+(\d+)[^\n]*', text[:first.start()] if first else "", re.I))
    verdict = "NO_SYNTAX_DIAGNOSTIC" if not first else "SYNTAX_LOCATION_UNRESOLVED"
    context = []
    if locations:
        loc = locations[-1]
        n = int(loc.group(2))
        context.append(loc.group().strip())
        # Do not associate a stale location from another diagnostic with this error.
        gap = text[loc.end():first.start()].strip().lower()
        if loc.group(1) in (str(pvfile), pvfile.name) and gap in ("", "error:") and 1 <= n <= len(lines):
            verdict = "SAME_LINE" if "typed-equality" in candidates.get(n, "") else "DIFFERENT_LINE"
            context.extend("%s %d\t%s" % (">" if i == n else " ", i, lines[i-1])
                           for i in range(max(1, n-3), min(len(lines), n+3)+1))
    (out / "context.txt").write_text("\n".join(context) + "\n")
    return verdict, len(candidates)


def main():
    mode, build_hash = sys.argv[1:]
    out = Path("/out")
    model = find_model()
    proverif = Path("/usr/local/bin/proverif")
    exporter = Path("/opt/section8-b3" if mode == "b3" else "/opt/rev013/exporter")
    expected = build_hash if mode == "b3" else EXPORTERS[mode]
    if mode == "b3" and expected == EXPORTERS["b2"]:
        raise SystemExit("B3 digest equals B2. Check the selected binary.")
    with (out / "hashes.txt").open("w") as stream:
        for path, want in [(model, EXPECTED_MODEL), (proverif, EXPECTED_PV), (exporter, expected)]:
            actual = digest(path)
            print(actual, path, file=stream)
            if actual != want:
                raise SystemExit("Hash mismatch: %s (expected %s, found %s)" % (path, want, actual))
    source = model.read_text(errors="replace").splitlines()
    blocks = []
    for i, line in enumerate(source):
        if re.search(r"^\s*rule\s+InitSucc\b", line):
            blocks.extend("%d\t%s" % (j+1, source[j]) for j in range(i, min(len(source), i+16)))
    (out / "InitSucc.txt").write_text("\n".join(blocks) + "\n")
    pvfile = out / ("yubikey_%s.pv" % mode)
    rc = run("export", [exporter, "-d=0", "-m=proverif", "--lemma=Login_reachable", "-o="+str(pvfile), model], out)
    if rc or not pvfile.is_file() or pvfile.stat().st_size == 0:
        raise SystemExit("Export failed; inspect export.rc and export.log")
    flags = []
    if mode == "b3":
        run("proverif-help", [proverif, "-help"], out)
        helptext = (out / "proverif-help.log").read_text(errors="replace")
        if re.search(r"(?m)^\s*-parse-only(?:\s|$)", helptext):
            flags = ["-parse-only"]
    rc = run("proverif", [proverif] + flags + [pvfile], out)
    verdict, count = inspect(pvfile, out / "proverif.log", out)
    info = ("mode=%s\nlemma=Login_reachable\nproverif_mode=%s\nexport_rc=0\n"
            "proverif_rc=%d\nlocation_check=%s\ninput_lines_listed=%d\n" %
            (mode, flags[0] if flags else "full", rc, verdict, count))
    (out / "summary.txt").write_text(info)
    print(info, end="")
    print((out / "context.txt").read_text(), end="")
    # An expected ProVerif syntax error for B2 still yields a successful evidence collection.
    return 0


if __name__ == "__main__":
    sys.exit(main())
