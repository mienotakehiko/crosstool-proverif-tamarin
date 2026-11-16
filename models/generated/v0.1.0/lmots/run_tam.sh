#!/bin/bash
export LC_ALL=C.UTF-8
for v in base rb1 cl1; do for l in exec_accept LS1_unforge forge; do
  s=$(date +%s)
  timeout 200 tamarin-prover +RTS -M1400m -RTS --prove=$l LMOTS_T_$v.spthy > tam_${v}_$l.out 2>&1; rc=$?
  r=$(grep -E "^  $l .*(verified|falsified|analysis incomplete)" tam_${v}_$l.out | head -1 | sed 's/^ *//')
  echo "$v $l rc=$rc t=$(( $(date +%s)-s ))s | $r"
done; done
echo DONE
