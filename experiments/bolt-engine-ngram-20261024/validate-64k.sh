#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=experiments/bolt-engine-ngram-20261024
RUN=experiments/nemotron-bolt-e4b-20261023/run-bolt.sh
export BOLT_IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda12-b11804@sha256:490d8cd8000203a3ab8fdfce14ef931e2aa85affd4dd4447bcc75f299f00fd9a
unset BOLT_SPEC BOLT_EXTRA BOLT_KV
restore_failure() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    export BOLT_IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3
    BOLT_CTX=65536 bash "$RUN" dflash-d4 > "$OUT/validation-rollback.log" 2>&1
  fi
  exit "$rc"
}
trap restore_failure EXIT
BOLT_CTX=65536 bash "$RUN" dflash-d4 > "$OUT/new-64k-d4-boot.log" 2>&1
python3 "$OUT/measure.py" new-64k-d4 > "$OUT/new-64k-d4-summary.log" 2>&1
BOLT_PROBE_OUT="$OUT/new-64k-d4-probes.jsonl" python3 experiments/nemotron-bolt-e4b-20261023/probe-bolt.py > "$OUT/new-64k-d4-probes.log" 2>&1
sudo docker logs bolt-serve > "$OUT/new-64k-d4-server.log" 2>&1
sudo docker inspect bolt-serve --format '{{.Config.Image}} {{json .Config.Cmd}}' > "$OUT/new-64k-d4-config.txt"
nvidia-smi --query-compute-apps=pid,used_memory --format=csv > "$OUT/new-64k-d4-vram.txt"
