#!/usr/bin/env python3
"""Generate the stage 2 LMS models.

Parameters: tree height h = 1 (leaves z and s(z)); LM-OTS with w = 2 and
p = 2 (one message chain 'm' and one checksum chain 'k') at every leaf.
The three variants share one rule set and differ only in how the signer
state may evolve:
  base      the leaf index q is a linear fact and only moves forwards;
  rollback  any earlier snapshot of the state can be restored;
  clone     the current state can be duplicated.
"""

N = {0: 'z', 1: 's(z)', 2: 's(s(z))', 3: 's(s(s(z)))'}
LEAVES = ['z', 's(z)']


def up(n, d, x, i='I'):
    """Term for n hash steps on chain d, starting from x."""
    t = x
    for _ in range(n):
        t = f"ch({i},'{d}',{t})"
    return t


def leaf_pk(q, i, sd):
    return (f"<{up(3, 'm', f'prf({sd},{q},{chr(39)}m{chr(39)})', i)}, "
            f"{up(3, 'k', f'prf({sd},{q},{chr(39)}k{chr(39)})', i)}>")


def model(variant):
    out = []
    w = out.append
    w(f"theory LMS_S2_{variant}")
    w("/*")
    w(" * Stage 2: LMS with tree height h = 1 (leaves z and s(z)) and LM-OTS")
    w(" * with w = 2 and p = 2 at every leaf. The OTS secret values are derived")
    w(" * from one seed with the private function prf, in the spirit of")
    w(" * RFC 8554, Appendix A. The hash chains are written in closed form")
    w(" * because w is fixed; the chain loops were studied in stage 1.")
    w(" * The signer state holds the next unused leaf index q.")
    w(f" * Variant: {variant}.")
    w(" */")
    w("begin")
    w("functions: ch/3, prf/3 [private], hl/3, s/1, z/0")
    w('restriction Cks: "All a c #i. Cks(a,c)@i ==>')
    w("    (a = z & c = s(s(s(z)))) | (a = s(z) & c = s(s(z)))")
    w('  | (a = s(s(z)) & c = s(z)) | (a = s(s(s(z))) & c = z)"')
    w("")
    root = f"hl(~I, {leaf_pk('z', '~I', '~sd')}, {leaf_pk('s(z)', '~I', '~sd')})"
    w("rule KeyGen:")
    w("  [ Fr(~I), Fr(~sd) ]")
    w("  --[ KeyGen(~I) ]->")
    w(f"  [ !Sk(~I,~sd), St(~I,z), !Snap(~I,z), !Root(~I, {root}),")
    w(f"    Out(<~I, {root}>) ]")
    w("")
    w("// Signing consumes the state at leaf q and stores q + 1. There is one")
    w("// rule per leaf and message digit; the checksum digit is 3 - a.")
    for qi, q in enumerate(LEAVES):
        sib = leaf_pk(LEAVES[1 - qi], 'I', 'sd')
        for a in range(4):
            c = 3 - a
            sm = up(a, 'm', f"prf(sd,{q},'m')")
            sk = up(c, 'k', f"prf(sd,{q},'k')")
            w(f"rule Sign_q{qi}_a{a}:")
            w(f"  [ St(I,{q}), !Sk(I,sd), In(<'sign',{N[a]}>) ]")
            w(f"  --[ Cks({N[a]},{N[c]}), Sign(I,{q},{N[a]}), UseLeaf(I,{q}) ]->")
            w(f"  [ St(I,s({q})), !Snap(I,s({q})),")
            w(f"    Out(<I,{q},{N[a]},{sm},{sk},{sib}>) ]")
    w("")
    if variant in ('rollback', 'clone'):
        w("// Bound the misuse to one event per key. One event is enough for the")
        w("// attacks of interest, and without the bound the backward search can")
        w("// restore or copy the state without end.")
        w('restriction OneMisuse: "All I #i #j. Misuse(I)@i & Misuse(I)@j ==> #i = #j"')
        w("")
    if variant == 'rollback':
        w("// Restore any earlier snapshot of the signer state.")
        w("rule Rollback:")
        w("  [ St(I,q), !Snap(I,q0) ] --[ Misuse(I), Rollback(I,q,q0) ]-> [ St(I,q0) ]")
        w("")
    if variant == 'clone':
        w("// Duplicate the current signer state (for example, a copied VM image).")
        w("rule Clone:")
        w("  [ St(I,q) ] --[ Misuse(I), Clone(I,q) ]-> [ St(I,q), St(I,q) ]")
        w("")
    w("rule RevealSeed:")
    w("  [ !Sk(I,sd) ] --[ RevealSeed(I) ]-> [ Out(sd) ]")
    w("")
    w("// Verification hashes both values up to the top of their chains,")
    w("// combines the result with the authentication path and compares it")
    w("// with the stored root.")
    for qi, q in enumerate(LEAVES):
        for a in range(4):
            c = 3 - a
            pkc = f"<{up(3 - a, 'm', 'sm')}, {up(3 - c, 'k', 'sk')}>"
            r = f"hl(I, {pkc}, sib)" if qi == 0 else f"hl(I, sib, {pkc})"
            w(f"rule Verify_q{qi}_a{a}:")
            w(f"  [ !Root(I,{r}), In(<I,{q},{N[a]},sm,sk,sib>) ]")
            w(f"  --[ Cks({N[a]},{N[c]}), Accept(I,{q},{N[a]}) ]-> []")
    w("")
    w("lemma exec: exists-trace")
    w('  "Ex I q a #s #k. Sign(I,q,a)@s & Accept(I,q,a)@k & not (Ex #r. RevealSeed(I)@r)"')
    w("")
    w("// L-S4 (leaf index uniqueness), pure form: each leaf signs at most once.")
    w("lemma LS4_pure [use_induction]:")
    w('  "All I q a1 a2 #i #j. Sign(I,q,a1)@i & Sign(I,q,a2)@j ==> #i = #j"')
    w("")
    extra = []
    if variant == 'rollback':
        extra.append("(Ex x y #r. Rollback(I,x,y)@r)")
    if variant == 'clone':
        extra.append("(Ex x #r. Clone(I,x)@r)")
    exc = (" | " + " | ".join(extra)) if extra else ""
    w("// L-S4 with the state-misuse events as explicit exceptions.")
    w("lemma LS4 [use_induction]:")
    w(f'  "All I q a1 a2 #i #j. Sign(I,q,a1)@i & Sign(I,q,a2)@j ==> #i = #j{exc}"')
    w("")
    w("// L-S1 (unforgeability): an accepted digit at leaf q was signed at leaf q.")
    w("lemma LS1:")
    w('  "All I q a #k. Accept(I,q,a)@k ==> (Ex #s. Sign(I,q,a)@s) | (Ex #r. RevealSeed(I)@r)"')
    w("")
    w("// L-S3 (attack side): a forgery without a seed reveal.")
    w("lemma LS3_forge: exists-trace")
    w('  "Ex I q a #k. Accept(I,q,a)@k & not (Ex #s. Sign(I,q,a)@s) & not (Ex #r. RevealSeed(I)@r)"')
    w("end")
    return "\n".join(out) + "\n"


for v in ['base', 'rollback', 'clone']:
    with open(f"LMS_S2_{v}.spthy", 'w') as f:
        f.write(model(v))
