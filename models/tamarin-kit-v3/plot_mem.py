#!/usr/bin/env python3
"""Draw the memory curves in results/out/*.mem (elapsed seconds against RSS
in MB), one line per job, into results/memory.png. Needs matplotlib; when it
is missing, print a plain-text summary instead."""
import glob, os, sys

here = os.path.dirname(os.path.abspath(__file__))
curves = {}
for path in sorted(glob.glob(os.path.join(here, 'results', 'out', '*.mem'))):
    pts = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                pts.append((float(parts[0]), float(parts[1])))
    if pts:
        curves[os.path.basename(path)[:-4]] = pts

if not curves:
    sys.exit('no memory samples found in results/out')

for name, pts in curves.items():
    peak = max(p[1] for p in pts)
    print(f'{name:60s} {pts[-1][0]:8.0f} s  peak {peak:7.0f} MB')

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit('matplotlib not installed; text summary only')

fig, ax = plt.subplots(figsize=(9, 5))
for name, pts in curves.items():
    ax.plot([p[0] for p in pts], [p[1] for p in pts], label=name, linewidth=1)
ax.set_xlabel('elapsed time (s)')
ax.set_ylabel('resident memory (MB)')
ax.grid(True, alpha=0.3)
if len(curves) <= 20:
    ax.legend(fontsize=6, loc='upper left')
fig.tight_layout()
out = os.path.join(here, 'results', 'memory.png')
fig.savefig(out, dpi=150)
print('wrote', out)
