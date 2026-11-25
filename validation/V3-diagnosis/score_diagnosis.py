#!/usr/bin/env python3
"""Score the diagnosis procedure against sealed labels (series V3).

    python3 -B score_diagnosis.py LABELS.tsv PREDICTIONS.tsv

Both files have a header and the two tab-separated columns item and cause. A
label is the cause that the construction of the item fixes or that a person
assigns without access to the predictions. A prediction is the output of the
decision tree, which may be "undetermined". The script prints the confusion
matrix, the precision, recall and F1 score of every cause, the macro-averaged
F1 score, the accuracy and the share of undetermined predictions.
"""
import collections
import sys


def read(path):
    table = {}
    with open(path, encoding="utf-8") as handle:
        next(handle)
        for line in handle:
            if line.strip() and not line.startswith("#"):
                item, cause = line.rstrip("\n").split("\t")[:2]
                table[item] = cause
    return table


def main():
    labels, predictions = read(sys.argv[1]), read(sys.argv[2])
    missing = sorted(set(labels) - set(predictions))
    if missing:
        print(f"{len(missing)} labeled item(s) have no prediction: {missing[:5]}")
        return 1
    causes = sorted(set(labels.values()))
    columns = causes + sorted(set(predictions.values()) - set(causes))
    matrix = collections.Counter((labels[i], predictions[i]) for i in labels)
    width = max(len(c) for c in columns + ["label \\ prediction"]) + 2
    print("label \\ prediction".ljust(width) + "".join(c.ljust(width) for c in columns))
    for label in causes:
        print(label.ljust(width) + "".join(str(matrix[(label, c)]).ljust(width) for c in columns))
    scores = []
    print()
    for cause in causes:
        tp = matrix[(cause, cause)]
        predicted = sum(matrix[(label, cause)] for label in causes)
        actual = sum(matrix[(cause, c)] for c in columns)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append(f1)
        print(f"{cause.ljust(width)}precision {precision:.2f}  recall {recall:.2f}  F1 {f1:.2f}  (n = {actual})")
    total = len(labels)
    correct = sum(matrix[(c, c)] for c in causes)
    undetermined = sum(1 for i in labels if predictions[i] == "undetermined")
    print(f"\nitems {total}; accuracy {correct / total:.2f}; macro-F1 {sum(scores) / len(scores):.2f}; "
          f"undetermined {undetermined / total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
