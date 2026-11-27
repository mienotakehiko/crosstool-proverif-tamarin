#!/usr/bin/env python3
"""Compare two independently produced, merged artifact result files with the fixed native reference."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

KEY = ('input_file', 'lemma')
FLAGS = ('translate_error', 'proverif_timeout', 'proverif_oom')
BOOL = {'true', 'false'}

def load(path):
    out = {}
    for num, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = tuple(row[k] for k in KEY)
        if not all(isinstance(k, str) and k for k in key) or key in out:
            raise ValueError(f'{path}, line {num}: empty or duplicate task {key!r}')
        out[key] = row
    return out

def category(row):
    value = row['proverif_result']
    for k in FLAGS:
        if type(row[k]) is not bool:
            raise ValueError(f'Invalid {k} for {row["input_file"]}, {row["lemma"]}')
    err = row['proverif_error']
    faults = [name for name, active in zip(('export_error','timeout','oom'),(row[k] for k in FLAGS)) if active]
    if err:
        faults.append('pv_error')
    if type(value) is bool:
        if faults:
            raise ValueError(f'Conflicting Boolean result and error flags: {row!r}')
        return str(value).lower()
    if faults:
        return '+'.join(faults)
    if value is None:
        return 'unresolved'
    return 'reported:' + str(value)

def save_tsv(out, header, rows):
    with out.open('x', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(header)
        w.writerows(rows)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('reference','b0','b2','output'):
        p.add_argument(n, type=Path)
    a = p.parse_args()
    if len({x.resolve() for x in (a.reference,a.b0,a.b2)}) != 3:
        p.error('Specify three separate files: published native reference, fresh B0, fresh B2')
    ref, b0, b2 = (load(x) for x in (a.reference,a.b0,a.b2))
    if len(ref) != 566 or len({k[0] for k in ref}) != 121:
        p.error('Expected the published 121-theory, 566-task reference')
    for name,rows in [('B0',b0),('B2',b2)]:
        if rows.keys() != ref.keys():
            missing=sorted(ref.keys()-rows.keys())
            extra=sorted(rows.keys()-ref.keys())
            p.error(f'{name}: missing={len(missing)}, extra={len(extra)}; first missing={missing[:4]!r}, first extra={extra[:4]!r}')
    results=[]
    moves=Counter()
    agree={k:[0,0] for k in ('b0','b2','b0_common','b2_common')}
    flips=[]
    for key, r in sorted(ref.items()):
        for row in (b0[key], b2[key]):
            if row['trace_quantifier'] != r['trace_quantifier']:
                raise ValueError(f'Quantifier changed for {key}')
        x, y = category(b0[key]), category(b2[key])
        v=r['tamarin_result']
        n=str(v).lower() if type(v) is bool else 'unresolved'
        moves[x,y]+=1
        if x != y and {x,y} == BOOL:
            flips.append(key)
        for label, val in (('b0',x),('b2',y)):
            if val in BOOL and n in BOOL:
                agree[label][1]+=1
                agree[label][0]+=int(val==n)
                if x in BOOL and y in BOOL:
                    count=agree[label+'_common']
                    count[1]+=1
                    count[0]+=int(val==n)
        results.append((*key,r['trace_quantifier'],n,x,y))
    a.output.mkdir(parents=False, exist_ok=False)
    cols=(*KEY,'quantifier','native','B0','B2')
    save_tsv(a.output/'paired.tsv', cols, results)
    save_tsv(a.output/'changed.tsv', cols, (r for r in results if r[-1]!=r[-2]))
    save_tsv(a.output/'transitions.tsv', ('B0','B2','tasks'), ((*k,v) for k,v in sorted(moves.items())))
    for i, name in enumerate(('B0', 'B2')):
        save_tsv(a.output/f'results_{name}.tsv', ('model','lemma','verdict','native'),
                 ((r[0],r[1],r[4+i],r[3]) for r in results))
    report = {'model_count':121, 'paired_tasks':len(results),'changed':sum(n for (x,y),n in moves.items() if x!=y),
              'boolean_flips':len(flips),'gained_boolean':sum(n for (x,y),n in moves.items() if x not in BOOL and y in BOOL),
              'lost_boolean':sum(n for (x,y),n in moves.items() if x in BOOL and y not in BOOL),
              'native_agreement_numerator_denominator':agree,
              'sha256':{k:hashlib.sha256(f.read_bytes()).hexdigest() for k,f in [('reference',a.reference),('B0',a.b0),('B2',a.b2)]}}
    text=json.dumps(report,indent=2)+'\n'
    (a.output/'summary.json').write_text(text,encoding='utf-8')
    print(text,end='')

if __name__ == '__main__':
    main()
