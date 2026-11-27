#!/usr/bin/env bash
set -euo pipefail
kit=$(cd -- "$(dirname -- "$0")" && pwd)
rule='lib/export/src/Export/ProVerif/Rule.hs'
old='53beed7363c1f069326c326428050daa269a5ff3c3e7ad5b46ed5bdd4b1048eb'
b2bin='a07b24ef01cbd12b3eba99491d9b980f1561ec2df41a8137d0fe2f4744dbd6f5'
commit='c293106913ccf7bb41f49b0dc555a8074e8ea88c'
check_archive () {
  printf '%s  %s\n' "$1" "$2" | sha256sum --check -
}
case "${1:-}" in
prepare)
  test "$#" -eq 3
  patch=$(realpath -- "$2")
  test -s "$patch"
  archive="$kit/reference/ccs26_step7_20261115.zip"
  check_archive '06fdccdd13c59d5004952766bf4e0c7cf1c515d2931bcabd450bc7da4bbbe10d' "$archive"
  mkdir -- "$3"
  cd -- "$3"
  root=$PWD
  unzip -qo "$archive"
  (cd ccs26_step7_20261115 && sha256sum --quiet --check SHA256SUMS)
  cp -a ccs26_step7_20261115/context .
  mkdir -p "tree/$(dirname -- "$rule")"
  cp context/Rule.candidate.hs "tree/$rule"
  cp -- "$patch" input.patch
  sha256sum input.patch > input.patch.sha256
  git -C tree init -q
  git -C tree apply --numstat "$root/input.patch" > patch-files.tsv
  if [[ "$(cut -f3- patch-files.tsv)" != "$rule" ]]; then
    echo 'Expected a patch for lib/export/src/Export/ProVerif/Rule.hs only. Inspect patch-files.tsv.' >&2
    exit 2
  fi
  git -C tree apply --check "$root/input.patch"
  git -C tree apply "$root/input.patch"
  cp -- "tree/$rule" context/Rule.candidate.hs
  new=$(sha256sum context/Rule.candidate.hs | cut -d' ' -f1)
  test "$new" != "$old"
  diff_rc=0
  diff -u ccs26_step7_20261115/context/Rule.candidate.hs context/Rule.candidate.hs > changes.diff || diff_rc=$?
  test "$diff_rc" = 1
  python3 - "$old" "$new" <<'PY'
from pathlib import Path
import sys
p = Path("context/compile-candidate.sh")
s = p.read_text()
assert s.count(sys.argv[1]) == 1, "Unexpected original build pin"
p.write_text(s.replace(sys.argv[1], sys.argv[2]))
PY
  (cd context && sha256sum Dockerfile Rule.candidate.hs compile-candidate.sh compile-variant.sh) > context.sha256
  echo "Inspect $root/changes.diff before running build."
  ;;
build)
  test "$#" -eq 2
  cd -- "$2"
  (cd context && sha256sum --check ../context.sha256)
  test ! -e build || { echo 'Choose a new preparation directory, or inspect the existing build.' >&2; exit 2; }
  docker buildx build --platform linux/amd64 --progress plain \
    --build-arg "TAMARIN_REF=$commit" --output "type=local,dest=$PWD/build" context 2>&1 | tee build.log
  (cd build/candidate && sha256sum --check tamarin-prover.sha256)
  read -r source_hash _ < build/candidate/Rule.hs.sha256
  read -r actual_hash _ < <(sha256sum context/Rule.candidate.hs)
  test "$source_hash" = "$actual_hash"
  [[ "$(cat build/metadata/source.commit)" = "$commit" ]]
  read -r binary_hash _ < build/candidate/tamarin-prover.sha256
  test "$binary_hash" != "$b2bin"
  echo "B3_BINARY=$PWD/build/candidate/tamarin-prover"
  ;;
x1)
  test "$#" -eq 3
  binary=$(realpath -- "$2")
  test -x "$binary" && test "$(basename -- "$binary")" = tamarin-prover
  (cd "$(dirname -- "$binary")" && sha256sum --check tamarin-prover.sha256)
  read -r new _ < "$(dirname -- "$binary")/tamarin-prover.sha256"
  test "$new" != "$b2bin"
  archive="$kit/reference/ccs26_step8_20261115.zip"
  check_archive '7dfe43adf9386fa4f43057ac3ecde3340d34eb2e5ede36e27da3c77e3e7cdd1a' "$archive"
  mkdir -- "$3"
  cd -- "$3"
  unzip -qo "$archive"
  cd ccs26_step8_20261115
  sha256sum --quiet --check SHA256SUMS
  cp SHA256SUMS ../SHA256SUMS.b2
  cp candidate-binary.sha256 ../candidate-binary.b2.sha256
  python3 - "$b2bin" "$new" <<'PY'
import hashlib
from pathlib import Path
import sys
pin = Path("candidate-binary.sha256")
old = pin.read_bytes()
old_hash = hashlib.sha256(old).hexdigest()
assert old.decode().split() == [sys.argv[1], "tamarin-prover"]
pin.write_bytes(old.replace(sys.argv[1].encode(), sys.argv[2].encode()))
mf = Path("SHA256SUMS")
old_entry = old_hash + "  ./candidate-binary.sha256"
s = mf.read_text()
assert s.splitlines().count(old_entry) == 1
mf.write_text(s.replace(old_entry, hashlib.sha256(pin.read_bytes()).hexdigest() + "  ./candidate-binary.sha256"))
PY
  bash run-step8.sh "$binary" 2>&1 | tee ../x1.log
  ;;
*) echo 'Usage: b3.sh prepare CANDIDATE_PATCH NEW_DIR | build PREPARED_DIR | x1 B3_BINARY NEW_DIR' >&2; exit 2 ;;
esac
