#!/usr/bin/env bash
set -euo pipefail

kit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$kit_dir"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
tamarin_commit='c293106913ccf7bb41f49b0dc555a8074e8ea88c'
proverif_commit='1d4cd9458d9ccf648e149ec2ea5147b2c87b67df'

sha256sum -c SHA256SUMS
run_dir="$(mktemp -d "$kit_dir/step3-build.XXXXXXXX")"
report="$run_dir/evidence"
binaries="$run_dir/binaries"
mkdir "$report"

stage='preflight'
finish() {
  local rc=$?
  trap - EXIT
  printf 'stage=%s\nrc=%s\n' "$stage" "$rc" | tee "$report/status.txt"
  if tar -czf "$run_dir/evidence.tar.gz" -C "$report" .; then
    sha256sum -- "$run_dir/evidence.tar.gz"
    printf 'ARCHIVE=%s\n' "$run_dir/evidence.tar.gz"
  else
    printf 'Evidence directory: %s\n' "$report" >&2
    if [ "$rc" -eq 0 ]; then rc=1; fi
  fi
  if [ -d "$binaries" ]; then printf 'BINARIES=%s\n' "$binaries"; fi
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp SHA256SUMS "$report/kit.sha256"
df -h "$kit_dir" | tee "$report/disk.txt"
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}' | tee "$report/docker-version.txt"
docker buildx version | tee "$report/buildx-version.txt"
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Created}}' "$image" | tee "$report/fixed-image.txt"
read -r found_id found_platform _ < "$report/fixed-image.txt"
test "$found_id" = "$image"
test "$found_platform" = linux/amd64

stage='build'
build_cmd=(docker buildx build --platform linux/amd64 --progress plain
  --build-arg "TAMARIN_REF=$tamarin_commit"
  --output "type=local,dest=$binaries" "$kit_dir/context")
printf '%q ' "${build_cmd[@]}" > "$report/build-command.sh"
printf '\n' >> "$report/build-command.sh"
"${build_cmd[@]}" 2>&1 | tee "$report/build.log"

stage='binary-check'
test "$(cat "$binaries/metadata/source.commit")" = "$tamarin_commit"
baseline_rule='faa7042e95c3ffb45b033de161abd17b006e268b534e699e9ccbe8a784c30b56'
candidate_rule='ccf63a271655fd1900a990a4a54be6ce28ebf26b26dc198e74ca9f0a29871d2c'
printf '%s  lib/export/src/Export/ProVerif/Rule.hs\n' "$baseline_rule" | cmp - "$binaries/baseline/Rule.hs.sha256"
printf '%s  lib/export/src/Export/ProVerif/Rule.hs\n' "$candidate_rule" | cmp - "$binaries/candidate/Rule.hs.sha256"
cp -r "$binaries/metadata" "$report"
for variant in baseline candidate; do
  output="$binaries/$variant"
  (cd "$output" && sha256sum -c tamarin-prover.sha256)
  cp -- "$output/Rule.hs.sha256" "$report/$variant-Rule.hs.sha256"
  cp -- "$output/tamarin-prover.sha256" "$report/$variant-tamarin-prover.sha256"
done
if cmp -s "$binaries/baseline/tamarin-prover" "$binaries/candidate/tamarin-prover"; then
  printf 'The two rebuilt binaries have identical bytes. Review the build before regression.\n' >&2
  exit 1
fi

stage='fixed-runtime-check'
docker run --rm --pull never --network none --entrypoint /bin/sh "$image" -ec '
  test "$(cat /opt/eval/TAMARIN_COMMIT)" = "$1"
  test "$(cat /opt/eval/PROVERIF_COMMIT)" = "$2"
  sha256sum /usr/local/bin/tamarin-prover /usr/local/bin/proverif /usr/local/bin/maude /opt/eval/eval.py
' sh "$tamarin_commit" "$proverif_commit" | tee "$report/fixed-runtime.sha256"
cmp "$report/fixed-runtime.sha256" "$kit_dir/fixed-runtime.sha256"

for variant in baseline candidate; do
  stage="$variant-smoke"
  binary="$binaries/$variant/tamarin-prover"
  docker run --rm --pull never --network none --read-only     --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128     --cap-drop ALL --security-opt no-new-privileges --env HOME=/tmp     --tmpfs /tmp:rw,nosuid,nodev,size=128m     --mount "type=bind,src=$binary,dst=/step3-tamarin-prover,readonly"     --entrypoint /usr/bin/timeout "$image"     60s /step3-tamarin-prover +RTS -N1 -M768m -RTS --version     2>&1 | tee "$report/$variant-version.log"
done

stage='complete'
