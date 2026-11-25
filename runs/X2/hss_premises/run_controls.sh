#!/usr/bin/env bash
set -euo pipefail

input="$1"
run_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'
pv_sha='f6b5e9606e639350085167f150e6bca7adfcdac0b34614b890e72f7f9e0c1c28'

docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" \
  > "$run_dir/image.txt"
cat -- "$run_dir/image.txt"
[[ "$(cat -- "$run_dir/image.txt")" == "$image linux/amd64" ]] || exit 1

printf '%s  /usr/local/bin/proverif\n' "$pv_sha" |
  docker run --rm -i --pull never --network none --read-only \
    --entrypoint /bin/sh "$image" \
    -c 'sha256sum -c - && /usr/bin/timeout --version' \
    > "$run_dir/preflight.txt" 2>&1 || {
      cat -- "$run_dir/preflight.txt"
      exit 1
    }
head -n 2 -- "$run_dir/preflight.txt"

for lemma in exec LS7; do
  for variant in dginj_only topauth_only; do
    out="$run_dir/$lemma/$variant"
    mkdir -p -- "$run_dir/$lemma"
    mkdir -- "$out"
    cp -- "$input/results/hss_noinj/$lemma/$variant/translated.pv" "$out/input.pv"
    (cd -- "$out" && sha256sum input.pv > input.sha256)

    cmd=(docker run --pull never --network none --read-only
      --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128
      --cap-drop=ALL --security-opt=no-new-privileges
      --user "$(id -u):$(id -g)" --env HOME=/tmp --workdir /tmp
      --tmpfs /tmp:rw,nosuid,nodev,size=128m
      --cidfile "$out/container.id"
      --mount "type=bind,src=$out/input.pv,dst=/input.pv,readonly"
      --entrypoint /usr/bin/timeout "$image"
      --verbose --kill-after=5s 300s /usr/local/bin/proverif /input.pv)

    printf '%q ' "${cmd[@]}" > "$out/command.txt"
    printf '\n' >> "$out/command.txt"
    printf '\nStart hss_noinj/%s/%s\n' "$lemma" "$variant"

    rc=0
    started=$SECONDS
    "${cmd[@]}" > "$out/stdout.txt" 2> "$out/stderr.txt" || rc=$?
    printf 'rc=%s\nwall_seconds_rounded=%s\n' \
      "$rc" "$((SECONDS-started))" > "$out/status.txt"

    inspect_rc=1
    if [[ -s "$out/container.id" ]]; then
      cid="$(cat -- "$out/container.id")"
      inspect_rc=0
      docker inspect --type container --format '{{json .State}}' "$cid" \
        > "$out/container-state.json" 2> "$out/inspect.stderr.txt" || inspect_rc=$?
      docker rm -- "$cid" > "$out/cleanup.log" 2>&1 || true
    fi

    grep '^RESULT ' "$out/stdout.txt" > "$out/result-lines.txt" || true
    cat -- "$out/status.txt" "$out/result-lines.txt"
    grep -E '^([^ ]*/)?timeout: sending signal' "$out/stderr.txt" || true
    if [[ "$inspect_rc" != 0 || ( "$rc" != 0 && "$rc" != 124 && "$rc" != 137 ) ]]; then
      tail -n 12 -- "$out/stderr.txt"
      exit 1
    fi
  done
done
