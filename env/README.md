# Environment records

| Path | Content |
| --- | --- |
| [`fixed-ccs26/runtime.json`](fixed-ccs26/runtime.json) | Image identifier, pinned Tamarin and ProVerif commits and the hashes of the tools in the container image of the series X0, X1, X2 and K |
| [`fixed-ccs26/Dockerfile.eval.upstream`](fixed-ccs26/Dockerfile.eval.upstream) | Dockerfile of the translation artifact from which the image derives |
| [`ec2-96g/environment.txt`](ec2-96g/environment.txt) | Cloud host of the seven runs at 96 GiB in series L, with 16 processors, 126,757 MB of memory and the tool versions |
| [`validation-host/environment.txt`](validation-host/environment.txt) | WSL2 host of the validation series, with 8 processors, 58 GiB of memory and the tool versions |

The field `binary_rebuild_verified` of `runtime.json` is false. The image of the runs carries the recorded tool hashes, and no rebuild has confirmed these binaries bit for bit.

Each model set of the validation series also holds a file `results/environment.json` with the host, the limits and the tool versions of its run.
