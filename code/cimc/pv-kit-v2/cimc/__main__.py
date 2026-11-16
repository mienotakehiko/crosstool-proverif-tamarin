"""Usage: python3 -m cimc <cim.toml> <outdir> [--n N]
Writes the four ProVerif encodings, the four Tamarin variants, the
side-condition report and a manifest with SHA-256 sums."""
import argparse
import hashlib
import json
import os
import sys

from . import __version__
from .core import Model
from .backends import tamarin, proverif
from . import checks


def main():
    ap = argparse.ArgumentParser(prog='cimc')
    ap.add_argument('cim')
    ap.add_argument('outdir')
    ap.add_argument('--n', type=int, default=None, help='unrolling depth (default: the CIM bound)')
    a = ap.parse_args()
    m = Model(a.cim)
    n = a.n or m.bound or 2
    os.makedirs(a.outdir, exist_ok=True)
    src = os.path.basename(a.cim)
    files = {}
    for v in ('base', 'cl1', 'rb1', 'omega'):
        files[f'{m.name}_T_{v}.spthy'] = tamarin(m, v, __version__, src)
    files[f'{m.name}_PV_U{n}.pv'] = proverif(m, 'U', n, __version__, src)
    files[f'{m.name}_PV_Urb{n}.pv'] = proverif(m, 'Urb', n, __version__, src)
    files[f'{m.name}_PV_lin.pv'] = proverif(m, 'lin', n, __version__, src)
    files[f'{m.name}_PV_rep.pv'] = proverif(m, 'rep', n, __version__, src)
    rep = checks.run(m)
    lines = [f'# side conditions of Theorem 1 for {m.name} (cimc {__version__})']
    lines += [f'{k:10s} {s:16s} {d}' for k, s, d in rep]
    files[f'{m.name}_checks.txt'] = '\n'.join(lines) + '\n'
    man = {}
    for fn, txt in files.items():
        with open(os.path.join(a.outdir, fn), 'w') as f:
            f.write(txt)
        man[fn] = hashlib.sha256(txt.encode()).hexdigest()
    man['_cim'] = hashlib.sha256(open(a.cim, 'rb').read()).hexdigest()
    man['_checks_failed'] = [k for k, s, _ in rep if s == 'FAIL']
    with open(os.path.join(a.outdir, f'{m.name}_manifest.json'), 'w') as f:
        json.dump(man, f, indent=1)
    print('\n'.join(lines))
    print(f'wrote {len(files)} files to {a.outdir}')
    sys.exit(1 if man['_checks_failed'] else 0)


if __name__ == '__main__':
    main()
