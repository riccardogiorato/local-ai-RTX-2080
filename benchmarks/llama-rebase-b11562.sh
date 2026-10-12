#!/bin/bash
set -u
B=/home/riccardogiorato/Desktop/github/llamacpp-b2f036c0f/build-sm75/bin/llama-server
M=/home/riccardogiorato/models; BENCH=/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks
COMMON="--alias local-model --host 127.0.0.1 --port 8080 --parallel 1 --n-gpu-layers 999 --flash-attn on --jinja"
drain(){ local w=0; while [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -gt 100 ]; do sleep 3; w=$((w+3)); [ $w -gt 150 ] && return 1; done; return 0; }
ready(){ local i=0; until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; do sleep 5; i=$((i+5)); pgrep -x llama-server >/dev/null || return 1; [ $i -gt 900 ] && return 1; done
  for i in $(seq 1 60); do curl -s -m 120 -X POST http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"local-model","messages":[{"role":"user","content":"Say OK."}],"max_tokens":8}' | grep -q '"choices"' && return 0; sleep 5; done; return 1; }
run(){ label=$1; shift
  pkill -x llama-server; sleep 4; drain || echo "WARN gpu not drained"
  echo "===== $label $(date +%H:%M:%S)"
  setsid $B $COMMON "$@" > /tmp/$label.server.log 2>&1 < /dev/null &
  if ready; then echo "VRAM $(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader | head -1)"
    ( cd $BENCH && WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh $label 900 < /dev/null > /tmp/$label.stdout 2>&1 )
    grep -E 'warm-up|ABORT' /tmp/$label.stdout | head -2
    f=$(ls -t $BENCH/results/$label-2*.jsonl 2>/dev/null | head -1); [ -n "$f" ] && python3 -c "
import json; rows=[json.loads(l) for l in open('$f')]
print('== $label', f'{sum(r[\"passed\"] for r in rows)}/{len(rows)} wall {sum(r[\"wall_s\"] for r in rows)}s', 'fails:', [r['task'].split('-')[0] for r in rows if not r['passed']])"
  else echo "$label: server never ready"; tail -5 /tmp/$label.server.log; fi
  pkill -x llama-server; sleep 4; }
run qwen35-4b-b11562-v22  -m $M/qwen35-4b-mtp/Qwen3.5-4B-Q4_K_M.gguf --ctx-size 32768 --batch-size 512 --ubatch-size 512 -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 4
run gemma-e4b-b11562-v22  -m $M/gemma-4-e4b-qat/gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf --ctx-size 131072 --no-warmup --spec-type draft-mtp --spec-draft-model $M/gemma-4-e4b-qat/gemma-4-E4B-it-qat-assistant-MTP-Q8_0.gguf --spec-draft-n-max 3
run qwen35-9b-b11562-v22  -m $M/qwen35-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf --ctx-size 32768 --batch-size 512 --ubatch-size 512 -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 4
run mimo-9b-b11562-v22    -m $M/mimo-9b/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf --ctx-size 32768 --batch-size 512 --ubatch-size 512 -ctk q8_0 -ctv q8_0
run a3b-iq2xxs-b11562-v22 -m $M/qwen35-35b-a3b/Qwen3.5-35B-A3B-UD-IQ2_XXS.gguf --override-tensor "exps=CPU" --ctx-size 32768 -ctk q8_0 -ctv q8_0 --threads 6 --cache-ram 32768 --spec-type draft-mtp --spec-draft-model $M/qwen35-35b-a3b/Qwen3.5-35B-A3B-MTP-ONLY-Q4_K_M.gguf --spec-draft-n-max 4
echo LLAMA-REBASE-DONE
