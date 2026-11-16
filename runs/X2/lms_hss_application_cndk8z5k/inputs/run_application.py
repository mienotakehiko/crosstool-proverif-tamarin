"""Compare Tamarin exports of the saved LMS and HSS models."""

import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time


ROOT = Path(__file__).resolve().parent
IMAGE = "sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793"
IMAGE_RECORD = f"{IMAGE} linux/amd64"
BINARY = {
    "baseline": "3a6ca4b3f023d206043119671b47db40e318f71dd5616dd35f0e6c212aa44ad1",
    "candidate": "a07b24ef01cbd12b3eba99491d9b980f1561ec2df41a8137d0fe2f4744dbd6f5",
}
RUNTIME = {
    "/usr/local/bin/tamarin-prover": "b942e7f58d15023bc1a7210c0bedbc0d36db921f0a54888827bca7989730f70a",
    "/usr/local/bin/proverif": "f6b5e9606e639350085167f150e6bca7adfcdac0b34614b890e72f7f9e0c1c28",
    "/usr/local/bin/maude": "13b89491dcfeef5a0befba10db503de1937fc46279320242423fc38f1fd830a0",
    "/opt/eval/eval.py": "29ec8cca3a7ef913d5ce8ae7e9d73cc965f9a3a6971ad8d440cee6809860eb40",
}
SELECTIONS = {
    "legacy_lms": ["exec", "LS1", "LS4_pure"],
    "same_cim_lms": ["exec", "LS1", "LS4_pure"],
    "hss_inj": ["exec", "LS7"],
    "hss_noinj": ["exec", "LS7"],
}
PAIR_COUNT = sum(map(len, SELECTIONS.values()))
KIT_FILES = {"run_application.py", "models.json", "README_ja.md"} | {
    f"models/{case}.spthy" for case in SELECTIONS
}
FOOTER = re.compile(
    r"\n\(\*\nGenerated from:\n[^*]*\*\)\s*\Z"
)
PROCESS_MARKER = re.compile(r"^\(\* Processes \*\)[ \t]*$", re.M)
QUERY_MARKER = re.compile(r"^\(\* Queries \*\)[ \t]*$", re.M)
COMMENT = re.compile(r"\(\*.*?\*\)", re.S)
NOTE = re.compile(
    r"\b(?:warning|omitted|unsupported)\b|translation failed|not emitted|has negated event"
    r"|incomplete|outside the supported|wellformedness checks failed", re.I
)


def sha(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
        return digest.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(folder, label, command, limit):
    folder.mkdir(parents=True, exist_ok=True)
    dump(folder / f"{label}.command.json", command)
    start = time.monotonic()
    timed_out = False
    rc = 127
    with (folder / f"{label}.stdout.txt").open("wb") as stdout, (
        folder / f"{label}.stderr.txt"
    ).open("wb") as stderr:
        try:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        except OSError as exc:
            stderr.write((str(exc) + "\n").encode("utf-8"))
        else:
            try:
                rc = process.wait(timeout=limit)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                timed_out = isinstance(exc, subprocess.TimeoutExpired)
                rc = 124 if timed_out else 130
    record = {"rc": rc, "timeout": timed_out, "limit_seconds": limit,
              "wall_seconds": time.monotonic() - start}
    dump(folder / f"{label}.meta.json", record)
    return record


def validate_kit(root):
    frozen = json.loads((root / "KIT_HASHES.json").read_text(encoding="utf-8"))
    if set(frozen) != KIT_FILES:
        raise ValueError("kit_manifest_file_set_mismatch")
    for name, expected in frozen.items():
        if sha(root / name) != expected:
            raise ValueError(f"kit_hash_mismatch: {name}")
    models = json.loads((root / "models.json").read_text(encoding="utf-8"))
    if [m["id"] for m in models] != list(SELECTIONS):
        raise ValueError("model_selection_mismatch")
    for model in models:
        case = model["id"]
        if model["file"] != f"models/{case}.spthy" or model["lemmas"] != SELECTIONS[case]:
            raise ValueError(f"lemma_selection_mismatch: {case}")
        path = root / model["file"]
        if sha(path) != model["sha256"]:
            raise ValueError(f"model_hash_mismatch: {case}")
        source = path.read_text(encoding="utf-8")
        for lemma in model["lemmas"]:
            if len(re.findall(r"^lemma\s+" + re.escape(lemma) + r"\s*(?:\[|:)", source, re.M)) != 1:
                raise ValueError(f"source_lemma_missing_or_duplicated: {case}/{lemma}")
    return models


def inspect_pv(text, lemma):
    body = FOOTER.sub("", text).rstrip() + "\n"
    markers = list(PROCESS_MARKER.finditer(body))
    if len(markers) != 1:
        raise ValueError("process_marker_missing_or_duplicated")
    prefix = body[:markers[0].start()]
    sections = QUERY_MARKER.split(prefix)
    if len(sections) != 2:
        raise ValueError("query_section_missing_or_duplicated")
    section = sections[1]
    code = COMMENT.sub("", section)
    count = len(re.findall(r"^\s*query\b", code, re.M))
    if count != 1 or not re.search(r"\(\*\s*" + re.escape(lemma) + r"\s*\*\)", section):
        raise ValueError(f"requested_query_missing_or_ambiguous: {lemma} ({count} queries)")
    if not re.search(r"^\s*process\b", COMMENT.sub("", body[markers[0].end():]), re.M):
        raise ValueError("process_body_missing")
    return body, prefix


def scan_diagnostics(text):
    warnings, information = [], []
    for number, line in enumerate(text.splitlines(), 1):
        codes = set(re.findall(r"\[(PV-[A-Z0-9-]+)\]", line))
        record = {"line": number, "text": line.strip()}
        if NOTE.search(line) or codes - {"PV-GOAL-INVERTED"}:
            warnings.append(record)
        elif codes or "Lemma has a leading negation" in line:
            information.append(record)
    return {"warnings": warnings, "information": information}


def export_one(out, root, model, lemma, variant, binary):
    folder = out / model["id"] / lemma / variant
    pv = folder / "translated.pv"
    meta = run(folder, "export", [
        binary, "+RTS", "-N1", "-M768m", "-RTS", "-d=0", "-m=proverif",
        f"--lemma={lemma}", f"-o={pv}", str(root / model["file"]),
    ], 60)
    row = {"model": model["id"], "lemma": lemma, "variant": variant,
           "source_sha256": model["sha256"], "export": meta, "status": "REVIEW"}
    diagnostics = {}
    for name in ("export.stdout.txt", "export.stderr.txt", "translated.pv"):
        path = folder / name
        if path.is_file():
            diagnostics[name] = scan_diagnostics(path.read_text(encoding="utf-8", errors="replace"))
    row["diagnostics"] = diagnostics
    if pv.is_file():
        row["generated_sha256"] = sha(pv)

    if meta["rc"] != 0:
        row["reason"] = "export_timed_out" if meta["timeout"] else "export_failed"
        return row, None
    if not pv.is_file() or pv.stat().st_size == 0:
        row["reason"] = "translated_pv_missing_or_empty"
        return row, None
    try:
        body, prefix = inspect_pv(pv.read_text(encoding="utf-8"), lemma)
    except ValueError as exc:
        row["reason"] = str(exc)
        return row, None

    row["queries"] = 1
    row["row_condition_lines"] = [
        line.strip() for line in body.splitlines() if "get " in line and "suchthat" in line
    ]
    if any(d["warnings"] for d in diagnostics.values()):
        row["reason"] = "translation_diagnostic"
    else:
        row["status"] = "EXPORTED"
    return row, (body, prefix)


def compare_exports(out, root, models, binaries):
    rows, pairs = [], []
    fields = ("model", "lemma", "status", "declarations_query_prefix_equal", "body_equal",
              "baseline_status", "candidate_status")
    with (out / "comparison.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for model in models:
            for lemma in model["lemmas"]:
                outputs, states = {}, {}
                for variant, binary in binaries.items():
                    row, result = export_one(out, root, model, lemma, variant, binary)
                    rows.append(row)
                    dump(out / "summary.json", rows)
                    if result is None:
                        raise RuntimeError(f"{model['id']}/{lemma}/{variant}: {row['reason']}")
                    outputs[variant] = result
                    states[variant] = row["status"]
                old, old_prefix = outputs["baseline"]
                new, new_prefix = outputs["candidate"]
                same_prefix = old_prefix == new_prefix
                same_body = old == new
                status = "UNCHANGED" if same_body else "CHANGED"
                if not same_prefix or "REVIEW" in states.values():
                    status = "REVIEW"
                comparison = dict(zip(fields, (model["id"], lemma, status, same_prefix,
                                              same_body, states["baseline"], states["candidate"])))
                pair_dir = out / model["id"] / lemma
                dump(pair_dir / "comparison.json", comparison)
                changes = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                               fromfile="baseline", tofile="candidate")
                (pair_dir / "changes.diff").write_text("".join(changes), encoding="utf-8")
                pairs.append(comparison)
                writer.writerow(comparison)
                stream.flush()
                print(f"{model['id']}\t{lemma}\t{status}", flush=True)
                if not same_prefix:
                    raise RuntimeError(f"{model['id']}/{lemma}: declaration_or_query_changed")
    return rows, pairs


def inside():
    out = Path("/work")
    try:
        models = validate_kit(ROOT)
        checks = {path: sha(path) for path in RUNTIME}
        dump(out / "runtime.json", checks)
        if checks != RUNTIME:
            raise ValueError("runtime_hash_mismatch")
        binaries = {variant: f"/{variant}-tamarin" for variant in BINARY}
        checks = {variant: sha(path) for variant, path in binaries.items()}
        dump(out / "binary_hashes.json", checks)
        if checks != BINARY:
            raise ValueError("mounted_binary_hash_mismatch")
        rows, pairs = compare_exports(out, ROOT, models, binaries)
    except Exception as exc:
        dump(out / "inside_status.json", {"complete": False, "error": str(exc)})
        raise
    complete = len(rows) == 2 * PAIR_COUNT and len(pairs) == PAIR_COUNT
    dump(out / "inside_status.json", {
        "complete": complete, "exports": len(rows), "pairs": len(pairs),
        "review_rows": sum(r["status"] == "REVIEW" for r in rows),
        "review_pairs": sum(p["status"] == "REVIEW" for p in pairs),
        "provers_run": 0,
    })
    if not complete:
        raise RuntimeError("incomplete_export_collection")


def launch(files):
    out = Path(tempfile.mkdtemp(prefix="lms_hss_application_", dir=ROOT))
    snapshot = out / "inputs"
    snapshot.mkdir()
    results = out / "results"
    results.mkdir()
    for name in sorted(KIT_FILES | {"KIT_HASHES.json"}):
        dest = snapshot / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    name = out.name.replace("_", "-")
    print("RESULT_DIR=" + str(out), flush=True)
    launched = False
    error = None
    try:
        meta = run(out, "image", ["docker", "image", "inspect", "--format",
                                  "{{.Id}} {{.Os}}/{{.Architecture}}", IMAGE], 30)
        if meta["rc"] != 0 or (out / "image.stdout.txt").read_text().strip() != IMAGE_RECORD:
            raise RuntimeError("fixed_image_missing_or_mismatch")
        cmd = [
            "docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
            "--cpus=1", "--memory=2g", "--memory-swap=2g", "--pids-limit=128",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--name", name,
            "--user", f"{os.getuid()}:{os.getgid()}", "--env", "HOME=/work", "--env", "PYTHONUTF8=1",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
            "--mount", f"type=bind,src={snapshot},dst=/kit,readonly",
            "--mount", f"type=bind,src={results},dst=/work",
        ]
        for variant, path in files.items():
            cmd += ["--mount", f"type=bind,src={path},dst=/{variant}-tamarin,readonly"]
        cmd += ["--workdir", "/work", "--entrypoint", "python3",
                IMAGE, "-B", "/kit/run_application.py", "--inside"]
        launched = True
        meta = run(out, "container", cmd, 1500)
        if meta["rc"] != 0:
            raise RuntimeError(f"container_failed: rc={meta['rc']}; see container.stderr.txt")
        status = json.loads((results / "inside_status.json").read_text(encoding="utf-8"))
        if (status["complete"], status["exports"], status["pairs"]) != (True, 2 * PAIR_COUNT, PAIR_COUNT):
            raise RuntimeError("incomplete_inside_status")
    except (Exception, KeyboardInterrupt) as exc:
        error = str(exc) or type(exc).__name__
    finally:
        if launched:
            run(out, "cleanup", ["docker", "rm", "-f", name], 20)
        dump(out / "host_status.json", {"complete": error is None, "error": error})
        entries = sorted(path for path in out.rglob("*") if path.is_file())
        (out / "SHA256SUMS").write_text("".join(
            f"{sha(path)}  ./{path.relative_to(out)}\n" for path in entries
        ), encoding="utf-8")
        archive = out.with_suffix(".tar.gz")
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(out, arcname=out.name)
        checksum = Path(f"{archive}.sha256")
        checksum.write_text(f"{sha(archive)}  {archive.name}\n", encoding="utf-8")
        print(f"ARCHIVE={archive}\nHASH={checksum}\nCOMPLETE={error is None}", flush=True)
    if error:
        raise SystemExit(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        validate_kit(ROOT)
        if args.self_test:
            print("SELF_TEST_OK: 4 models, 10 lemma selections, kit and model hashes")
            return
        files = {}
        for variant, expected in BINARY.items():
            supplied = getattr(args, variant)
            if supplied is None:
                parser.error("--baseline and --candidate are required")
            path = supplied.expanduser().resolve()
            if not path.is_file() or not os.access(path, os.X_OK) or sha(path) != expected:
                raise ValueError(f"{variant}_binary_missing_not_executable_or_hash_mismatch: {path}")
            files[variant] = path
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    launch(files)


if __name__ == "__main__":
    if sys.argv[1:] == ["--inside"] and ROOT == Path("/kit"):
        inside()
    else:
        main()
