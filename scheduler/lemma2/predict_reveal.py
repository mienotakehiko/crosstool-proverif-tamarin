#!/usr/bin/env python3
"""Predict the effect of the reveal alternative with the atomic scheduler (no prover).

    python3 -B predict_reveal.py --cimc CIMC_DIR --checker DIR_OF_unrolled_check CIM.toml [...] [--length 3]

The script enumerates the atomic scheduler of Appendix B for one thread. For
the acceptance event of each model, it reports whether the matching signing or
release event precedes every acceptance (a) if a reveal counts as an excuse
and (b) if it does not.
"""
import argparse, re, sys
ap = argparse.ArgumentParser(); ap.add_argument('--cimc', required=True); ap.add_argument('--checker', required=True)
ap.add_argument('--length', type=int, default=3); ap.add_argument('cims', nargs='+'); a = ap.parse_args()
sys.path.insert(0, a.cimc); sys.path.insert(0, a.checker)
from cimc.core import Model
import unrolled_check as uc
PAIRS = {'Accept': 'Sign', 'Acc': 'Rel'}
for path in a.cims:
    m = Model(path)
    system = uc.System(m, m.bound or 2)
    words, states = uc.atomic(system, 1, a.length)
    unexcused, excused = [], []
    for w in words:
        events = w.split()
        for k, e in enumerate(events):
            name, args = e.split('(', 1)
            if name not in PAIRS:
                continue
            before = events[:k]
            if (PAIRS[name] + '(' + args) in before:
                continue
            prefix = ' '.join(events[:k + 1])
            (excused if any(x.startswith('Reveal') for x in before) else unexcused).append(prefix)
    shortest = lambda items: min(items, key=lambda x: (len(x.split()), x))
    example = shortest(unexcused) if unexcused else (shortest(excused) if excused else None)
    print(f'{m.name}: {len(words)} words; authentication with reveal alternative: {"FAILS" if unexcused else "holds"}; '
          f'without it: {"fails" if unexcused or excused else "holds"}' + (f'; e.g. {example}' if example else ''))
