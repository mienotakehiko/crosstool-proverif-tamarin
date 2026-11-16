#!/usr/bin/env python3
"""Print the lemma names in a .spthy file in source order.

Track block comment nesting as the Tamarin parser does and skip lemmas
inside comments.
"""
import re, sys


def strip_comments(t):
    out, depth, i = [], 0, 0
    while i < len(t):
        if t.startswith('/*', i):
            depth += 1; i += 2; continue
        if depth and t.startswith('*/', i):
            depth -= 1; i += 2; continue
        if not depth and t.startswith('//', i):
            j = t.find('\n', i); i = len(t) if j < 0 else j; continue
        if not depth:
            out.append(t[i])
        i += 1
    return ''.join(out)


def lemmas(path):
    return re.findall(r'^\s*lemma\s+([A-Za-z0-9_]+)', strip_comments(open(path).read()), re.M)


if __name__ == '__main__':
    print('\n'.join(lemmas(sys.argv[1])))
