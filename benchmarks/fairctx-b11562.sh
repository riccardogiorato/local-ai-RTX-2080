#!/bin/bash
set -u
B=/home/riccardogiorato/Desktop/github/llamacpp-b2f036c0f/build-sm75/bin/llama-server
M=/home/riccardogiorato/models; BENCH=/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks
SP=/home/riccardogiorato/Desktop/github/strata-port; WT3=/home/riccardogiorato/Desktop/github/strata-0143
COMMON="--alias local-model --host 127.0.0.1 --port 8080 --parallel 1 --n-gpu-layers 999 --flash-attn on --jinja"
drain(){ local w=0; while [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -gt 100 ]; do sleep 3; w=$((w+3)); [ $w -gt 200 ] && return 1; done; return 0; }
llama_ready(){ local i=0
  until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; do sleep 5; i=$((i+5)); pgrep -x llama-server >/dev/null || return 1; [ $i -gt 600 ] && return 1; done
  for i in $(seq 1 40); do curl -s -m 120 -X POST http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"local-model","messages":[{"role":"user","content":"Say OK."}],"max_tokens":8}' | grep -q '"choices"' && return 0; sleep 5; done; return 1; }
run_llama(){ label=$1; shift
  pkill -x llama-server 2>/dev/null; sleep 4; drain || echo "WARN gpu not drained"
  echo "===== $label $(date +%H:%M:%S)"
  setsid $B $COMMON "$@" > /tmp/$label.server.log 2>&1 < /dev/null &
  if llama_ready; then echo "VRAM $(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader | head -1)"
    ( cd $BENCH && WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh $label 900 < /dev/null > /tmp/$label.stdout 2>&1 )
    grep -E 'warm-up attempt 1|ABORT' /tmp/$label.stdout | head -1
    f=$(ls -t $BENCH/results/$label-2*.jsonl 2>/dev/null | head -1); [ -n "$f" ] && python3 -c "
import json; rows=[json.loads(l) for l in open('$f')]
print('== $label', f'{sum(r[\"passed\"] for r in rows)}/{len(rows)} wall {sum(r[\"wall_s\"] for r in rows)}s', 'misses:', [r['task'].split('-tb-')[0].replace('task','t') for r in rows if not r['passed']])"
  else echo "$label: server never ready"; tail -4 /tmp/$label.server.log | cut -c1-160; fi
  pkill -x llama-server 2>/dev/null; sleep 4; }
suite(){ f=$1; python3 -c "
import json; rows=[json.loads(l) for l in open('$f')]
print('== '$(basename $f), f'{sum(r[\"passed\"] for r in rows)}/{len(rows)} wall {sum(r[\"wall_s\"] for r in rows)}s', 'misses:', [r['task'].split('-tb-')[0].replace('task','t') for r in rows if not r['passed']])"; }

run_llama qwen35-9b-64k-b11562-v22  -m $M/qwen35-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf --ctx-size 65536 --batch-size 512 --ubatch-size 512 -ctk q4_0 -ctv q4_0 --spec-type draft-mtp --spec-draft-n-max 4
run_llama mimo-9b-64k-b11562-v22    -m $M/mimo-9b/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf --ctx-size 65536 --batch-size 512 --ubatch-size 512 -ctk q4_0 -ctv q4_0
run_llama qwen35-4b-128k-b11562-v22  -m $M/qwen35-4b-mtp/Qwen3.5-4B-Q4_K_M.gguf --ctx-size 131072 --batch-size 512 --ubatch-size 512 -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 4
run_llama a3b-iq2xxs-64k-b11562-v22 -m $M/qwen35-35b-a3b/Qwen3.5-35B-A3B-UD-IQ2_XXS.gguf --override-tensor "exps=CPU" --ctx-size 65536 -ctk q8_0 -ctv q8_0 --threads 6 --cache-ram 65536 --spec-type draft-mtp --spec-draft-model $M/qwen35-35b-a3b/Qwen3.5-35B-A3B-MTP-ONLY-Q4_K_M.gguf --spec-draft-n-max 4

# --- Strata champion at 128K (tuned chat config, localhost-bound copy) ---
python3 - <<'PY'
import json
c=json.load(open("/home/riccardogiorato/Desktop/github/strata-port/strata-q20-gsq-01401-tailnet.json"))
c["host"]="127.0.0.1"; c["log"]="suite-0143-128k.log"
json.dump(c,open("/home/riccardogiorato/Desktop/github/strata-port/suite-0143-128k.json","w"), indent=2)
print("champion 128K ctx:", c["args"][c["args"].index("--max-context")+1])
PY
systemctl --user stop 'ctx-*' 2>/dev/null; systemctl --user reset-failed 'ctx-*' 2>/dev/null; sleep 5; drain || true
echo "===== strata-q20-128k-0143-v22 $(date +%H:%M:%S)"
systemd-run --user --unit=ctx-champ --working-directory=$WT3 python3 -m serve.server --engine strata --config $SP/suite-0143-128k.json --port 8080 >/dev/null
i=0; until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"loaded": true'; do sleep 5; i=$((i+5)); [ $i -gt 1500 ] && { echo TIMEOUT; break; }; done
sleep 15
( cd $BENCH && WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh strata-q20-128k-0143-v22 900 < /dev/null > /tmp/strata-128k.stdout 2>&1 )
grep -E 'warm-up attempt 1|ABORT' /tmp/strata-128k.stdout | head -1
f=$(ls -t $BENCH/results/strata-q20-128k-0143-v22-2*.jsonl 2>/dev/null | head -1); [ -n "$f" ] && suite $f
systemctl --user stop ctx-champ 2>/dev/null; sleep 8; drain || true

# --- Strata Coder at 32K (era 0.1.38 engine, full draft vocab for era accuracy) ---
cp $SP/mtp/rt/draft_vocab.bin $SP/mtp/rt/draft_vocab.en.bak
cp $SP/data/draft_vocab.bin $SP/mtp/rt/draft_vocab.bin
python3 - <<'PY'
import json
c=json.load(open("/home/riccardogiorato/Desktop/github/strata-port/strata-coder-iq1m.json"))
a=c["args"]; a[a.index("--max-context")+1]="32768"; a[a.index("--prefill")+1]="auto:32768"
c["host"]="127.0.0.1"; c["log"]="suite-coder-32k.log"
json.dump(c,open("/home/riccardogiorato/Desktop/github/strata-port/suite-coder-32k.json","w"), indent=2)
print("coder 32K configured")
PY
systemctl --user reset-failed ctx-coder 2>/dev/null
echo "===== strata-coder-32k-0138-v22 $(date +%H:%M:%S)"
( cd $SP && systemd-run --user --unit=ctx-coder --working-directory=$SP python3 -m serve.server --engine strata --config suite-coder-32k.json --port 8080 >/dev/null )
i=0; ok=0
until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; do sleep 5; i=$((i+5)); [ $i -gt 1200 ] && break; done
if curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; then ok=1; fi
if [ $ok = 1 ]; then
  sleep 15
  ( cd $BENCH && WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh strata-coder-32k-0138-v22 900 < /dev/null > /tmp/coder-32k.stdout 2>&1 )
  grep -E 'warm-up attempt 1|ABORT' /tmp/coder-32k.stdout | head -1
  f=$(ls -t $BENCH/results/strata-coder-32k-0138-v22-2*.jsonl 2>/dev/null | head -1); [ -n "$f" ] && suite $f
else echo "coder 32K: never ready"; tail -5 $SP/suite-coder-32k.log 2>/dev/null | cut -c1-160; fi
systemctl --user stop ctx-coder 2>/dev/null; sleep 6
cp $SP/mtp/rt/draft_vocab.en.bak $SP/mtp/rt/draft_vocab.bin; rm -f $SP/mtp/rt/draft_vocab.en.bak
echo "EN draft vocab restored: $(stat -c %s $SP/mtp/rt/draft_vocab.bin) bytes"
echo FAIRCTX-DONE
