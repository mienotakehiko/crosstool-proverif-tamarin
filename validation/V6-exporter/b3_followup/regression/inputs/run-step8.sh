#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  printf 'Usage: bash run-step8.sh CANDIDATE_BINARY\n' >&2
  exit 2
fi
kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
candidate="$(realpath -- "$1")"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
commit='c293106913ccf7bb41f49b0dc555a8074e8ea88c'
proverif_commit='1d4cd9458d9ccf648e149ec2ea5147b2c87b67df'

cd "$kit"
sha256sum -c SHA256SUMS
run_dir="$(mktemp -d "$kit/step8-run.XXXXXXXX")"
out="$run_dir/evidence"
mkdir "$out"
stage=preflight

finish() {
  local rc=$?
  trap - EXIT
  printf 'stage=%s\nrc=%s\n' "$stage" "$rc" | tee "$out/status.txt"
  if (cd "$out" &&
      find . -type f ! -name SHA256SUMS -print0 | LC_ALL=C sort -z |
        xargs -0 sha256sum > SHA256SUMS) &&
     tar -czf "$run_dir/evidence.tar.gz" -C "$out" .; then
    sha256sum -- "$run_dir/evidence.tar.gz"
    printf 'ARCHIVE=%s\n' "$run_dir/evidence.tar.gz"
  else
    printf 'EVIDENCE_DIR=%s\n' "$out" >&2
    if [ "$rc" -eq 0 ]; then rc=1; fi
  fi
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir "$out/inputs"
cp -a -- models reference cases.json common.py regression.py run-step8.sh \
  README_ja.md STEP7_RESULTS.md candidate-binary.sha256 fixed-runtime.sha256 "$out/inputs/"
cp -- SHA256SUMS "$out/kit.sha256"
test -x "$candidate"
read -r expected _ < candidate-binary.sha256
printf '%s  %s\n' "$expected" "$candidate" |
  sha256sum -c - | tee "$out/binary-check.txt"
printf '%s  tamarin-prover\n' "$expected" > "$out/candidate-binary.sha256"

docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}' |
  tee "$out/docker-version.txt"
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" |
  tee "$out/fixed-image.txt"
grep -Fxq "$image linux/amd64" "$out/fixed-image.txt"
docker run --rm --pull never --network none --read-only --entrypoint /bin/sh "$image" -ec '
  test "$(cat /opt/eval/TAMARIN_COMMIT)" = "$1"
  test "$(cat /opt/eval/PROVERIF_COMMIT)" = "$2"
  sha256sum /usr/local/bin/tamarin-prover /usr/local/bin/proverif /usr/local/bin/maude /opt/eval/eval.py
' sh "$commit" "$proverif_commit" | tee "$out/runtime.sha256"
cmp "$out/runtime.sha256" fixed-runtime.sha256

stage=regression
cmd=(docker run --rm --pull never --network none --read-only
  --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128
  --cap-drop ALL --security-opt no-new-privileges
  --user "$(id -u):$(id -g)" --env HOME=/work --env PYTHONUTF8=1
  --tmpfs /tmp:rw,nosuid,nodev,size=128m
  --mount "type=bind,src=$kit,dst=/kit,readonly"
  --mount "type=bind,src=$out,dst=/work"
  --mount "type=bind,src=$candidate,dst=/step8-tamarin-prover,readonly"
  --workdir /work --entrypoint python3 "$image" -B /kit/regression.py)
printf '%q ' "${cmd[@]}" > "$out/runtime-command.sh"
printf '\n' >> "$out/runtime-command.sh"
result=0
"${cmd[@]}" 2>&1 | tee "$out/regression.log" || result=$?
if [ -f "$out/decision.json" ]; then cat "$out/decision.json"; fi
if [ "$result" -ne 0 ]; then exit "$result"; fi
test -s "$out/decision.json"
stage=complete
