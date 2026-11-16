#!/usr/bin/env bash
set -euo pipefail

kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
commit='c293106913ccf7bb41f49b0dc555a8074e8ea88c'
proverif_commit='1d4cd9458d9ccf648e149ec2ea5147b2c87b67df'

cd "$kit"
sha256sum -c SHA256SUMS
run_dir="$(mktemp -d "$kit/step7-run.XXXXXXXX")"
out="$run_dir/evidence"
binaries="$run_dir/binaries"
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
  if [ -x "$binaries/candidate/tamarin-prover" ]; then
    printf 'CANDIDATE_BINARY=%s\n' "$binaries/candidate/tamarin-prover"
  fi
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir "$out/inputs"
cp -a -- context models reference cases.json row-id-guards.patch common.py probe.py \
  run-step7.sh README_ja.md STEP6_RESULTS.md TAMARIN-LICENSE candidate-Rule.hs.sha256 "$out/inputs/"
cp -- SHA256SUMS "$out/kit.sha256"
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}' |
  tee "$out/docker-version.txt"
docker buildx version | tee "$out/buildx-version.txt"
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" |
  tee "$out/fixed-image.txt"
grep -Fxq "$image linux/amd64" "$out/fixed-image.txt"
docker run --rm --pull never --network none --read-only --entrypoint /bin/sh "$image" -ec '
  test "$(cat /opt/eval/TAMARIN_COMMIT)" = "$1"
  test "$(cat /opt/eval/PROVERIF_COMMIT)" = "$2"
  sha256sum /usr/local/bin/tamarin-prover /usr/local/bin/proverif /usr/local/bin/maude /opt/eval/eval.py
' sh "$commit" "$proverif_commit" | tee "$out/runtime.sha256"
cmp "$out/runtime.sha256" fixed-runtime.sha256

stage=build
build_cmd=(docker buildx build --platform linux/amd64 --progress plain
  --build-arg "TAMARIN_REF=$commit"
  --output "type=local,dest=$binaries" "$kit/context")
printf '%q ' "${build_cmd[@]}" > "$out/build-command.sh"
printf '\n' >> "$out/build-command.sh"
"${build_cmd[@]}" 2>&1 | tee "$out/build.log"

stage=binary-check
test "$(cat "$binaries/metadata/source.commit")" = "$commit"
cp -a -- "$binaries/metadata" "$out/"
candidate="$binaries/candidate"
cmp candidate-Rule.hs.sha256 "$candidate/Rule.hs.sha256"
(
  cd "$candidate"
  sha256sum -c tamarin-prover.sha256
  test -x tamarin-prover
)
cp -- "$candidate/tamarin-prover.sha256" "$out/candidate-binary.sha256"

stage=focus-check
cmd=(docker run --rm --pull never --network none --read-only
  --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128
  --cap-drop ALL --security-opt no-new-privileges
  --user "$(id -u):$(id -g)" --env HOME=/work --env PYTHONUTF8=1
  --tmpfs /tmp:rw,nosuid,nodev,size=128m
  --mount "type=bind,src=$kit,dst=/kit,readonly"
  --mount "type=bind,src=$out,dst=/work"
  --mount "type=bind,src=$candidate/tamarin-prover,dst=/step7-tamarin-prover,readonly"
  --workdir /work --entrypoint python3 "$image" -B /kit/probe.py)
printf '%q ' "${cmd[@]}" > "$out/probe-command.sh"
printf '\n' >> "$out/probe-command.sh"
probe_rc=0
"${cmd[@]}" 2>&1 | tee "$out/probe.log" || probe_rc=$?
if [ -f "$out/decision.json" ]; then cat "$out/decision.json"; fi
if [ "$probe_rc" -ne 0 ]; then exit "$probe_rc"; fi
test -s "$out/decision.json"
stage=complete
