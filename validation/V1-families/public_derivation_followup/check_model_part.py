#!/usr/bin/env python3
"""Compare the follow-up sets with the archived sets of series V1.

    python3 -B validation/V1-families/public_derivation_followup/check_model_part.py

The follow-up declares the function prf public and appends two properties. For
each of the 16 model files, the script removes the first line, which names the
generator version and the input file, renames the model and separates the
queries or lemmas from the rest. It then requires three facts.

  1. The model part equals the model part of the file of series V1 once the
     attribute [private] is removed from the single declaration of prf there.
  2. Every query or lemma of the file of series V1 occurs unchanged, in the
     same order.
  3. The file holds exactly two further queries or lemmas, whose names end
     with _noreveal.

A difference between a verdict of this follow-up and a verdict of series V1 on
a property of V1 can therefore only stem from the declaration of prf. The
script starts no prover.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1_SETS = os.path.join(HERE, "..", "sets")
MEMBERS = ("lmots_w2m1", "lms_h1w2")


def split(path, name, common):
    """Return the model part and the list of queries or lemmas of one file."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read().replace(name, common)
    text = "\n".join(text.split("\n")[1:])
    if path.endswith(".spthy"):
        pattern = r"\nlemma .*?(?=\nlemma |\nend\n)"
    else:
        pattern = r"\(\* \w+ \*\)\nquery.*?\.\n\n"
    properties = [item.strip() for item in re.findall(pattern, text, flags=re.S)]
    return re.sub(pattern, "", text, flags=re.S), properties


def property_name(item):
    match = re.match(r"lemma (\w+)|\(\* (\w+) \*\)", item)
    return match.group(1) or match.group(2)


def main():
    problems = []
    count = 0
    for member in MEMBERS:
        old_name = member.upper()
        new_name = old_name + "_PUB"
        new_dir = os.path.join(HERE, "sets", member + "_pub")
        files = sorted(glob.glob(os.path.join(new_dir, "*.pv")) + glob.glob(os.path.join(new_dir, "*.spthy")))
        for new in files:
            base = os.path.basename(new)
            old = os.path.join(V1_SETS, member, base.replace("_PUB", ""))
            count += 1
            new_model, new_props = split(new, new_name, "MODEL")
            old_model, old_props = split(old, old_name, "MODEL")
            if old_model.count(" [private]") != 1 or "private" in new_model:
                problems.append(f"{base}: unexpected declaration of a private function")
            elif old_model.replace(" [private]", "") != new_model:
                problems.append(f"{base}: the model part differs beyond the declaration of prf")
            if new_props[:len(old_props)] != old_props:
                problems.append(f"{base}: a property of series V1 is missing or changed")
            extra = [property_name(item) for item in new_props[len(old_props):]]
            if len(extra) != 2 or not all(name.endswith("_noreveal") for name in extra):
                problems.append(f"{base}: unexpected further properties {extra}")
    for line in problems:
        print("DIFFERENT " + line)
    print(f"{count} model files compared with series V1, {len(problems)} differences beyond the "
          "declaration of prf and the two new properties")
    sys.exit(1 if problems or count != 16 else 0)


if __name__ == "__main__":
    main()
