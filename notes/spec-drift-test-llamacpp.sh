#!/usr/bin/env bash
# E2 drift test — does llama.cpp MTP speculative decoding on this RTX 2080 (sm_75)
# change the target model's greedy output bytes? (The TensorFold question, posed to
# our own stack: "drafts change speed only" — or do they change bits?)
#
# Modes:
#   A = with drafter (--spec-type draft-mtp --spec-draft-n-max 2)  [the 181 tok/s recipe]
#   B = serial (no drafter flags), identical otherwise
# Each mode runs the same prompt set twice (determinism controls A1/A2, B1/B2),
# greedy (temperature 0). Compare A1==A2, B1==B2, and A1==B1.
set -u
IMAGE='ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3'
MODEL=/models/gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf
OUT=/tmp/drift_test/out
NAME=localai-drift
mkdir -p "$OUT"

start_server() {
  local draft="$1" port="$2"
  sudo docker rm -f $NAME >/dev/null 2>&1 || true
  local spec=""
  if [ "$draft" = "yes" ]; then
    spec="--spec-type draft-mtp --spec-draft-model /models/gemma-4-E4B-it-qat-assistant-MTP-Q8_0.gguf --spec-draft-n-max 2"
  fi
  sudo docker run --gpus all -p ${port}:8080 -v ~/models/gemma-4-e4b-qat:/models:ro -d --name $NAME \
    "$IMAGE" \
    --model "$MODEL" --alias drift-test \
    --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 --n-gpu-layers 999 \
    --flash-attn on --jinja --no-warmup $spec >/dev/null
  for i in $(seq 1 60); do
    if curl -s --max-time 2 http://127.0.0.1:${port}/health | grep -q '"ok"'; then
      return 0
    fi
    sleep 2
  done
  echo "server did not come up"; sudo docker logs $NAME | tail -20; exit 1
}

run_prompt() {
  local port="$1" tag="$2" id="$3" prompt="$4" npred="$5"
  # temperature 0 = greedy; same body for every run
  local body
  body=$(jq -n --arg p "$prompt" --argjson n "$npred" \
    '{prompt: $p, n_predict: $n, temperature: 0.0, cache_prompt: true}')
  local resp
  resp=$(curl -s --max-time 300 http://127.0.0.1:${port}/completion -d "$body")
  echo "$resp" | jq -r '.content' > "$OUT/${tag}-${id}.txt"
  echo "$resp" | jq -c '{tokens: .tokens_evaluated, gen: .tokens_generated, speed: .timings.predicted_per_second}' \
    > "$OUT/${tag}-${id}.meta"
}

PROMPTS=(
  "Write a Python function that checks whether a string is a palindrome, then explain how it works."
  "Explain why the sky is blue, in exactly three sentences."
  "List the steps to make espresso, then rank them by importance."
  "A farmer has 17 sheep and all but 9 run away. How many are left? Explain your reasoning step by step."
  "Translate the following into Italian and explain one grammatical choice: 'The cats that we saw yesterday were sleeping under the table.'"
  "Write a haiku about a GPU cooling fan, then explain the syllable count of each line."
)
NPRED=(220 160 180 260 220 180)

run_suite() {
  local port="$1" tag="$2"
  for i in "${!PROMPTS[@]}"; do
    run_prompt "$port" "$tag" "$i" "${PROMPTS[$i]}" "${NPRED[$i]}"
  done
}

echo "== mode A: with MTP drafter =="
start_server yes 8080
run_suite 8080 A1
run_suite 8080 A2
sudo docker rm -f $NAME >/dev/null

echo "== mode B: serial, no drafter =="
start_server no 8080
run_suite 8080 B1
run_suite 8080 B2
sudo docker rm -f $NAME >/dev/null

echo "== comparisons =="
fail=0
cd "$OUT"
echo "-- determinism within A (drafted):"
for i in 0 1 2 3 4 5; do cmp -s "A1-$i.txt" "A2-$i.txt" && echo "  prompt $i: IDENTICAL" || { echo "  prompt $i: DIFFERS"; fail=1; }; done
echo "-- determinism within B (serial):"
for i in 0 1 2 3 4 5; do cmp -s "B1-$i.txt" "B2-$i.txt" && echo "  prompt $i: IDENTICAL" || { echo "  prompt $i: DIFFERS"; fail=1; }; done
echo "-- THE TEST — drafted vs serial:"
same=0
for i in 0 1 2 3 4 5; do
  if cmp -s "A1-$i.txt" "B1-$i.txt"; then echo "  prompt $i: byte-identical"; same=$((same+1));
  else
    echo "  prompt $i: DRIFTS"
    firstdiff=$(cmp "A1-$i.txt" "B1-$i.txt" 2>&1 | head -1)
    echo "     $firstdiff"
    ac=$(wc -c < "A1-$i.txt"); bc=$(wc -c < "B1-$i.txt")
    alen=$(wc -l < "A1-$i.txt"); blen=$(wc -l < "B1-$i.txt")
    echo "     A bytes=$ac lines=$alen | B bytes=$bc lines=$blen"
  fi
done
echo "== result: $same / 6 prompts byte-identical drafted vs serial =="