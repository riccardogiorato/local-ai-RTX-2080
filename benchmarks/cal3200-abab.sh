#!/bin/bash
cd /home/riccardogiorato/Desktop/github/local-ai-rtx2080
SP=/home/riccardogiorato/Desktop/github/strata-port; OUT=benchmarks/results/strata-0143-cal3200-abab-20261012
for arm in current defaults current defaults; do
  cfg=$SP/strata-q20-gsq-01401-tailnet.json; [ $arm = defaults ] && cfg=$SP/cal3200-defaults.json
  python3 benchmarks/strata-env-probe.py $cfg $OUT-$arm.json "[[\"$arm\",{}]]" < /dev/null >> /tmp/cal3200-abab.out 2>&1
done
echo ABAB-DONE >> /tmp/cal3200-abab.out
