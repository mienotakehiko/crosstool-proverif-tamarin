#!/usr/bin/env bash
set -euo pipefail

kit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
image="${1:-sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$(mktemp -d "$HOME/H1_CIM_D_RB2.${timestamp}.XXXXXXXX")"
run_name="$(basename "$run_dir")"
archive="$HOME/${run_name}.tar.gz"
printf 'RESULT_DIR=%s\n' "$run_dir"

cp -a "$kit_dir/inputs" "$kit_dir/run_inside.py" "$kit_dir/run_pilot.sh" "$run_dir/"
(
  cd "$run_dir/inputs"
  sha256sum -c SHA256SUMS
) > "$run_dir/inputs.check.txt"
{
  date -u
  uname -a
  docker version
} > "$run_dir/host.txt" 2>&1 || true

rc=0
if image_id="$(docker image inspect --format '{{.Id}}' "$image" 2> "$run_dir/image.stderr.txt")"; then
  printf '%s\n%s\n' "$image" "$image_id" > "$run_dir/image.txt"
  command=(docker run --rm --pull never --network none --cpus=1 --memory=2g
    --user "$(id -u):$(id -g)" --volume "$run_dir:/work" --workdir /work
    "$image_id" python3 -B /work/run_inside.py)
  printf '%q ' "${command[@]}" > "$run_dir/launcher.command.txt"
  printf '\n' >> "$run_dir/launcher.command.txt"
  "${command[@]}" > "$run_dir/container.stdout.txt" 2> "$run_dir/container.stderr.txt" || rc=$?
else
  rc=$?
fi
printf '%s\n' "$rc" > "$run_dir/container.exit_code.txt"
if [[ -f "$run_dir/summary.tsv" ]]; then
  cat "$run_dir/summary.tsv"
else
  printf 'PILOT=INCOMPLETE\n'
fi
tar -czf "$archive" -C "$(dirname "$run_dir")" -- "$run_name"
printf 'ARCHIVE=%s\n' "$archive"
sha256sum "$archive"
exit "$rc"
