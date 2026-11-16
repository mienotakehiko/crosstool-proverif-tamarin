#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  printf 'Usage: bash run-step4.sh STEP3_RUN_DIRECTORY\n' >&2
  exit 2
fi

kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
step3="$(cd -- "$1" && pwd)"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
step3_sha='5d3caef163dbaa9c1dbe83d81e47d35c9e59dae980ac30f11cf28979b336251d'
tamarin_commit='c293106913ccf7bb41f49b0dc555a8074e8ea88c'
proverif_commit='1d4cd9458d9ccf648e149ec2ea5147b2c87b67df'
baseline_rule='faa7042e95c3ffb45b033de161abd17b006e268b534e699e9ccbe8a784c30b56'
candidate_rule='ccf63a271655fd1900a990a4a54be6ce28ebf26b26dc198e74ca9f0a29871d2c'

cd "$kit"
sha256sum -c SHA256SUMS
run_dir="$(mktemp -d "$kit/step4-run.XXXXXXXX")"
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
cp -a -- models reference cases.json common.py regression.py fixed-runtime.sha256 \
  run-step4.sh "$out/inputs/"
cp -- SHA256SUMS "$out/kit.sha256"

cp -- "$step3/evidence.tar.gz" "$out/step3-build-evidence.tar.gz"
printf '%s  %s\n' "$step3_sha" "$out/step3-build-evidence.tar.gz" |
  sha256sum -c - | tee "$out/step3-archive-check.txt"
proof="$out/step3-build-evidence.tar.gz"
tar -xOzf "$proof" ./status.txt > "$out/step3-status.txt"
printf 'stage=complete\nrc=0\n' | cmp - "$out/step3-status.txt"
printf '%s\n' "$tamarin_commit" | cmp - <(tar -xOzf "$proof" ./metadata/source.commit)
tar -xOzf "$proof" ./fixed-runtime.sha256 | cmp - fixed-runtime.sha256

for variant in baseline candidate; do
  rule="$baseline_rule"
  if [ "$variant" = candidate ]; then rule="$candidate_rule"; fi
  tar -xOzf "$proof" "./$variant-Rule.hs.sha256" > "$out/$variant-Rule.hs.sha256"
  printf '%s  lib/export/src/Export/ProVerif/Rule.hs\n' "$rule" |
    cmp - "$out/$variant-Rule.hs.sha256"
  tar -xOzf "$proof" "./$variant-tamarin-prover.sha256" > "$out/$variant-tamarin-prover.sha256"
  (
    cd "$step3/binaries/$variant"
    sha256sum -c "$out/$variant-tamarin-prover.sha256"
    test -x tamarin-prover
  )
done
if cmp -s "$step3/binaries/baseline/tamarin-prover" "$step3/binaries/candidate/tamarin-prover"; then
  printf 'Unexpected identical Tamarin executables.\n' >&2
  exit 1
fi

docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}' |
  tee "$out/docker-version.txt"
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" |
  tee "$out/fixed-image.txt"
grep -Fxq "$image linux/amd64" "$out/fixed-image.txt"
docker run --rm --pull never --network none --entrypoint /bin/sh "$image" -ec '
  test "$(cat /opt/eval/TAMARIN_COMMIT)" = "$1"
  test "$(cat /opt/eval/PROVERIF_COMMIT)" = "$2"
  sha256sum /usr/local/bin/tamarin-prover /usr/local/bin/proverif /usr/local/bin/maude /opt/eval/eval.py
' sh "$tamarin_commit" "$proverif_commit" | tee "$out/runtime-actual.sha256"
cmp "$out/runtime-actual.sha256" fixed-runtime.sha256

for variant in baseline candidate; do
  stage="$variant"
  binary="$step3/binaries/$variant/tamarin-prover"
  cmd=(docker run --rm --pull never --network none --read-only
    --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128
    --cap-drop ALL --security-opt no-new-privileges
    --user "$(id -u):$(id -g)" --env HOME=/work --env PYTHONUTF8=1
    --tmpfs /tmp:rw,nosuid,nodev,size=128m
    --mount "type=bind,src=$kit,dst=/kit,readonly"
    --mount "type=bind,src=$out,dst=/work"
    --mount "type=bind,src=$binary,dst=/step4-tamarin-prover,readonly"
    --workdir /work --entrypoint python3 "$image" -B /kit/regression.py "$variant")
  printf '%q ' "${cmd[@]}" > "$out/$variant.command.sh"
  printf '\n' >> "$out/$variant.command.sh"
  "${cmd[@]}" 2>&1 | tee "$out/$variant.container.log"
  printf '\n[%s]\n' "$variant"
  cat "$out/$variant/counts.tsv"
done

stage=complete
