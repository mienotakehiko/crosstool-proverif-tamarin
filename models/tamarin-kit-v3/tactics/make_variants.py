#!/usr/bin/env python3
"""Build the optimisation variants of a Tamarin model for kit v3.

For each model in models/, the script writes two files to variants/

  <model>__T0.spthy   the model as it is (no change)
  <model>__T1.spthy   the model with the tactic "statefirst" added

and records the SHA-256 of every input and output in variants/MANIFEST.tsv.

The tactic changes only the order in which Tamarin solves open goals. It
does not add, remove or change any rule, restriction or lemma, so a
verdict obtained with it is a verdict on the unchanged model (type S
optimisation in the paper). The script checks this: it compares the
rule, restriction and lemma text of T0 and T1 and stops if they differ.

The tactic targets the LMS/HSS models of stages 2, L-S6, and L-S7.
  - goals on the signer state (St, Snap, BotSt, TopPending) and on the
    stored roots and certificates (!Root, !TopOK) come first, because
    they fix the leaf index and the key, which prunes the search early;
  - goals that concern the misuse rules (Clone, Rollback) come next;
  - the attacker deducing a chain value or a tree node (KU(ch(..)),
    KU(hl(..))) is postponed, because these goals branch over every
    position in the chain;
  - the attacker deducing a PRF output (KU(prf(..))) comes last; it can
    only be solved by a reveal rule, which the other goals usually decide.
Lemmas outside TARGET use the default heuristic.

usage: python3 tactics/make_variants.py            (all models)
       python3 tactics/make_variants.py LMS_S2_clone (one model)
"""
import hashlib, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(os.path.dirname(ROOT), 'handwritten')
OUT = os.path.join(ROOT, 'variants')

TACTIC = r'''
// Kit v3, optimisation T1 (search order only; see tactics/make_variants.py)
tactic: statefirst
presort: C
prio:
    regex "St\(" | regex "Snap\(" | regex "BotSt\(" | regex "TopPending\("
prio:
    regex "!Root\(" | regex "!TopOK\("
prio:
    regex "Misuse\(" | regex "Clone\(" | regex "Rollback\("
deprio:
    regex "KU\( *ch\(" | regex "KU\( *hl\("
deprio:
    regex "KU\( *prf\("

'''

# The models for which T1 is generated. Stage 1 models (C1_*, LMOTS_*, A_*)
# use other facts and are run with the default heuristic and with the
# built-in rankings only (optimisation T4).
TARGET = re.compile(r'^(LMS_S2_|LMS_LS6_|HSS_LS7)')


def body_without_tactics(text):
    """Rules, restrictions and lemmas, without comments, tactics and
    heuristic annotations, normalised for comparison."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'\ntactic:.*?(?=\n(rule|lemma|restriction|end)\b)', '\n', text, flags=re.S)
    return re.sub(r'\s+', ' ', text).strip()


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    rows = []
    for fn in sorted(os.listdir(MODELS)):
        if not fn.endswith('.spthy'):
            continue
        name = fn[:-6]
        if only and name not in only:
            continue
        src = os.path.join(MODELS, fn)
        text = open(src).read()
        t0 = os.path.join(OUT, f'{name}__T0.spthy')
        with open(t0, 'w') as f:
            f.write(text)
        rows.append((name, 'T0', sha(src), sha(t0)))
        if not TARGET.match(name):
            continue
        i = text.find('\nlemma ')
        if i < 0:
            sys.exit(f'{fn}: no lemma found')
        t1_text = text[:i] + '\n' + TACTIC + text[i + 1:]
        if body_without_tactics(t1_text) != body_without_tactics(text):
            sys.exit(f'{fn}: T1 changed the model, refusing to continue')
        t1 = os.path.join(OUT, f'{name}__T1.spthy')
        with open(t1, 'w') as f:
            f.write(t1_text)
        rows.append((name, 'T1', sha(src), sha(t1)))
    with open(os.path.join(OUT, 'MANIFEST.tsv'), 'w') as f:
        f.write('# model\tvariant\tsha256_source\tsha256_variant\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    print(f'wrote {len(rows)} files to variants/')


if __name__ == '__main__':
    main()
