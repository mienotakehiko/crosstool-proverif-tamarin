"""Run the H1 RB5 model through the fixed CCS 2026 export path."""

import importlib.util
import json
import re
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
ARTIFACT = Path("/opt/eval")
PINS = {
    "TAMARIN_COMMIT": "c293106913ccf7bb41f49b0dc555a8074e8ea88c",
    "PROVERIF_COMMIT": "1d4cd9458d9ccf648e149ec2ea5147b2c87b67df",
}
REFERENCE = {
    "rb5_block_reachable": ("false", "same_reachability"),
    "rb5_send_while_active_unreachable": ("true", "same_unreachability"),
    "rb5_commit_send_reachable": ("false", "same_reachability"),
    "rb5_commit_before_send": ("true", "commit_correspondence"),
    "rb5_abort_send_reachable": ("false", "same_reachability"),
    "rb5_abort_before_send": ("true", "abort_correspondence"),
}
REACHABILITY = {
    "rb5_block_reachable": (
        ("KudosStart", ()),
        ("AppSendChecked", ("phase_active", "no_outcome")),
        ("AppSendBlocked", ()),
    ),
    "rb5_commit_send_reachable": (
        ("KudosStart", ()),
        ("KudosCommit", ()),
        ("AppSendChecked", ("phase_closed", "outcome_commit")),
        ("AppSend", ("phase_closed", "outcome_commit")),
    ),
    "rb5_abort_send_reachable": (
        ("KudosStart", ()),
        ("KudosAbort", ()),
        ("AppSendChecked", ("phase_closed", "outcome_abort")),
        ("AppSend", ("phase_closed", "outcome_abort")),
    ),
}


def reachability_witness(log, lemma):
    if "A trace has been found." not in log:
        return False
    events = re.findall(
        r"^event e(KudosStart|KudosCommit|KudosAbort|AppSendChecked|AppSendBlocked|AppSend)\(([^()]*)\) at \{",
        log, re.MULTILINE)
    expected = REACHABILITY[lemma]
    if len(events) != len(expected):
        return False
    sid = events[0][1].strip()
    for (name, arguments), (expected_name, constants) in zip(events, expected, strict=True):
        fields = [field.strip() for field in arguments.split(",")]
        if name != expected_name or fields[0] != sid:
            return False
        if tuple(field.removeprefix("v") for field in fields[1:]) != constants:
            return False
    return True


def capture(folder, label, command):
    (folder / f"{label}.command.json").write_text(json.dumps(command) + "\n")
    timed = ["/usr/bin/time", "-o", str(folder / f"{label}.time.txt"),
             "-f", "wall_seconds=%e\nmax_rss_kib=%M",
             "timeout", "-k", "1s", "60s", *command]
    with (folder / f"{label}.stdout.txt").open("wb") as out, (
        folder / f"{label}.stderr.txt"
    ).open("wb") as err:
        code = subprocess.run(timed, stdout=out, stderr=err, check=False).returncode
    (folder / f"{label}.exit_code.txt").write_text(f"{code}\n")
    return code

def evaluate(official, theory, lemma):
    folder = ROOT / lemma
    folder.mkdir()
    model = folder / "translated.pv"
    tm = capture(folder, "tamarin", [
        "tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS", "-d=0",
        f"--prove={lemma}", str(theory),
    ])
    original = official.parse_tamarin_results(
        (folder / "tamarin.stdout.txt").read_text(errors="replace")
    ).get(lemma)
    export = capture(folder, "export", [
        "tamarin-prover", "-d=0", "-m=proverif", f"--lemma={lemma}",
        f"-o={model}", str(theory),
    ])
    pv_code, translated, diagnostic, flags = None, None, None, {}
    raw_translated = []
    if export == 0 and model.is_file() and model.stat().st_size:
        body = model.read_text(errors="replace")
        pv_code = capture(folder, "proverif", ["proverif", str(model)])
        log = (folder / "proverif.stdout.txt").read_text(errors="replace")
        translated, diagnostic = official.reconstruct_proverif_result(body, log)
        raw_translated = re.findall(r"^RESULT .*? (true|false|cannot be proved)\.$",
                                    log, re.MULTILINE)
        flags = official.extract_translation_flags(body)
        flags["restriction_missing"] = any(marker in body for marker in (
            "Restriction translation failed", "Restriction has negated event"))
        flags["axiom_missing"] = any(marker in body for marker in (
            "Axiom translation failed", "Axiom has negated event"))

    if lemma in REACHABILITY and translated is True:
        flags["reachability_trace_present"] = reachability_witness(log, lemma)

    missing_trace = flags.get("reachability_trace_present") is False
    incomplete = missing_trace or any(flags.get(k, False) for k in (
        "restriction_missing", "axiom_missing", "timepoints_split"))
    if tm == 0 and export == 0 and pv_code == 0 and not incomplete:
        if original is True and translated is True:
            status = "MATCH"
        elif isinstance(original, bool) and isinstance(translated, bool):
            status = "DIFFERENT"
        else:
            status = "REVIEW"
    else:
        status = "REVIEW"
    raw, reference = REFERENCE[lemma]
    return {
        "lemma": lemma, "cim_pv_archived_raw": raw,
        "cim_reference": reference, "tamarin_retest": original,
        "pv_from_tamarin": translated, "translated_pv_raw": raw_translated,
        "pv_diagnostic": diagnostic,
        "exit_codes": {"tamarin": tm, "export": export, "proverif": pv_code},
        "translation_flags": flags, "status": status,
    }

def main():
    pins = {key: (ARTIFACT / key).read_text().strip() for key in PINS}
    (ROOT / "commits.json").write_text(json.dumps(pins, indent=2) + "\n")
    if pins != PINS:
        raise SystemExit("CCS 2026 source commits do not match the expected revisions.")
    tools = [shutil.which(name) for name in ("tamarin-prover", "proverif", "maude")]
    if any(path is None for path in tools):
        raise SystemExit("The image is missing an expected executable.")
    with (ROOT / "tool_sha256.txt").open("wb") as out:
        subprocess.run(["sha256sum", *tools, str(ARTIFACT / "eval.py")], stdout=out, check=True)

    with (ROOT / "rb4_tool_comparison.txt").open("wb") as out:
        comparison = subprocess.run(
            ["sha256sum", "-c", str(ROOT / "inputs/rb4_tool_sha256.txt")],
            stdout=out, stderr=subprocess.STDOUT, check=False)
    if comparison.returncode:
        print("TOOL_HASHES=DIFFERENT", flush=True)
    spec = importlib.util.spec_from_file_location("ccs26_eval", ARTIFACT / "eval.py")
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)

    inputs = ROOT / "inputs"
    baseline = json.loads((inputs / "cim_comparison.json").read_text())
    pv_log = (inputs / "cim_pv_stdout.txt").read_text()
    raw_pv = re.findall(r"^RESULT .* is (true|false)\.$", pv_log, re.MULTILINE)
    tm_log = (inputs / "cim_tm_stdout.txt").read_text()
    if (baseline["pass"] is not True or
            baseline["proverif_verdicts"] != raw_pv or
            raw_pv != [raw for raw, _ in REFERENCE.values()] or
            official.parse_tamarin_results(tm_log) != dict.fromkeys(REFERENCE, True)):
        raise SystemExit("The archived RB5 baseline does not match.")
    results = [evaluate(official, inputs / "rb5.spthy", lemma) for lemma in REFERENCE]
    (ROOT / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    columns = ["lemma", "cim_pv_archived_raw", "cim_reference", "tamarin_retest", "pv_from_tamarin", "status"]
    with (ROOT / "summary.tsv").open("w") as out:
        out.write("\t".join(columns) + "\n")
        for row in results:
            out.write("\t".join(str(row[key]) for key in columns) + "\n")

if __name__ == "__main__":
    main()
