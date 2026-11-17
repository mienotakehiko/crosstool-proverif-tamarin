#!/usr/bin/env python3
"""Bounded, sequential same-source comparison. Never changes saved evidence."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'cimc'))
from cimc.core import Model
from cimc.backends import proverif, tamarin
from cimc import __version__
from cimc.checks import run as check_model

OUT = ROOT / 'audit_20261028' / 'extension_20261029'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def limit_memory():
    # GHC reserves a large virtual arena; RLIMIT_AS prevents startup even
    # with a small live heap. Heap is capped separately and RSS is watched.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def execute(args, output, seconds=30):
    start = datetime.datetime.now(datetime.timezone.utc)
    with output.open('w') as stream:
        p = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                             env=dict(os.environ, LC_ALL='C.UTF-8'),
                             start_new_session=True, preexec_fn=limit_memory)
        import signal
        import time
        peak = 0
        while p.poll() is None:
            try:
                kb = int(next(x.split()[1] for x in Path(f'/proc/{p.pid}/status').read_text().splitlines()
                              if x.startswith('VmRSS:')))
                peak = max(peak, kb)
            except (FileNotFoundError, StopIteration, ProcessLookupError):
                pass
            elapsed = (datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()
            if elapsed > seconds or peak > 850*1024:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                rc = 124 if elapsed > seconds else 137
                break
            time.sleep(0.1)
        else:
            rc = p.returncode
    return dict(command=args, rc=rc, stdout=output.name,
                stdout_sha256=digest(output),
                elapsed_s=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds(),
                timeout_s=seconds, rss_stop_mib=850, sampled_peak_rss_kib=peak)


def pv_results(text):
    return [dict(query=q, verdict=v) for q, v in
            re.findall(r'^RESULT (.*?) (is true|is false|cannot be proved)\.$', text, re.M)]


def main():
    global OUT
    if '--retry-rss' in sys.argv:
        OUT = OUT.with_name('extension_20261029_rss')
    namespace_tags = '--namespace-tags' in sys.argv
    if namespace_tags:
        OUT = OUT.with_name('extension_20261029_namespaced')
    OUT.mkdir(exist_ok=True)
    env = {}
    for tool in ('proverif', 'tamarin-prover', 'maude'):
        path = Path(shutil.which(tool)).resolve()
        env[tool] = dict(path=str(path), sha256=digest(path))
    (OUT/'executables.json').write_text(json.dumps(env, indent=2)+'\n')
    rows = []
    for seed in ('lmots', 'lms_s2'):
        src = ROOT/'cimc/cims'/f'{seed}.toml'
        dest = OUT/seed
        dest.mkdir(exist_ok=True)
        shutil.copyfile(src, dest/src.name)
        if namespace_tags:
            local_src = dest/src.name
            local_src.write_text(local_src.read_text().replace("'m'", "'tag_m'").replace("'k'", "'tag_k'"))
            src = local_src
        model = Model(src)
        pv = dest/'direct.pv'
        tm = dest/'generated.spthy'
        pv.write_text(proverif(model, 'U', model.bound, __version__, src.name))
        tm.write_text(tamarin(model, 'base', __version__, src.name))
        frozen = dict(cim_sha256=digest(src), direct_pv_sha256=digest(pv),
                      generated_tamarin_sha256=digest(tm), generator_version=__version__,
                      recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      bound=model.bound, checks=check_model(model),
                      translator='local Tamarin export; NOT the pinned CCS artifact build')
        frozen['source_tag_renaming'] = namespace_tags
        (dest/'manifest_before_runs.json').write_text(json.dumps(frozen, indent=2)+'\n')
        a = execute(['proverif', str(pv)], dest/'direct.out')
        a['results'] = pv_results((dest/'direct.out').read_text())
        b = execute(['tamarin-prover', '--prove', '--derivcheck-timeout=0', str(tm),
                     '+RTS', '-N1', '-M600m', '-RTS'], dest/'tamarin.out')
        b['results'] = [dict(lemma=l, quantifier=q, verdict=v) for l,q,v in
                        re.findall(r'^\s*(\w+) \((all-traces|exists-trace)\): (verified|falsified)',
                                   (dest/'tamarin.out').read_text(), re.M)]
        exports = []
        for prop in model.properties:
            if prop.get('misuse_exception'):
                continue
            name = prop['name']
            translated = dest/f'{name}.translated.pv'
            c = execute(['tamarin-prover', '--derivcheck-timeout=0', '-m=proverif',
                         f'--lemma={name}', f'-o={translated}', str(tm),
                         '+RTS', '-N1', '-M600m', '-RTS'], dest/f'{name}.translate.out')
            c['lemma'] = name
            c['exists_trace'] = prop['kind']=='phi3'
            if translated.exists() and translated.stat().st_size:
                c['translated_sha256'] = digest(translated)
                text = translated.read_text()
                c['leading_negation'] = 'leading negation' in text
                c['translation_warnings'] = [x for x in text.splitlines() if
                    'translation failed' in x.lower() or 'has negated event' in x.lower()]
                d = execute(['proverif', str(translated)], dest/f'{name}.translated.out')
                d['results'] = pv_results((dest/f'{name}.translated.out').read_text())
                c['pv_run'] = d
            exports.append(c)
        row = dict(seed=seed, frozen=frozen, direct=a, tamarin=b, translated=exports)
        rows.append(row)
        (OUT/'same_source_results.json').write_text(json.dumps(rows, indent=2)+'\n')
        print(seed, 'DIRECT', a['results'], 'TAMARIN', b['results'],
              'TRANSLATED', [(x['lemma'], x.get('pv_run',{}).get('results',[])) for x in exports], flush=True)


if __name__ == '__main__':
    main()
