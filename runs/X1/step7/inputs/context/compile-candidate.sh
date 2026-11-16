#!/bin/sh
set -eu

variant=$1
case "$variant" in
  candidate) expected='53beed7363c1f069326c326428050daa269a5ff3c3e7ad5b46ed5bdd4b1048eb' ;;
  *) exit 2 ;;
esac

cd /opt/build
rule='lib/export/src/Export/ProVerif/Rule.hs'
out="/build-evidence/$variant"
mkdir "$out"
printf '%s  %s\n' "$expected" "$rule" | sha256sum -c -
sha256sum "$rule" > "$out/Rule.hs.sha256"
# Use the same source tree path and Stack flags as Step 3.
stack install --system-ghc --local-bin-path /opt/build/bin
cp /opt/build/bin/tamarin-prover "$out/tamarin-prover"
strip "$out/tamarin-prover"
(cd "$out" && sha256sum tamarin-prover > tamarin-prover.sha256)
