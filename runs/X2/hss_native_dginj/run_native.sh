#!/usr/bin/env bash
set -euo pipefail

run_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
model="$run_dir/hss_dginj_only.spthy"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'

(cd -- "$run_dir" && sha256sum -c inputs.sha256)
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" \
  > "$run_dir/image.txt"
[[ "$(cat -- "$run_dir/image.txt")" == "$image linux/amd64" ]] || exit 1

docker run --rm -i --pull never --network none --read-only \
  --entrypoint /bin/sh "$image" \
  -c 'sha256sum -c - && /usr/local/bin/tamarin-prover --version' \
  > "$run_dir/preflight.txt" 2>&1 <<'HASHES'
b942e7f58d15023bc1a7210c0bedbc0d36db921f0a54888827bca7989730f70a  /usr/local/bin/tamarin-prover
13b89491dcfeef5a0befba10db503de1937fc46279320242423fc38f1fd830a0  /usr/local/bin/maude
HASHES
cat -- "$run_dir/preflight.txt"

for lemma in exec LS7; do
  out="$run_dir/$lemma"
  mkdir -- "$out"
  cmd=(docker run --pull never --network none --read-only
    --cpus=1 --memory=8g --memory-swap=8g --pids-limit=128
    --cap-drop=ALL --security-opt=no-new-privileges
    --user "$(id -u):$(id -g)" --env HOME=/tmp --workdir /tmp
    --tmpfs /tmp:rw,nosuid,nodev,size=256m
    --cidfile "$out/container.id"
    --mount "type=bind,src=$model,dst=/input.spthy,readonly"
    --entrypoint /usr/bin/timeout "$image"
    --verbose --kill-after=5s 900s /usr/local/bin/tamarin-prover
    +RTS -N1 -M4g -RTS --with-maude=/usr/local/bin/maude
    "--prove=$lemma" /input.spthy)

  printf '%q ' "${cmd[@]}" > "$out/command.txt"
  printf '\n' >> "$out/command.txt"
  printf '\n開始 Tamarin %s\n' "$lemma"

  rc=0
  started=$SECONDS
  "${cmd[@]}" > "$out/stdout.txt" 2> "$out/stderr.txt" || rc=$?
  printf 'rc=%s\nwall_seconds_rounded=%s\n' \
    "$rc" "$((SECONDS-started))" > "$out/status.txt"

  if [[ ! -s "$out/container.id" ]]; then
    cat -- "$out/stderr.txt"
    exit 1
  fi
  cid="$(cat -- "$out/container.id")"
  inspect_rc=0
  docker inspect --type container --format '{{json .State}}' "$cid" \
    > "$out/container-state.json" 2> "$out/inspect.stderr.txt" || inspect_rc=$?
  docker rm -- "$cid" > "$out/cleanup.log" 2>&1 || true

  grep -E "^[[:space:]]*$lemma[[:space:]]+\((exists-trace|all-traces)\):" \
    "$out/stdout.txt" > "$out/result-lines.txt" || true
  cat -- "$out/status.txt" "$out/result-lines.txt"

  if [[ "$inspect_rc" != 0 || "$rc" == 12[567] ]]; then
    tail -n 12 -- "$out/stderr.txt"
    exit 1
  fi
done
