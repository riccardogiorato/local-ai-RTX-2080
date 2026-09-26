#!/usr/bin/env bash
# ub-prefill-sweep.sh — Phase 1 of the UBBoost investigation:
# plain -ub/-b sweep on a served model; tests how much of UBBoost's claimed
# prefill gain is just "bigger ubatch" on this card.
# Usage: ub-prefill-sweep.sh <label>   (server must ALREADY be up on :8080
#        with the model under test; this script only measures)
set -euo pipefail
LABEL="${1:?label}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

python3 - "$REPO" <<'PYEOF'
import json, sys, time, urllib.request
repo = sys.argv[1]
text = open(f"{repo}/prompts/code-continuation.txt", encoding="utf-8").read()
# a LONG fresh prompt class for prefill: the 512-token llama-bench-equivalent
# is what public tables use; server-timing gives prompt_per_second directly.
rows = []
for i in range(3):
    body = json.dumps({"prompt": text, "n_predict": 32, "temperature": 0,
                       "cache_prompt": False, "stream": False}).encode()
    t0 = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:8080/completion", data=body,
        headers={"Content-Type": "application/json"}), timeout=900))
    t = r["timings"]
    rows.append({"run": i+1, "prompt_n": t["prompt_n"],
                 "prefill_tps": round(t["prompt_per_second"], 1),
                 "decode_tps": round(t["predicted_per_second"], 2)})
print(json.dumps({"label": __import__("os").environ.get("SWEEP_LABEL","?"), "rows": rows}))
PYEOF