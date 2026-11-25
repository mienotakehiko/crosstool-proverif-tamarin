#!/usr/bin/env python3
"""Run ProVerif and Tamarin on one generated model set and record every verdict.

    python3 -B run_set.py SETDIR [--out RESULTS] [--pv-timeout 600]
                          [--tm-timeout 3600] [--heap 16g] [--skip-tamarin]
                          [--skip-proverif] [--retry-unresolved] [--tm-jobs FILE]
                          [--tamarin tamarin-prover] [--proverif proverif]

SETDIR contains the files that the generator writes for one Common Iterative
Model: *_PV_*.pv and *_T_*.spthy. The script writes, under RESULTS (default
SETDIR/results):

    pv_results.jsonl   one line per ProVerif query
    tam_results.jsonl  one line per Tamarin lemma
    out/               raw tool output and one memory curve per Tamarin job
    environment.json   host, limits and tool versions

A second call skips the jobs that already have a record, so an interrupted
series resumes where it stopped. With --retry-unresolved, a second call also
repeats the jobs whose last record holds no verdict (time limit, memory limit
or tool error), for example under larger limits; the new records follow the
old ones, and the last record of a job counts. With --tm-jobs FILE, Tamarin
runs only the jobs that FILE lists (one line per job: model, tab, lemma). The
script never changes SETDIR itself.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def tool_version(command):
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60)
        text = (done.stdout + done.stderr).strip().splitlines()
        return " | ".join(line.strip() for line in text[:12] if line.strip())[:900]
    except Exception as error:  # the record keeps the reason
        return f"unavailable: {error}"


def tree_rss_mb(pid):
    """Resident memory of a process and its descendants in MB (Linux)."""
    total, todo, seen = 0, [pid], set()
    while todo:
        current = todo.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            with open(f"/proc/{current}/status") as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        total += int(line.split()[1])
            for task in os.listdir(f"/proc/{current}/task"):
                with open(f"/proc/{current}/task/{task}/children") as handle:
                    todo.extend(int(x) for x in handle.read().split())
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return total // 1024


def run_limited(command, out_path, timeout, mem_path=None, step=5):
    """Run a command in its own process group; return (status, rc, seconds)."""
    start = time.monotonic()
    with open(out_path, "w") as out:
        process = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    samples = []
    stop = threading.Event()

    def sample():
        while not stop.wait(step):
            samples.append((int(time.monotonic() - start), tree_rss_mb(process.pid)))

    watcher = threading.Thread(target=sample, daemon=True)
    if mem_path:
        watcher.start()
    status = "done"
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    stop.set()
    if mem_path:
        with open(mem_path, "w") as handle:
            handle.writelines(f"{t}\t{mb}\n" for t, mb in samples)
    return status, process.returncode, round(time.monotonic() - start, 2), samples


def slope(samples):
    if len(samples) < 2 or samples[-1][0] == samples[0][0]:
        return None
    return round((samples[-1][1] - samples[0][1]) / ((samples[-1][0] - samples[0][0]) / 60), 1)


FINAL = {"true", "false", "cannot", "verified", "falsified"}


def existing(path, keys, retry=False):
    """Keys of the recorded jobs; with retry, only of the jobs whose last record holds a verdict."""
    last = {}
    if os.path.exists(path):
        with open(path) as handle:
            for line in handle:
                if line.strip():
                    record = json.loads(line)
                    last[tuple(record[k] for k in keys)] = record["verdict"]
    return {key for key, verdict in last.items() if not retry or verdict in FINAL}


def run_proverif(args, files, results):
    target = os.path.join(results, "pv_results.jsonl")
    recorded = {model for model, _ in existing(target, ("model", "query"))}
    settled = existing(target, ("model", "query"), args.retry_unresolved)
    for path in files:
        model = os.path.basename(path)[:-3]
        names_here = re.findall(r"^\(\* (\w+) \*\)\nquery", open(path).read(), re.M)
        if model in recorded and (not args.retry_unresolved or all((model, n) in settled for n in names_here)):
            continue
        out = os.path.join(results, "out", model + ".pvout")
        status, rc, seconds, _ = run_limited([args.proverif, path], out, args.pv_timeout)
        text = open(out, errors="replace").read()
        names = re.findall(r"^\(\* (\w+) \*\)\nquery", open(path).read(), re.M)
        found = re.findall(r"^RESULT (.*) (is true|is false|cannot be proved)\.$", text, re.M)
        digest = sha256(path)
        with open(target, "a") as handle:
            if status == "TIMEOUT" or not found:
                verdict = "TIMEOUT" if status == "TIMEOUT" else "ERROR"
                for name in names or ["*"]:
                    handle.write(json.dumps(dict(model=model, query=name, verdict=verdict, rc=rc,
                                                 seconds=seconds, sha256=digest, timeout_s=args.pv_timeout)) + "\n")
            else:
                for index, (_, result) in enumerate(found):
                    verdict = {"is true": "true", "is false": "false", "cannot be proved": "cannot"}[result]
                    name = names[index] if index < len(names) else f"q{index}"
                    handle.write(json.dumps(dict(model=model, query=name, verdict=verdict, rc=rc,
                                                 seconds=seconds, sha256=digest, timeout_s=args.pv_timeout)) + "\n")
        print(f"proverif {model}: {status} rc={rc} {seconds}s", flush=True)


def run_tamarin(args, files, results):
    target = os.path.join(results, "tam_results.jsonl")
    done = existing(target, ("model", "lemma"), args.retry_unresolved)
    only = None
    if args.tm_jobs:
        with open(args.tm_jobs, encoding="utf-8") as handle:
            only = {tuple(line.rstrip("\n").split("\t")[:2]) for line in handle if line.strip() and not line.startswith("#")}
    for path in files:
        model = os.path.basename(path)[:-6]
        lemmas = re.findall(r"^lemma ([A-Za-z0-9_]+)", open(path).read(), re.M)
        digest = sha256(path)
        for lemma in lemmas:
            if (model, lemma) in done or (only is not None and (model, lemma) not in only):
                continue
            base = os.path.join(results, "out", f"{model}__{lemma}")
            command = [args.tamarin, f"--prove={lemma}", path, "+RTS", f"-M{args.heap}", "-RTS"]
            # one memory sample every five seconds, more often under a short time limit
            status, rc, seconds, samples = run_limited(command, base + ".out", args.tm_timeout, base + ".mem",
                                                       step=max(1, min(5, args.tm_timeout // 20)))
            text = open(base + ".out", errors="replace").read()
            line = re.search(rf"^\s*{re.escape(lemma)} \((all-traces|exists-trace)\): (.*)$", text, re.M)
            raw = line.group(0).strip() if line else ""
            if status == "TIMEOUT":
                verdict = "TIMEOUT"
            elif "Heap exhausted" in text or rc == 251:
                verdict = "HEAP"
            elif rc in (137, -9):
                verdict = "KILLED"
            elif line and line.group(2).startswith("verified"):
                verdict = "verified"
            elif line and line.group(2).startswith("falsified"):
                verdict = "falsified"
            else:
                verdict = "ERROR"
            steps = re.search(r"\((\d+) steps\)", raw)
            count = len(samples)
            record = dict(model=model, lemma=lemma, verdict=verdict, rc=rc, seconds=seconds, raw=raw,
                          quantifier=line.group(1) if line else None,
                          steps=int(steps.group(1)) if steps else None, heap_cap=args.heap,
                          timeout_s=args.tm_timeout, sha256=digest,
                          rss_max_mb=max((mb for _, mb in samples), default=None),
                          rss_growth_early_mb_per_min=slope(samples[:max(2, int(0.3 * count))]) if count >= 4 else None,
                          rss_growth_late_mb_per_min=slope(samples[int(0.7 * count):]) if count >= 4 else None)
            with open(target, "a") as handle:
                handle.write(json.dumps(record) + "\n")
            print(f"tamarin {model} {lemma}: {verdict} rc={rc} {seconds}s", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("setdir")
    parser.add_argument("--out")
    parser.add_argument("--pv-timeout", type=int, default=600)
    parser.add_argument("--tm-timeout", type=int, default=3600)
    parser.add_argument("--heap", default="16g")
    parser.add_argument("--proverif", default="proverif")
    parser.add_argument("--tamarin", default="tamarin-prover")
    parser.add_argument("--skip-tamarin", action="store_true")
    parser.add_argument("--skip-proverif", action="store_true")
    parser.add_argument("--retry-unresolved", action="store_true")
    parser.add_argument("--tm-jobs", help="file with the Tamarin jobs to run: model, tab, lemma")
    args = parser.parse_args()
    for tool, skipped in ((args.proverif, args.skip_proverif), (args.tamarin, args.skip_tamarin)):
        if not skipped and shutil.which(tool) is None:
            print(f"run_set.py: {tool} not found; put it on the PATH, name it with --proverif or --tamarin, "
                  f"or skip the tool", file=sys.stderr)
            return 2
    results = args.out or os.path.join(args.setdir, "results")
    os.makedirs(os.path.join(results, "out"), exist_ok=True)
    names = sorted(os.listdir(args.setdir))
    pv_files = [os.path.join(args.setdir, n) for n in names if n.endswith(".pv")]
    tm_files = [os.path.join(args.setdir, n) for n in names if n.endswith(".spthy")]
    memory = ""
    try:
        with open("/proc/meminfo") as handle:
            memory = handle.readline().strip()
    except OSError:
        pass
    environment = dict(
        date_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), host=platform.node(),
        system=platform.platform(), processors=os.cpu_count(), memory=memory,
        proverif=tool_version([args.proverif, "-help"]), tamarin=tool_version([args.tamarin, "--version"]),
        limits=dict(pv_timeout_s=args.pv_timeout, tm_timeout_s=args.tm_timeout, heap=args.heap),
        script_sha256=sha256(os.path.abspath(__file__)))
    with open(os.path.join(results, "environment.json"), "w") as handle:
        json.dump(environment, handle, indent=1)
    if not args.skip_proverif:
        run_proverif(args, pv_files, results)
    if not args.skip_tamarin:
        run_tamarin(args, tm_files, results)


if __name__ == "__main__":
    sys.exit(main())
