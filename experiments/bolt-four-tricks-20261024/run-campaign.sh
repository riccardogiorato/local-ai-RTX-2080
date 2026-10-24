#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=experiments/bolt-four-tricks-20261024
for i in $(seq 1 360); do
  [ -f "$OUT/build-cublas-cache.txt" ] && break
  sleep 2
done
test -f "$OUT/build-cublas-cache.txt"
python3 "$OUT/bench.py" baseline mtp-d2 mtp-d3 draft-kvq8 draft-q4 native-default native-cublas > "$OUT/campaign.log" 2>&1
python3 "$OUT/cache-replay.py" > "$OUT/cache-replay.log" 2>&1
python3 "$OUT/summarize.py" > "$OUT/summary.txt"
