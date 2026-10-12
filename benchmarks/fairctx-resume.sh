#!/bin/bash
# Resume the fair-context chain after the champion run was cut at 9/11: finish task8+task9 on the SAME live
# ctx-champ serve, merge, then the Strata Coder 32K arm, then mark FAIRCTX-DONE (which releases oc47-test.sh).
set -u
REPO=/home/riccardogiorato/Desktop/github/local-ai-rtx2080; BENCH=$REPO/benchmarks; SP=/home/riccardogiorato/Desktop/github/strata-port
RUNLOG=$BENCH/results/fairctx-ram3200-20261012.runner.log
drain(){ local w=0; while [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -gt 100 ]; do sleep 3; w=$((w+3)); [ $w -gt 200 ] && return 1; done; return 0; }
summ(){ python3 -c "
import json; rows=[json.loads(l) for l in open('$1')]
print('== $2', f'{sum(r[\"passed\"] for r in rows)}/{len(rows)} wall {sum(r[\"wall_s\"] for r in rows)}s', 'misses:', [r['task'].split('-tb-')[0] for r in rows if not r['passed']])"; }
PART=$(ls -t $BENCH/results/strata-q20-128k-0143-v22-2*.jsonl | head -1)
echo "== resume $(date +%H:%M:%S): champion partial $PART ($(wc -l < $PART) tasks), finishing task8+task9 on the live serve" >> $RUNLOG
curl -s -m 5 http://127.0.0.1:8080/health | grep -q '"loaded": true' || { echo "champion serve not up - aborting resume" >> $RUNLOG; exit 1; }
( cd $BENCH && TASK_RE='task(8|9)-' WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh strata-q20-128k-0143-v22-tail 900 < /dev/null > /tmp/strata-128k-tail.stdout 2>&1 )
TAIL=$(ls -t $BENCH/results/strata-q20-128k-0143-v22-tail-2*.jsonl | head -1)
MERGED=${PART%.jsonl}-merged.jsonl; cat $PART $TAIL > $MERGED
summ $MERGED strata-q20-128k-0143-v22 >> $RUNLOG
echo "   (9 tasks from $(basename $PART) + 2 from $(basename $TAIL), same ctx-champ serve boot)" >> $RUNLOG
systemctl --user stop ctx-champ 2>/dev/null; sleep 8; drain || true
# Strata Coder @32K (0.1.38 engine, full draft vocab for era accuracy)
cp $SP/mtp/rt/draft_vocab.bin $SP/mtp/rt/draft_vocab.en.bak; cp $SP/data/draft_vocab.bin $SP/mtp/rt/draft_vocab.bin
python3 - <<'PY'
import json
c=json.load(open("/home/riccardogiorato/Desktop/github/strata-port/strata-coder-iq1m.json"))
a=c["args"]; a[a.index("--max-context")+1]="32768"; a[a.index("--prefill")+1]="auto:32768"
c["host"]="127.0.0.1"; c["log"]="suite-coder-32k.log"
json.dump(c,open("/home/riccardogiorato/Desktop/github/strata-port/suite-coder-32k.json","w"), indent=2)
PY
systemctl --user reset-failed ctx-coder 2>/dev/null
echo "===== strata-coder-32k-0138-v22 $(date +%H:%M:%S)" >> $RUNLOG
( cd $SP && systemd-run --user --unit=ctx-coder --working-directory=$SP python3 -m serve.server --engine strata --config suite-coder-32k.json --port 8080 >/dev/null )
i=0; until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; do sleep 5; i=$((i+5)); [ "$(systemctl --user is-active ctx-coder)" = active ] || break; [ $i -gt 1200 ] && break; done
if curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; then
  sleep 15
  ( cd $BENCH && WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh strata-coder-32k-0138-v22 900 < /dev/null > /tmp/coder-32k.stdout 2>&1 )
  grep -m1 -E 'warm-up attempt 1|ABORT' /tmp/coder-32k.stdout >> $RUNLOG
  f=$(ls -t $BENCH/results/strata-coder-32k-0138-v22-2*.jsonl 2>/dev/null | head -1); [ -n "$f" ] && summ $f strata-coder-32k-0138-v22 >> $RUNLOG
else echo "coder 32K: never ready ($(tail -2 $SP/suite-coder-32k.log 2>/dev/null | tr '\n' ' ' | cut -c1-200))" >> $RUNLOG; fi
systemctl --user stop ctx-coder 2>/dev/null; sleep 6
cp $SP/mtp/rt/draft_vocab.en.bak $SP/mtp/rt/draft_vocab.bin; rm -f $SP/mtp/rt/draft_vocab.en.bak
echo "EN draft vocab restored: $(stat -c %s $SP/mtp/rt/draft_vocab.bin) bytes" >> $RUNLOG
echo FAIRCTX-DONE >> $RUNLOG
