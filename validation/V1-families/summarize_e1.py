#!/usr/bin/env python3
"""Summarize the runs of the parameterized families of series V1.

    python3 -B summarize_e1.py SETROOT --family CIMDIR/family.tsv
        [--out scaling.tsv] [--figure scaling.pdf]
        [--series lms_h1w1,lms_h2w1,lms_h3w1]

SETROOT holds one directory per family member with the results/ directory of
run_set.py. The script writes one line per member with the ProVerif time of
every encoding, the Tamarin time, the proof steps and the peak memory on the
standard variant T, the number of conclusive verdicts and the size of the
largest ProVerif file.

The option --figure needs matplotlib. It draws two panels for the members that
--series names, in the order of their update bound n. One panel shows the
ProVerif time of the four encodings, and the other shows the Tamarin proof
steps on T summed over the lemmas. An open marker shows a run without a
verdict. The two measures have different units, so each panel has its own
axis.
"""
import argparse
import collections
import glob
import json
import os
import sys

ENCODINGS = ("U", "Urb", "lin", "rep")
# categorical slots 1 to 4 of the validated reference palette, light surface
COLORS = {"U": "#2a78d6", "Urb": "#eb6834", "lin": "#1baf7a", "rep": "#eda100"}
MARKERS = {"U": "o", "Urb": "s", "lin": "^", "rep": "D"}
LABELS = {"U": "PV-U(n)", "Urb": "PV-Urb(n)", "lin": "PV-lin", "rep": "PV-rep"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e3e2de"


def encoding(model):
    tail = model.split("_PV_")[-1]
    return "Urb" if tail.startswith("Urb") else ("U" if tail.startswith("U") else tail)


def read_jsonl(path):
    """Return the records of a result file. If a job has several records, the last one counts."""
    last = {}
    if os.path.exists(path):
        for line in open(path):
            if line.strip():
                record = json.loads(line)
                last[(record["model"], record.get("query", record.get("lemma")))] = record
    return list(last.values())


def member(setdir):
    name = os.path.basename(os.path.normpath(setdir))
    row = collections.OrderedDict(set=name)
    pv = read_jsonl(os.path.join(setdir, "results", "pv_results.jsonl"))
    tm = read_jsonl(os.path.join(setdir, "results", "tam_results.jsonl"))
    for enc in ENCODINGS:
        mine = [r for r in pv if encoding(r["model"]) == enc]
        row[f"pv_{enc}_s"] = max((r["seconds"] for r in mine), default="")
        row[f"pv_{enc}_verdicts"] = "/".join(str(sum(1 for r in mine if r["verdict"] == v))
                                             for v in ("true", "false", "cannot")) if mine else ""
        row[f"pv_{enc}_open"] = sum(1 for r in mine if r["verdict"] not in ("true", "false", "cannot"))
    base = [r for r in tm if r["model"].endswith("_T_base")]
    done = [r for r in base if r["verdict"] in ("verified", "falsified")]
    row["tm_base_lemmas"] = len(base)
    row["tm_base_conclusive"] = len(done)
    row["tm_base_s"] = round(sum(r["seconds"] for r in base), 2) if base else ""
    row["tm_base_steps"] = sum(r["steps"] or 0 for r in done) if done else ""
    row["tm_base_rss_max_mb"] = max((r.get("rss_max_mb") or 0 for r in base), default="")
    row["tm_all_conclusive"] = sum(1 for r in tm if r["verdict"] in ("verified", "falsified"))
    row["tm_all_records"] = len(tm)
    row["pv_conclusive"] = sum(1 for r in pv if r["verdict"] in ("true", "false"))
    row["pv_records"] = len(pv)
    sizes = [os.path.getsize(p) for p in glob.glob(os.path.join(setdir, "*.pv"))]
    row["largest_pv_bytes"] = max(sizes, default="")
    return row


def draw(rows, series, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    chosen = [rows[name] for name in series if name in rows]
    if len(chosen) < 2:
        print("figure skipped: fewer than two members of --series have results", file=sys.stderr)
        return
    xs = [int(r["bound"]) for r in chosen]
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK})
    figure, (left, right) = plt.subplots(1, 2, figsize=(6.6, 2.9))
    for axis in (left, right):
        axis.set_xscale("log", base=2)
        axis.set_xticks(xs)
        axis.set_xticklabels([str(x) for x in xs])
        axis.minorticks_off()
        axis.grid(axis="y", color=GRID, linewidth=0.6)
        axis.set_axisbelow(True)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
        axis.set_xlabel("update bound n (leaves)")
        axis.margins(x=0.12)
    for enc in ENCODINGS:
        points = [(x, r[f"pv_{enc}_s"], r[f"pv_{enc}_open"]) for x, r in zip(xs, chosen) if r[f"pv_{enc}_s"] != ""]
        if not points:
            continue
        left.plot([p[0] for p in points], [max(p[1], 0.01) for p in points], color=COLORS[enc], linewidth=1.6,
                  solid_capstyle="round", zorder=2)
        for x, seconds, unfinished in points:
            left.plot([x], [max(seconds, 0.01)], marker=MARKERS[enc], markersize=6.5, linestyle="none",
                      markerfacecolor="white" if unfinished else COLORS[enc], markeredgecolor=COLORS[enc] if unfinished else "white",
                      markeredgewidth=1.2, zorder=3)
        left.plot([], [], color=COLORS[enc], marker=MARKERS[enc], markersize=5, linewidth=1.6, label=LABELS[enc])
    left.set_yscale("log")
    left.set_ylabel("ProVerif time (s)")
    left.set_title("ProVerif: time per encoding", loc="left", fontsize=8)
    left.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=4,
                handlelength=2.0, columnspacing=1.0)
    steps = [(x, r["tm_base_steps"], r["tm_base_conclusive"] < r["tm_base_lemmas"]) for x, r in zip(xs, chosen)
             if r["tm_base_steps"] != ""]
    if steps:
        right.plot([p[0] for p in steps], [p[1] for p in steps], color=COLORS["U"], linewidth=1.6, zorder=2)
        for x, value, unfinished in steps:
            right.plot([x], [value], marker="o", markersize=6.5, linestyle="none",
                       markerfacecolor="white" if unfinished else COLORS["U"],
                       markeredgecolor=COLORS["U"] if unfinished else "white", markeredgewidth=1.2, zorder=3)
            right.annotate(f"{value:,}", (x, value), textcoords="offset points", xytext=(0, 7), ha="center",
                           fontsize=7, color=INK)
    right.set_ylim(bottom=0)
    right.set_ylabel("proof steps")
    right.set_title("Tamarin: proof steps on T, all lemmas", loc="left", fontsize=8)
    figure.tight_layout()
    figure.savefig(path)
    print(f"figure written to {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("setroot")
    parser.add_argument("--family", help="family.tsv written by make_family.py")
    parser.add_argument("--out", default="scaling.tsv")
    parser.add_argument("--figure")
    parser.add_argument("--series", default="lms_h1w1,lms_h2w1,lms_h3w1")
    args = parser.parse_args()
    info = {}
    if args.family:
        for line in open(args.family).read().splitlines()[1:]:
            name, family, parameters, bound = line.split("\t")
            info[name.lower()] = (family, parameters, bound)
    rows = collections.OrderedDict()
    for name in sorted(os.listdir(args.setroot)):
        setdir = os.path.join(args.setroot, name)
        if os.path.isdir(os.path.join(setdir, "results")):
            row = member(setdir)
            family, parameters, bound = info.get(name.lower(), ("", "", ""))
            row.update(family=family, parameters=parameters, bound=bound)
            rows[name.lower()] = row
    if not rows:
        print("no member with results found", file=sys.stderr)
        return 1
    columns = ["set", "family", "parameters", "bound"] + [c for c in next(iter(rows.values())) if c not in
                                                         ("set", "family", "parameters", "bound")]
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write("\t".join(columns) + "\n")
        for row in rows.values():
            handle.write("\t".join(str(row[c]) for c in columns) + "\n")
    print(f"{len(rows)} members written to {args.out}")
    if args.figure:
        draw(rows, args.series.split(","), args.figure)
    return 0


if __name__ == "__main__":
    sys.exit(main())
