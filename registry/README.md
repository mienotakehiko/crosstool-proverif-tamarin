# Registry

| File | Content |
| --- | --- |
| [`repository-files.tsv`](repository-files.tsv) | Path, size in bytes and SHA-256 hash of every file of the repository except the inventory itself |
| [`normalized-files.tsv`](normalized-files.tsv) | Files whose published bytes differ from the bytes of the runs, with the original hash, the published hash and the kind of change |
| [`series.tsv`](series.tsv) | Index of the experimental series with their units, sizes and main records |

## Normalized files

Model files, inputs and verdict records keep the bytes of the runs. The table of normalized files lists every other case, and each row states one of the following changes.

| Change | Files |
| --- | --- |
| Host names and local paths replaced by placeholders | Logs, environment records and command files of the runs |
| Notes or headings translated into English | Two tables and one log excerpt |
| Messages translated into English, commands unchanged | Four run scripts of series X2 |
| Docstrings and comments revised, statements unchanged | Scripts of the validation series and of Lemma 2 |
| Default paths or input lists adapted to the layout of this repository | Five scripts, which the table marks |

The result records and the hash lists of the runs cite the hashes of the original files. The check `scripts/verify_evidence.py` therefore reads the original hash of a normalized file from the table and the hash of every other file from its bytes. For this reason a plain call of `sha256sum -c` on a hash list inside a run directory reports the normalized logs as changed, and it reports files that this repository does not hold as missing. The check counts both kinds of entries and compares all others.

The two runners `validation/common/run_set.py` and `validation/common/run_set_monotonic.py` keep their bytes, because every file `results/environment.json` records the hash of the runner that produced it.

## Update the inventory

After a change to any file, write the inventory again and repeat the checks.

```bash
python3 -B scripts/update_manifest.py
python3 -B scripts/update_manifest.py --check
python3 -B scripts/verify_evidence.py
```

Inside a Git working tree the script lists the files that Git tracks or would track, so run it after `git add -A` and add the inventory in a second step.
