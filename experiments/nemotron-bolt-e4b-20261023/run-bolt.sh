#!/usr/bin/env bash
# Serve Nemotron 3.5 Bolt E4B on 127.0.0.1:8080 (llama.cpp, pinned b11804).
# Stages: nodraft (default) | dflash-d4 | dflash-d7 | stop
# Port 8080 chosen to match the pi provider entry + measure-decode default;
# the standing Strata serve is NOT used or touched by this script.
set -euo pipefail
STAGE="${1:-nodraft}"
# BOLT_IMAGE overrides the engine for controlled comparisons / rollback.
IMAGE="${BOLT_IMAGE:-ghcr.io/ggml-org/llama.cpp:server-cuda12-b11804@sha256:490d8cd8000203a3ab8fdfce14ef931e2aa85affd4dd4447bcc75f299f00fd9a}"
M=/home/riccardogiorato/models/nemotron-bolt-e4b
MAIN=/models/NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf
DRAFT=/models/dflash-NVIDIA-Nemotron-3.5-Bolt-E4B-Q8_0.gguf
CTX="${BOLT_CTX:-8192}"
# BOLT_KV=q8_0 -> quantized KV cache (K+V; flash-attn is on so V quant is allowed).
# BOLT_EXTRA -> arbitrary extra llama-server flags (e.g. -ub 1024 for prefill sweeps).
# BOLT_SPEC -> speculative methods for dflash stages (default draft-dflash).
KV_ARGS=()
[ -n "${BOLT_KV:-}" ] && KV_ARGS=(--cache-type-k "$BOLT_KV" --cache-type-v "$BOLT_KV")

case "$STAGE" in
  stop)
    sudo docker rm -f bolt-serve 2>/dev/null || true
    exit 0 ;;
  nodraft) DRAFT_ARGS=() ;;
  dflash-* )
    N=${STAGE#dflash-d}
    [[ "$N" =~ ^[1-9][0-9]*$ ]] || { echo "invalid draft depth: $N"; exit 2; }
    DRAFT_ARGS=(--spec-type "${BOLT_SPEC:-draft-dflash}" --spec-draft-model "$DRAFT" --spec-draft-n-max "$N") ;;
  *) echo "unknown stage: $STAGE (nodraft | dflash-d4 | dflash-d7 | stop)"; exit 2 ;;
esac

sudo docker rm -f bolt-serve 2>/dev/null || true
sudo docker run --gpus all -p 8080:8080 -v "$M":/models:ro -d \
  --name bolt-serve "$IMAGE" \
  --model "$MAIN" --alias local-model \
  --host 0.0.0.0 --port 8080 --ctx-size "$CTX" --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --jinja --no-warmup --metrics "${DRAFT_ARGS[@]}" "${KV_ARGS[@]}" \
  ${BOLT_EXTRA:-} > /dev/null
echo "bolt-serve up (stage=$STAGE ctx=$CTX); waiting for /health..."
for i in $(seq 1 120); do
  curl -sf --max-time 2 http://127.0.0.1:8080/health >/dev/null 2>&1 && { echo "healthy after ${i}x2s"; exit 0 ; }
  sleep 2
done
echo "server did not become healthy in 240 s"; sudo docker logs --tail 40 bolt-serve; exit 1
