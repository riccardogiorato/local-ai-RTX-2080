#!/usr/bin/env bash
set -euo pipefail
SRC=/tmp/bolt-b11804-tricks
OUT="$(cd "$(dirname "$0")" && pwd)"
for mode in default cublas; do
  force=OFF; [ "$mode" = cublas ] && force=ON
  cmake -S "$SRC" -B "$SRC/build-$mode" -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DGGML_CUDA_FORCE_CUBLAS="$force" -DGGML_CUDA_NCCL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_NUMBER=11804 -DLLAMA_BUILD_COMMIT=c7fc50941 > "$OUT/build-$mode-config.log" 2>&1
  cmake --build "$SRC/build-$mode" --target llama-server llama-quantize -j 6 > "$OUT/build-$mode.log" 2>&1
  cp "$SRC/build-$mode/CMakeCache.txt" "$OUT/build-$mode-cache.txt"
done
