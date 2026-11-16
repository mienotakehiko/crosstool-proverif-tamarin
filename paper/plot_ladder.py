#!/usr/bin/env python3
"""Plot archived time-to-heap-exhaustion points from the R3 ladder."""
import argparse
from collections import defaultdict
import csv
from pathlib import Path


def main():
    import matplotlib.pyplot as plt

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    groups = defaultdict(list)
    with Path(__file__).with_name("ladder_points.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["verdict"] != "HEAP":
                raise ValueError(f"Expected heap exhaustion for {row['job']}")
            groups[row["group"]].append((int(row["heap_cap"].removesuffix("g")), float(row["seconds"])))

    fig, ax = plt.subplots(figsize=(7.5, 4.2), layout="constrained")
    for group, points in groups.items():
        x, y = zip(*sorted(points))
        line, = ax.plot(x, y, marker="o", label=group)
        ax.scatter([x[-1]], [y[-1]], facecolor="white", edgecolor=line.get_color(), zorder=3)
    ax.set(xlabel="Heap cap (GiB)", ylabel="Time to heap exhaustion (s)", xticks=[8, 16, 32, 56])
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(args.output)


if __name__ == "__main__":
    main()
