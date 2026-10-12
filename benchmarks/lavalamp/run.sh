#!/bin/bash
# Lava-lamp generation across the top models, one server at a time on :8080 (fair-context launch settings).
set -u
B=/home/riccardogiorato/Desktop/github/llamacpp-b2f036c0f/build-sm75/bin/llama-server
M=/home/riccardogiorato/models; L=/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/lavalamp
SP=/home/riccardogiorato/Desktop/github/strata-port; WT3=/home/riccardogiorato/Desktop/github/strata-0143
COMMON="--alias local-model --host 127.0.0.1 --port 8080 --parallel 1 --n-gpu-layers 999 --flash-attn on --jinja"
drain(){ local w=0; while [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -gt 100 ]; do sleep 3; w=$((w+3)); [ $w -gt 200 ] && return 1; done; }
ready(){ local i=0; until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -qE '"ok"|"loaded": true'; do sleep 5; i=$((i+5)); [ $i -gt 1500 ] && return 1; done
  for i in $(seq 1 40); do curl -s -m 120 -X POST http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"local-model","messages":[{"role":"user","content":"Say OK."}],"max_tokens":8}' | grep -q '"choices"' && return 0; sleep 5; done; return 1; }
llama(){ label=$1; shift; pkill -x llama-server; sleep 4; drain
  echo "===== $label $(date +%H:%M:%S)"; setsid $B $COMMON "$@" > /tmp/lava-$label.log 2>&1 < /dev/null &
  if ready; then python3 $L/gen.py $label "llama.cpp b11562"; else echo "$label never ready"; fi
  pkill -x llama-server; sleep 4; }
strata(){ label=$1 unit=$2 cfg=$3 cwd=$4 eng=$5; systemctl --user reset-failed $unit 2>/dev/null; drain
  echo "===== $label $(date +%H:%M:%S)"
  ( cd $cwd && systemd-run --user --unit=$unit --working-directory=$cwd python3 -m serve.server --engine strata --config $cfg --port 8080 >/dev/null )
  if ready; then sleep 10; python3 $L/gen.py $label "$eng"; else echo "$label never ready"; fi
  systemctl --user stop $unit; sleep 8; }

strata strata-125b ctx-lava-champ $SP/suite-0143-128k.json $WT3 "Strata 0.1.43"
llama qwen35-9b  -m $M/qwen35-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf --ctx-size 65536 --batch-size 512 --ubatch-size 512 -ctk q4_0 -ctv q4_0 --spec-type draft-mtp --spec-draft-n-max 4
llama a3b-35b    -m $M/qwen35-35b-a3b/Qwen3.5-35B-A3B-UD-IQ2_XXS.gguf --override-tensor "exps=CPU" --ctx-size 65536 -ctk q8_0 -ctv q8_0 --threads 6 --cache-ram 65536 --spec-type draft-mtp --spec-draft-model $M/qwen35-35b-a3b/Qwen3.5-35B-A3B-MTP-ONLY-Q4_K_M.gguf --spec-draft-n-max 4
llama qwen35-4b  -m $M/qwen35-4b-mtp/Qwen3.5-4B-Q4_K_M.gguf --ctx-size 131072 --batch-size 512 --ubatch-size 512 -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 4
llama gemma-e4b  -m $M/gemma-4-e4b-qat/gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf --ctx-size 131072 --no-warmup --spec-type draft-mtp --spec-draft-model $M/gemma-4-e4b-qat/gemma-4-E4B-it-qat-assistant-MTP-Q8_0.gguf --spec-draft-n-max 3
llama mimo-9b    -m $M/mimo-9b/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf --ctx-size 65536 --batch-size 512 --ubatch-size 512 -ctk q4_0 -ctv q4_0

# Strata Coder, 0.1.38-era engine with the full draft vocab (as in the fair-context run)
cp $SP/mtp/rt/draft_vocab.bin $SP/mtp/rt/draft_vocab.en.bak; cp $SP/data/draft_vocab.bin $SP/mtp/rt/draft_vocab.bin
strata strata-coder ctx-lava-coder suite-coder-32k.json $SP "Strata 0.1.38"
cp $SP/mtp/rt/draft_vocab.en.bak $SP/mtp/rt/draft_vocab.bin; rm -f $SP/mtp/rt/draft_vocab.en.bak
echo LAVA-DONE
