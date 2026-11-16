"""Exploratory native Tamarin and direct PV only; never a pinned export."""
import json
from pathlib import Path
import shutil
import tempfile
from common import dump, pv_verdict, pv_results, run, sha, tm_verdict
from generate import LEMMAS, ROOT


def main():
    base = ROOT / "local_runs"
    base.mkdir(exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="local_", dir=base))
    tools = {}
    for name, flag in (("tamarin-prover", "--version"), ("proverif", "-help"), ("maude", "--version")):
        path = shutil.which(name)
        tools[name] = {"path": path, "sha256": sha(path) if path else None}
        command = [name, "+RTS", "-N1", "-M256m", "-RTS", flag] if name == "tamarin-prover" else [name, flag]
        run(out, name + "_version", command, 20, 512)
    dump(out / "tools.json", tools)
    rows = []
    for case in json.loads((ROOT / "cases.json").read_text()):
        cid = case["id"]
        folder = out / cid
        folder.mkdir()
        for ext in ("spthy", "pv"):
            shutil.copy2(ROOT / "models" / (cid + "." + ext), folder)
        tm = folder / (cid + ".spthy")
        pv = folder / (cid + ".pv")
        record = run(folder, "direct", ["proverif", str(pv)], 20, 512)
        raw = pv_results((folder / "direct.stdout.txt").read_text(), record["rc"])
        for i, lemma in enumerate(LEMMAS):
            meta = run(folder, lemma, ["tamarin-prover", "+RTS", "-N1", "-M256m", "-RTS",
                                      "-d=0", "--prove=" + lemma, str(tm)], 20, 512)
            native = tm_verdict((folder / (lemma + ".stdout.txt")).read_text(), lemma, meta["rc"])
            expected = "holds" if i == 3 else "reachable" if i == 0 or (i == 2 and case["repeat"]) else "unreachable"
            direct = pv_verdict(raw[i], lemma) if len(raw) == 4 else "unknown"
            rows.append({"case": cid, "lemma": lemma, "expected": expected, "native": native,
                         "direct": direct, "native_rc": meta["rc"], "direct_rc": record["rc"],
                         "pv_raw": raw[i] if len(raw) == 4 else raw,
                         "status": "MATCH" if native == direct == expected else "REVIEW"})
    dump(out / "summary.json", rows)
    dump(out / "input_hashes.json", {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.suffix in (".spthy", ".pv")})
    print(out)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
