"""Regression test: rerun al_assign on the stored sandbox records of
LMS_S2 and LMOTS and compare with the stored JSON. Run from cimc/."""
import json, subprocess, sys, tempfile, os
CASES = [('lms_s2', 'LMS_S2'), ('lmots', 'LMOTS')]
bad = 0
for cim, name in CASES:
    with tempfile.TemporaryDirectory() as d:
        pre = os.path.join(d, 'al')
        subprocess.run([sys.executable, '-m', 'cimc.al_assign', f'cims/{cim}.toml',
                        f'out/{cim}/{name}_checks.txt', '-o', pre,
                        '--pv', f'tests/data/{cim}_pv_sandbox.jsonl',
                        '--tm', f'tests/data/{cim}_tam_sandbox.tsv'],
                       check=True, stdout=subprocess.DEVNULL)
        got = json.load(open(pre + '.json'))
    exp = json.load(open(f'tests/data/al_{cim}_sandbox.json'))
    for k in ('cimc', 'al_assign_sha256', 'diagnosis_sha256'):
        got.pop(k, None); exp.pop(k, None)
    ok = got == exp
    bad += not ok
    print(f'{name}: {"SAME" if ok else "DIFF"}')
sys.exit(1 if bad else 0)
