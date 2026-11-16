"""Pinned-image execution, with artifact evaluator reconstruction preserved."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from common import dump, pv_reach, pv_results, run, sha, tm_verdict
from generate import LEMMAS

PINS = {"TAMARIN_COMMIT": "c293106913ccf7bb41f49b0dc555a8074e8ea88c",
        "PROVERIF_COMMIT": "1d4cd9458d9ccf648e149ec2ea5147b2c87b67df"}


def verify(kit, out, artifact=Path("/opt/eval")):
    actual = {k: (artifact / k).read_text().strip() for k in PINS}
    dump(out / "commits.json", actual)
    if actual != PINS:
        raise RuntimeError("commit_mismatch")
    checks = []
    for line in (kit / "tool_sha256_expected.txt").read_text().splitlines():
        expected, path = line.split()
        actual_hash = sha(path)
        checks.append({"path": path, "expected": expected, "actual": actual_hash})
    dump(out / "tool_checks.json", checks)
    if any(x["actual"] != x["expected"] for x in checks):
        raise RuntimeError("tool_hash_mismatch")


def evaluate(kit, out, evaluator):
    rows = []
    for case in json.loads((kit / "cases.json").read_text()):
        cid = case["id"]
        for lemma in LEMMAS:
            folder = out / cid / lemma
            folder.mkdir(parents=True)
            model = kit / "models" / (cid + ".spthy")
            translated = folder / "translated.pv"
            native_meta = run(folder, "native", ["tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS",
                                                  "-d=0", "--prove=" + lemma, str(model)], 60)
            native = tm_verdict((folder / "native.stdout.txt").read_text(), lemma, native_meta["rc"])
            export_meta = run(folder, "export", ["tamarin-prover", "+RTS", "-N1", "-M768m", "-RTS",
                                                  "-d=0", "-m=proverif", "--lemma=" + lemma,
                                                  "-o=" + str(translated), str(model)], 60)
            row = {"case": cid, "lemma": lemma, "native": native, "native_rc": native_meta["rc"],
                   "export_rc": export_meta["rc"], "translated": "not_run", "pv_raw": [],
                   "status": "REVIEW", "detail": "export_incomplete"}
            if export_meta["rc"] == 0 and translated.is_file() and translated.stat().st_size:
                body = translated.read_text(errors="replace")
                row["translated_sha256"] = sha(translated)
                row["translation_flags"] = evaluator.extract_translation_flags(body)
                # Preserve all flags and raw text; do not patch the translation.
                markers = [s for s in ("Restriction translation failed", "Restriction has negated event",
                                       "Axiom translation failed", "Axiom has negated event") if s in body]
                row["translation_warnings"] = markers
                meta = run(folder, "translated", ["proverif", str(translated)], 60)
                text = (folder / "translated.stdout.txt").read_text(errors="replace")
                row["translated_rc"] = meta["rc"]
                row["pv_raw"] = pv_results(text, meta["rc"])
                value, note = evaluator.reconstruct_proverif_result(body, text)
                row["evaluator_note"] = note
                row["evaluator_value"] = value
                labels = ("holds", "violated") if lemma == "single_consumption" else ("reachable", "unreachable")
                reach = labels[0] if value is True else labels[1] if value is False else "unknown"
                row["translated"] = reach if meta["rc"] == 0 else "unknown"
                flags = row["translation_flags"]
                review = markers or flags.get("timepoints_split") or flags.get("restriction_missing") or flags.get("axiom_missing")
                if (native_meta["rc"] or meta["rc"] or review or native == "unknown"
                        or row["translated"] == "unknown" or not row["pv_raw"]):
                    row["detail"] = "incomplete_or_translation_warning"
                else:
                    row["status"] = "MATCH" if native == reach else "DIFFERENT"
                    row["detail"] = "per_lemma_comparison_only"
            rows.append(row)
            dump(out / "summary.json", rows)
    return rows


def main():
    kit, out = map(Path, sys.argv[1:])
    status = {"mode": "pinned", "complete": False}
    dump(out / "summary.json", [])
    try:
        verify(kit, out)
        spec = importlib.util.spec_from_file_location("ccs26_eval", "/opt/eval/eval.py")
        evaluator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluator)
        rows = evaluate(kit, out, evaluator)
        status["complete"] = len(rows) == 16
        status["review_rows"] = sum(r["status"] == "REVIEW" for r in rows)
        if status["review_rows"]:
            raise RuntimeError("review_rows_present")
    except Exception as exc:
        status["error"] = repr(exc)
        raise
    finally:
        dump(out / "inside_status.json", status)


if __name__ == "__main__":
    main()
