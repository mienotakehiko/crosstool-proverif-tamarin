#!/usr/bin/env bash
set -euo pipefail

kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
proverif_sha='f6b5e9606e639350085167f150e6bca7adfcdac0b34614b890e72f7f9e0c1c28'

cd "$kit"
sha256sum -c SHA256SUMS
run_dir="$(mktemp -d "$kit/step6-run.XXXXXXXX")"
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
cp -a -- models diffs cases.json common.py probe.py run-step6.sh \
  README_ja.md STEP5_RESULTS.md "$out/inputs/"
cp -- SHA256SUMS "$out/kit.sha256"

docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}' |
  tee "$out/docker-version.txt"
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" |
  tee "$out/fixed-image.txt"
grep -Fxq "$image linux/amd64" "$out/fixed-image.txt"
docker run --rm --pull never --network none --read-only --entrypoint /bin/sh \
  "$image" -ec 'sha256sum /usr/local/bin/proverif' | tee "$out/proverif.sha256"
printf '%s  /usr/local/bin/proverif\n' "$proverif_sha" | cmp - "$out/proverif.sha256"

stage=proverif
cmd=(docker run --rm --pull never --network none --read-only
  --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128
  --cap-drop ALL --security-opt no-new-privileges
  --user "$(id -u):$(id -g)" --env HOME=/work --env PYTHONUTF8=1
  --tmpfs /tmp:rw,nosuid,nodev,size=128m
  --mount "type=bind,src=$kit,dst=/kit,readonly"
  --mount "type=bind,src=$out,dst=/work"
  --workdir /work --entrypoint python3 "$image" -B /kit/probe.py)
printf '%q ' "${cmd[@]}" > "$out/proverif.command.sh"
printf '\n' >> "$out/proverif.command.sh"
"${cmd[@]}" 2>&1 | tee "$out/container.log"
cat "$out/decision.json"
stage=complete
