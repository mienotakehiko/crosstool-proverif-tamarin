"""Bounded subprocess execution and conservative verdict handling."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(folder, phase, command, seconds, memory_mb=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dump(folder / (phase + ".command.json"), command)
    start = time.monotonic()
    timed_out = False
    code = 127
    def limits():
        if memory_mb:
            cap = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with (folder / (phase + ".stdout.txt")).open("wb") as out, (folder / (phase + ".stderr.txt")).open("wb") as err:
        try:
            process = subprocess.Popen(command, stdout=out, stderr=err,
                                       start_new_session=True, preexec_fn=limits)
            try:
                code = process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    pass
                # Also kill descendants after a group leader has exited.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                code = 124
            except BaseException:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise
        except OSError as exc:
            err.write((repr(exc) + "\n").encode())
    record = {"rc": code, "timeout": timed_out, "wall_seconds": time.monotonic() - start,
              "limit_seconds": seconds, "address_space_mb": memory_mb}
    dump(folder / (phase + ".meta.json"), record)
    (folder / (phase + ".exit_code.txt")).write_text(str(code) + "\n")
    return record


def tm_verdict(text, lemma, rc):
    if rc != 0:
        return "unknown"
    match = re.search(r"^\s*" + re.escape(lemma) + r"\s+\((exists-trace|all-traces)\):\s+(verified|falsified)\b", text, re.M)
    if not match:
        return "unknown"
    labels = {"verified": "holds", "falsified": "violated"} if match[1] == "all-traces" else {"verified": "reachable", "falsified": "unreachable"}
    return labels[match[2]]


def pv_results(text, rc):
    if rc:
        return []
    return re.findall(r"^RESULT .*? (true|false|cannot be proved)\.$", text, re.M)


def pv_reach(raw):
    # PV event queries assert absence; false is a reconstructed witness.
    return {"true": "unreachable", "false": "reachable"}.get(raw, "unknown")


def pv_verdict(raw, lemma):
    if lemma == "single_consumption":
        return {"true": "holds", "false": "violated"}.get(raw, "unknown")
    return pv_reach(raw)
