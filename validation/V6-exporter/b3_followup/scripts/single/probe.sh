#!/usr/bin/env bash
set -eu -o pipefail
kit=$(cd -- "$(dirname -- "$0")" && pwd)
mode=${1:-}
case "$mode" in
  b2|b0) test "$#" -eq 2 ;;
  b3) test "$#" -eq 3 ;;
  *) echo "Usage: bash probe.sh {b2|b0} NEW_DIR ; bash probe.sh b3 NEW_DIR BUILD/candidate/tamarin-prover" >&2; exit 2 ;;
esac
b2='sha256:38fffe6dff4d9c2b2757c43e3df20be1f21a57751183d7e803fa02829e77545b'
b0='sha256:540c245a3bc36569bb8f546ca664bd1f97205aee9658c7594dc86bffcdc5e6c8'
img=$b2
if [[ $mode == b0 ]]; then img=$b0; fi
original=$img
img=${SECTION8_IMAGE_ID:-$original}
if ! [[ $img =~ ^sha256:[a-f0-9]{64}$ ]]; then
  echo 'Use a complete immutable local image ID.' >&2
  exit 2
fi
mkdir -- "$2"
out=$(cd -- "$2" && pwd)
exec > >(tee "$out/session.log") 2>&1
echo "OUT=$out"
printf 'reference_image=%s\nused_image=%s\n' "$original" "$img" | tee "$out/image-selection.txt"
docker context show
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$img" | tee "$out/image.txt"
grep -Fxq "$img linux/amd64" "$out/image.txt"
args=()
digest=-
if [[ $mode == b3 ]]; then
  binary=$(realpath -- "$3")
  test -x "$binary" && test "$(basename -- "$binary")" = tamarin-prover || exit 2
  (cd -- "$(dirname -- "$binary")" && sha256sum --check tamarin-prover.sha256)
  read -r digest _ < "$(dirname -- "$binary")/tamarin-prover.sha256"
  args+=(--mount "type=bind,src=$binary,dst=/opt/section8-b3,readonly")
fi
rc=0
docker run --rm -i --pull never --network none --user "$(id -u):$(id -g)" \
  --env HOME=/tmp --workdir /out --memory=8g --memory-swap=8g \
  --mount "type=bind,src=$out,dst=/out" "${args[@]}" \
  --entrypoint python3 "$img" -B - "$mode" "$digest" < "$kit/inside.py" || rc=$?
echo "$rc" > "$out/container.rc"
echo "container_rc=$rc"
exit "$rc"
