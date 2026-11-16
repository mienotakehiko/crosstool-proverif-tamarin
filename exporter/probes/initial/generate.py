"""Generate both finite reference paths from one explicit case table."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEMMAS = ("honest_reachable", "bad_reachable", "repeat_reachable", "single_consumption")


def render(case):
    def tm(q):
        return "'%s'" % q if case["encoding"] == "constant" else "%s('tag_seed')" % q

    def pv(q):
        return q if case["encoding"] == "constant" else "%s(tag_seed)" % q

    init, good, bad = (case[k] for k in ("initial", "allowed", "prohibited"))
    declarations = "functions: q0/1, q1/1\n" if case["encoding"] == "constructor" else ""
    second = tm(good) if case["repeat"] else "'qdone'"
    # One initialization per trace, finite phase index, no attacker interfaces.
    source = f"""theory {case['id']} begin
{declarations}
rule Init:
  [ Fr(~sid) ] --[ InitOnce() ]-> [ St(~sid, {tm(init)}, 'phase0') ]
restriction OneInit:
  "All #i #j. InitOnce() @ i & InitOnce() @ j ==> #i = #j"
rule Good:
  [ St(sid, {tm(good)}, 'phase0') ] --[ Honest(sid) ]-> [ St(sid, {second}, 'phase1') ]
rule Bad:
  [ St(sid, {tm(bad)}, 'phase0') ] --[ Bad(sid) ]-> []
rule Again:
  [ St(sid, {tm(good)}, 'phase1') ] --[ Again(sid) ]-> []
lemma honest_reachable: exists-trace
  "Ex sid #i. Honest(sid) @ i"
lemma bad_reachable: exists-trace
  "Ex sid #i. Bad(sid) @ i"
lemma repeat_reachable: exists-trace
  "Ex sid #i. Again(sid) @ i"
lemma single_consumption: all-traces
  "All sid #i #j. Honest(sid) @ i & Honest(sid) @ j ==> #i = #j"
end
"""
    decl = ("free q0, q1, qdone: bitstring.\n" if case["encoding"] == "constant"
            else "free tag_seed, qdone: bitstring.\nfun q0(bitstring): bitstring.\nfun q1(bitstring): bitstring.\n")
    # Private one-shot channel represents consumption, not a persistent PV table.
    nxt = pv(good) if case["repeat"] else "qdone"
    direct = f"""{decl}event Seed(bitstring).
event Honest(bitstring).
event Bad.
event Again.
query sid: bitstring; event(Honest(sid)).
query event(Bad).
query event(Again).
query sid: bitstring; inj-event(Honest(sid)) ==> inj-event(Seed(sid)).
process
  new state: channel;
  new sid: bitstring;
  event Seed(sid);
  (out(state, {pv(init)}) |
   in(state, z: bitstring);
   (if z = {pv(good)} then (
      event Honest(sid);
      let next = {nxt} in
      if next = {pv(good)} then event Again)
    else if z = {pv(bad)} then event Bad))
"""
    return source, direct


def main():
    target = ROOT / "models"
    target.mkdir(exist_ok=True)
    for case in json.loads((ROOT / "cases.json").read_text()):
        tm, pv = render(case)
        (target / (case["id"] + ".spthy")).write_text(tm, encoding="ascii")
        (target / (case["id"] + ".pv")).write_text(pv, encoding="ascii")


if __name__ == "__main__":
    main()
