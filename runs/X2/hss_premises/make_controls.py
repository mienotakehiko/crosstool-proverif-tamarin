from pathlib import Path
import hashlib
import sys

src, prior_runner, run = map(Path, sys.argv[1:])
controls = run / "controls"

def block(text, start, end):
    start += "\n"
    end += "\n"
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"Heading check failed for {start.strip()}")
    first = text.index(start)
    last = text.index(end)
    if first >= last:
        raise SystemExit("The section order of the generated ProVerif file differs from the expected order")
    return text[first:last]

records = []
for lemma in ("exec", "LS7"):
    def candidate(model):
        path = src / "results" / model / lemma / "candidate" / "translated.pv"
        return path.read_bytes().decode("utf-8")

    noinj, inj = candidate("hss_noinj"), candidate("hss_inj")
    dginj = block(inj, "(* DgInj *)", "(* DistinctFact *)")
    topauth = block(inj, "(* Axioms from reuse/source lemmas *)", "(* Queries *)")
    if inj.replace(dginj, "", 1).replace(topauth, "", 1) != noinj:
        raise SystemExit(f"{lemma} differs in more than the two premises")

    for variant, term, anchor in (
        ("dginj_only", dginj, "(* DistinctFact *)"),
        ("topauth_only", topauth, "(* Queries *)"),
    ):
        if noinj.count(anchor) != 1:
            raise SystemExit(f"{lemma} has no unique insertion point")
        dest = controls / "results" / "hss_noinj" / lemma / variant / "translated.pv"
        dest.parent.mkdir(parents=True)
        body = noinj.replace(anchor, term + anchor, 1).encode("utf-8")
        dest.write_bytes(body)
        records.append(f"{hashlib.sha256(body).hexdigest()}  {dest.relative_to(run)}")

runner = prior_runner.read_text(encoding="utf-8")
for old, new in (
    ("for variant in baseline candidate; do",
     "for variant in dginj_only topauth_only; do"),
    ("^timeout: sending signal", "^([^ ]*/)?timeout: sending signal"),
):
    if runner.count(old) != 1:
        raise SystemExit(f"Check of the previous script failed for {old}")
    runner = runner.replace(old, new, 1)

(run / "run_controls.sh").write_text(runner, encoding="utf-8")
(run / "controls.sha256").write_text("\n".join(records) + "\n", encoding="utf-8")
print("The difference check passed. Wrote four diagnostic ProVerif files.")
