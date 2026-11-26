#!/usr/bin/env python3
"""Compare the model part of the follow-up sets with the archived sets of series V1.

    python3 -B validation/V1-families/reveal_followup/check_model_part.py

The follow-up changes the properties only. For each of the 16 model files the
script removes the first line, which names the generator version and the
input file, and every query or lemma, and it renames the model. The remaining
text must equal the text that the same steps leave of the file of series V1.
The script starts no prover.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1_SETS = os.path.join(HERE, "..", "sets")


def model_part(path, name, common):
    with open(path, encoding="utf-8") as handle:
        text = handle.read().replace(name, common)
    text = "\n".join(text.split("\n")[1:])
    if path.endswith(".spthy"):
        return re.sub(r"\nlemma .*?(?=\nlemma |\nend\n)", "", text, flags=re.S)
    return re.sub(r"\(\* \w+ \*\)\nquery.*?\.\n\n", "", text, flags=re.S)


def main():
    different = []
    count = 0
    for member in ("otp_n2", "otp_n3"):
        old_name = member.upper()
        new_name = old_name + "_REVEAL"
        new_dir = os.path.join(HERE, "sets", member + "_reveal")
        files = sorted(glob.glob(os.path.join(new_dir, "*.pv")) + glob.glob(os.path.join(new_dir, "*.spthy")))
        for new in files:
            old = os.path.join(V1_SETS, member, os.path.basename(new).replace("_REVEAL", ""))
            count += 1
            if model_part(new, new_name, "MODEL") != model_part(old, old_name, "MODEL"):
                different.append(os.path.basename(new))
    for name in different:
        print(f"DIFFERENT model part: {name}")
    print(f"{count - len(different)} of {count} model files have the model part of series V1")
    sys.exit(1 if different or count != 16 else 0)


if __name__ == "__main__":
    main()
