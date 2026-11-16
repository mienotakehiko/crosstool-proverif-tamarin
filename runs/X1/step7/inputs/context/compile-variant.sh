#!/bin/sh
set -eu

variant=$1
case "$variant" in
  baseline) expected='faa7042e95c3ffb45b033de161abd17b006e268b534e699e9ccbe8a784c30b56' ;;
  candidate) expected='ccf63a271655fd1900a990a4a54be6ce28ebf26b26dc198e74ca9f0a29871d2c' ;;
  *) exit 2 ;;
esac

cd /opt/build
rule='lib/export/src/Export/ProVerif/Rule.hs'
out="/build-evidence/$variant"
mkdir "$out"
printf '%s  %s\n' "$expected" "$rule" | sha256sum -c -
sha256sum "$rule" > "$out/Rule.hs.sha256"
# Both variants use the same source tree path, flags and dependencies.
stack install --system-ghc --local-bin-path /opt/build/bin
cp /opt/build/bin/tamarin-prover "$out/tamarin-prover"
strip "$out/tamarin-prover"
(cd "$out" && sha256sum tamarin-prover > tamarin-prover.sha256)
