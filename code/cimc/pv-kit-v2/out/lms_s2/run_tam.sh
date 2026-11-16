#!/bin/bash
export LC_ALL=C.UTF-8
for v in rb1 cl1; do for l in LS4_pure LS4 LS1 LS3_forge; do
  s=$(date +%s)
  timeout 240 tamarin-prover +RTS -M1400m -RTS --prove=$l LMS_S2_T_$v.spthy > tam_${v}_$l.out 2>&1; rc=$?
  r=$(grep -E "^  $l .*(verified|falsified|analysis incomplete)" tam_${v}_$l.out | head -1 | sed 's/^ *//')
  [ $rc = 251 ] && r=HEAP; [ $rc = 124 ] && r=TIMEOUT
  echo "$v $l rc=$rc t=$(( $(date +%s)-s ))s | $r"
done; done
