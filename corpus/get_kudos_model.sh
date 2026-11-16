#!/usr/bin/env bash
set -euo pipefail
output=${1:?Usage: get_kudos_model.sh OUTPUT_FILE}
temporary="$(mktemp)"
trap 'rm -f -- "$temporary"' EXIT
base=https://raw.githubusercontent.com/rikard-sics/kudos-tamarin-model
curl --fail --silent --show-error --location "$base/bfe9bd09ba42/KUDOS.spthy" --output "$temporary"
printf '%s  %s\n' e5933f73453dd9fa4b7e576f6631e351b1bae6d45fa47d8b01619c996d179652 "$temporary" | sha256sum -c -
cp -- "$temporary" "$output"
