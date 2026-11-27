# Releases and versions of the paper

The paper cites this repository by its address and names no commit. The repository changes whenever a review of the paper asks for a further measurement, and a commit hash in the paper would be out of date after every such change. A release fixes one state of the repository, and this page relates the releases to the versions of the manuscript.

## Releases

| Release | Version of the manuscript | Content | Archive |
| --- | --- | --- | --- |
| `v1.0` | Manuscript as submitted to *Cryptography* (MDPI) | The series G to K and V1 to V7 of the paper, the two follow-ups of series V1 and the benchmark comparison of series V6 | none yet |

Each release is a Git tag, and the release page of the repository states its date. A row of this table exists as soon as the corresponding state is ready, and the tag follows when the manuscript version goes to the journal.

## Identify a state

The tag determines the commit. The inventory [`registry/repository-files.tsv`](../registry/repository-files.tsv) of that commit states the size and the SHA-256 hash of every other file, and the checks compare the files with the inventory.

```bash
git clone https://github.com/mienotakehiko/crosstool-proverif-tamarin
cd crosstool-proverif-tamarin
git checkout v1.0
bash scripts/check_all.sh
```

## Later changes

A later change adds a release and a row to the table and moves no existing tag. If a change affects a number of the paper, the row names the manuscript version that reports the new number. The states before the first release carry no tag, and the history of the branch `main` holds them.

## Citation

The file [`CITATION.cff`](../CITATION.cff) identifies the repository. A citation of a result should name the paper and the release.
