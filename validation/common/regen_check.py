#!/usr/bin/env python3
"""Regenerate archived model sets with a chosen generator version and compare.

    python3 -B regen_check.py --cimc CIMC_DIR DIR [DIR ...]

DIR is one set directory (with cim.toml and the eight model files) or a
directory whose subdirectories are sets. For every set, the script runs the
generator in CIMC_DIR on cim.toml and compares each model file with the
archived one. The comparison skips the line that names the generator version.
The script ends with status 1 if a file differs or the generator refuses an
input.
"""
import argparse, glob, os, re, subprocess, sys, tempfile

def body(path):
    return [l for l in open(path, encoding='utf-8').read().splitlines() if not re.search(r'cimc \d+\.\d+\.\d+', l)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cimc', required=True); ap.add_argument('roots', nargs='+')
    a = ap.parse_args()
    sets = files = same = refused = 0; differing = []
    code = "import sys; sys.path.insert(0, %r); import runpy; runpy.run_module('cimc', run_name='__main__')" % os.path.abspath(a.cimc)
    for root in a.roots:
        single = os.path.exists(os.path.join(root, 'cim.toml'))
        for name in ([os.path.basename(os.path.normpath(root))] if single else sorted(os.listdir(root))):
            d = root if single else os.path.join(root, name); cim = os.path.join(d, 'cim.toml')
            models = sorted(glob.glob(os.path.join(d, '*.pv')) + glob.glob(os.path.join(d, '*.spthy')))
            if not os.path.exists(cim) or not models:
                continue
            sets += 1
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, 'out')
                done = subprocess.run([sys.executable, '-I', '-B', '-c', code, os.path.abspath(cim), out], capture_output=True, text=True, cwd=tmp)
                if not os.path.isdir(out):
                    refused += 1; differing.append((name, 'refused: ' + done.stderr.strip()[-160:])); continue
                for m in models:
                    files += 1
                    twin = os.path.join(out, os.path.basename(m))
                    if os.path.exists(twin) and body(twin) == body(m): same += 1
                    else: differing.append((name, os.path.basename(m)))
    print(f'{sets} set(s), {files} model file(s), {same} identical up to the version line, {refused} refused')
    for item in differing[:20]: print('DIFFERS', *item)
    sys.exit(1 if differing else 0)

if __name__ == '__main__':
    main()
