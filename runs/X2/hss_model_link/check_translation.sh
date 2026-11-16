#!/usr/bin/env bash
set -euo pipefail

run_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
binary="$1"
image='sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793'

printf '%s  %s\n' \
  'a07b24ef01cbd12b3eba99491d9b980f1561ec2df41a8137d0fe2f4744dbd6f5' \
  "$binary" | sha256sum -c -
(cd -- "$run_dir" && sha256sum -c inputs.sha256)

docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$image" \
  > "$run_dir/image.txt"
[[ "$(cat -- "$run_dir/image.txt")" == "$image linux/amd64" ]] || exit 1

printf 'lemma\texport_rc\tcomparison\n' > "$run_dir/comparison.tsv"
for lemma in exec LS7; do
  out="$run_dir/$lemma"
  cmd=(docker run --rm --pull never --network none --read-only
    --cpus=1 --memory=2g --memory-swap=2g --pids-limit=128
    --cap-drop=ALL --security-opt=no-new-privileges
    --user "$(id -u):$(id -g)" --env HOME=/work --workdir /work
    --tmpfs /tmp:rw,nosuid,nodev,size=128m
    --mount "type=bind,src=$run_dir,dst=/work"
    --mount "type=bind,src=$run_dir/hss_dginj_only.spthy,dst=/input.spthy,readonly"
    --mount "type=bind,src=$binary,dst=/candidate-tamarin,readonly"
    --entrypoint /usr/bin/timeout "$image"
    --verbose --kill-after=5s 60s /candidate-tamarin
    +RTS -N1 -M768m -RTS -d=0 -m=proverif
    "--lemma=$lemma" "-o=/work/$lemma/generated.pv" /input.spthy)

  printf '%q ' "${cmd[@]}" > "$out/command.txt"
  printf '\n' >> "$out/command.txt"
  rc=0
  "${cmd[@]}" > "$out/stdout.txt" 2> "$out/stderr.txt" || rc=$?

  status=NO_OUTPUT
  if [[ "$rc" -ne 0 ]]; then
    status=EXPORT_FAILED
  elif [[ -s "$out/generated.pv" ]]; then
    (cd -- "$out" && sha256sum checked.pv generated.pv > pv.sha256)
    if cmp -s -- "$out/checked.pv" "$out/generated.pv"; then
      status=BYTE_IDENTICAL
    else
      status=DIFFERS
      diff -u -- "$out/checked.pv" "$out/generated.pv" \
        > "$out/translation.diff" || [[ "$?" -eq 1 ]]
    fi
  fi
  printf '%s\t%s\t%s\n' "$lemma" "$rc" "$status" >> "$run_dir/comparison.tsv"
done

cat -- "$run_dir/comparison.tsv"
