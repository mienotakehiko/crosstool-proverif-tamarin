"""Compare two H1 RB3 diagnostic variants with the fixed CCS 2026 tools."""

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
VARIANTS = ("action_order", "equality_guard")
REFERENCE = {
    "rb3_same_reuse_reachable": ("false", "same_reachability"),
    "rb3_same_own_reachable": ("false", "same_reachability"),
    "rb3_different_own_reachable": ("false", "reachability_with_context_inequality"),
    "rb3_accepted_matches_protected": ("true", "event_binding"),
    "rb3_reuse_requires_same": ("true", "context_equality_and_no_piv"),
    "rb3_own_uses_sender_ssn": ("true", "sender_ssn_correspondence"),
}
REACHABILITY = {
    "rb3_same_reuse_reachable": ("same_ctx", "reuse_piv"),
    "rb3_same_own_reachable": ("same_ctx", "own_piv"),
    "rb3_different_own_reachable": ("different_ctx", "own_piv"),
}


def reachability_witness(log, lemma):
    if "A trace has been found." not in log:
        return False
    scenario, mode = REACHABILITY[lemma]
    for line in re.findall(r"^event eResponseAccepted\(([^()]*)\) at ", log, re.MULTILINE):
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 8:
            continue
        label, _, _, request_ctx, response_ctx, _, piv_mode, reply_piv = fields
        if (label.removeprefix("v"), piv_mode.removeprefix("v")) != (scenario, mode):
            continue
        if (request_ctx == response_ctx) != (scenario == "same_ctx"):
            continue
        if (reply_piv.removeprefix("v") == "no_piv") == (mode == "reuse_piv"):
            return True
    return False


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

def evaluate(official, theory, variant, lemma):
    folder = ROOT / variant / lemma
    folder.mkdir(parents=True)
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
    context_match_first = None
    if export == 0 and model.is_file() and model.stat().st_size:
        body = model.read_text(errors="replace")
        pv_code = capture(folder, "proverif", ["proverif", str(model)])
        log = (folder / "proverif.stdout.txt").read_text(errors="replace")
        translated, diagnostic = official.reconstruct_proverif_result(body, log)
        flags = official.extract_translation_flags(body)
        reuse_rule = re.search(r"(?ms)^let rProtectWithRequestNonce\s*=.*?(?=^let |\Z)", body)
        if reuse_rule:
            protected = reuse_rule[0].find("event eResponseProtected(")
            matched = reuse_rule[0].find("event eContextMatch(")
            if min(protected, matched) >= 0:
                context_match_first = matched < protected
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
        "variant": variant, "lemma": lemma, "cim_pv_archived_raw": raw,
        "cim_reference": reference, "tamarin_retest": original,
        "pv_from_tamarin": translated, "pv_diagnostic": diagnostic,
        "exit_codes": {"tamarin": tm, "export": export, "proverif": pv_code},
        "translation_flags": flags, "context_match_before_protection": context_match_first,
        "status": status,
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

    with (ROOT / "rb3_tool_comparison.txt").open("wb") as out:
        comparison = subprocess.run(
            ["sha256sum", "-c", str(ROOT / "inputs/rb3_tool_sha256.txt")],
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
        raise SystemExit("The archived RB3 baseline does not match.")
    results = [
        evaluate(official, inputs / f"rb3_{variant}.spthy", variant, lemma)
        for variant in VARIANTS
        for lemma in REFERENCE
    ]
    (ROOT / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    columns = ["variant", "lemma", "tamarin_retest", "pv_from_tamarin",
               "context_match_before_protection", "status"]
    with (ROOT / "summary.tsv").open("w") as out:
        out.write("\t".join(columns) + "\n")
        for row in results:
            out.write("\t".join(str(row[key]) for key in columns) + "\n")

if __name__ == "__main__":
    main()
