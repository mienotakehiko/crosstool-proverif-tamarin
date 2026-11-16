"""Run the two H1 RB1 schedules through the fixed CCS 2026 export path."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
ARTIFACT = Path("/opt/eval")
PINS = {
    "TAMARIN_COMMIT": "c293106913ccf7bb41f49b0dc555a8074e8ea88c",
    "PROVERIF_COMMIT": "1d4cd9458d9ccf648e149ec2ea5147b2c87b67df",
}
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

def evaluate(official, theory, case, lemma, expected):
    folder = ROOT / case / lemma
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
    if export == 0 and model.is_file() and model.stat().st_size:
        body = model.read_text(errors="replace")
        pv_code = capture(folder, "proverif", ["proverif", str(model)])
        log = (folder / "proverif.stdout.txt").read_text(errors="replace")
        translated, diagnostic = official.reconstruct_proverif_result(body, log)
        flags = official.extract_translation_flags(body)
        flags["restriction_missing"] = any(marker in body for marker in (
            "Restriction translation failed", "Restriction has negated event"))
        flags["axiom_missing"] = any(marker in body for marker in (
            "Axiom translation failed", "Axiom has negated event"))

    if lemma == "normal" and translated is True:
        flags["reachability_trace_present"] = (
            "A trace has been found." in log and
            any(line.startswith("event eNormal") for line in log.splitlines()))

    missing_trace = flags.get("reachability_trace_present") is False
    incomplete = missing_trace or any(flags.get(k, False) for k in (
        "restriction_missing", "axiom_missing", "timepoints_split"))
    if tm == 0 and export == 0 and pv_code == 0 and not incomplete:
        if original is expected and translated is expected:
            status = "MATCH"
        elif isinstance(original, bool) and isinstance(translated, bool):
            status = "DIFFERENT"
        else:
            status = "REVIEW"
    else:
        status = "REVIEW"
    return {
        "case": case, "lemma": lemma, "cim_pv_archived_raw": "false" if lemma == "normal" else "true",
        "cim_reference": "inverse_no_collision" if lemma == "collision" else "direct",
        "expected": expected, "tamarin_retest": original,
        "pv_from_tamarin": translated, "pv_diagnostic": diagnostic,
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

    with (ROOT / "h2_tool_comparison.txt").open("wb") as out:
        comparison = subprocess.run(
            ["sha256sum", "-c", str(ROOT / "inputs/h2_tool_sha256.txt")],
            stdout=out, stderr=subprocess.STDOUT, check=False)
    if comparison.returncode:
        print("TOOL_HASHES=DIFFERENT", flush=True)
    spec = importlib.util.spec_from_file_location("ccs26_eval", ARTIFACT / "eval.py")
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)

    cases = json.loads((ROOT / "inputs/cases.json").read_text())
    results = []
    for definition in cases:
        case = definition["case"]
        folder = ROOT / "inputs" / case
        proof = (folder / "cim_pv_stdout.txt").read_text()
        pv_baseline = official.parse_proverif_results(proof)
        tm_baseline = official.parse_tamarin_results((folder / "cim_tm_stdout.txt").read_text())
        expected = definition["expected"]
        if len(pv_baseline) != 2 or not all(value is True for value in pv_baseline.values()):
            raise SystemExit(f"The archived {case} ProVerif baseline does not match.")
        if tm_baseline != expected:
            raise SystemExit(f"The archived {case} Tamarin baseline does not match.")
        theory = folder / (case + ".spthy")
        results.extend(evaluate(official, theory, case, lemma, verdict)
                       for lemma, verdict in expected.items())
    (ROOT / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    columns = ["case", "lemma", "cim_reference", "expected", "tamarin_retest", "pv_from_tamarin", "status"]
    with (ROOT / "summary.tsv").open("w") as out:
        out.write("\t".join(columns) + "\n")
        for row in results:
            out.write("\t".join(str(row[key]) for key in columns) + "\n")

if __name__ == "__main__":
    main()
