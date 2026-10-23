#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=experiments/bolt-engine-ngram-20261024
RUN=experiments/nemotron-bolt-e4b-20261023/run-bolt.sh
export BOLT_IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda12-b11804@sha256:490d8cd8000203a3ab8fdfce14ef931e2aa85affd4dd4447bcc75f299f00fd9a
export BOLT_CTX=8192
restore() { unset BOLT_SPEC BOLT_EXTRA; BOLT_IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 BOLT_CTX=65536 bash "$RUN" dflash-d4 > "$OUT/restore.log" 2>&1; }
trap restore EXIT
for label in new-d4 new-ngram-simple-d4 new-ngram-map-d4; do
  unset BOLT_EXTRA
  case "$label" in
    new-d4) export BOLT_SPEC=draft-dflash ;;
    new-ngram-simple-d4) export BOLT_SPEC=ngram-simple,draft-dflash; export BOLT_EXTRA='--spec-ngram-simple-size-n 4 --spec-ngram-simple-size-m 8' ;;
    new-ngram-map-d4) export BOLT_SPEC=ngram-map-k,draft-dflash; export BOLT_EXTRA='--spec-ngram-map-k-size-n 4 --spec-ngram-map-k-size-m 8' ;;
  esac
  bash "$RUN" dflash-d4 > "$OUT/$label-boot.log" 2>&1
  sudo docker inspect bolt-serve --format '{{.Config.Image}} {{json .Config.Cmd}}' > "$OUT/$label-config.txt"
  python3 "$OUT/measure.py" "$label" > "$OUT/$label-summary.log" 2>&1
  sudo docker logs bolt-serve > "$OUT/$label-server.log" 2>&1
  nvidia-smi --query-compute-apps=pid,used_memory --format=csv > "$OUT/$label-vram.txt"
done
