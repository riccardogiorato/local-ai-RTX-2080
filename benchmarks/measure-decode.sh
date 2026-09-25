#!/usr/bin/env bash
# measure-decode.sh <label> — decode/prefill/acceptance for the model on 127.0.0.1:8080
# Both fixed prompt classes, 2 runs each (ranges, no best-of), temperature 0,
# fresh prefill per call (cache_prompt off). Server-reported rates only.
# Acceptance = accepted draft tokens / drafted tokens; mean_len = predicted/verify-count
# (reproduces prior conventions: TC d2 0.995/2.99, A3B d4 0.774/4.09).
set -euo pipefail
LABEL="${1:?label}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
N_PREDICT="${N_PREDICT:-256}"

mval() { curl -s "http://127.0.0.1:$PORT/metrics" | awk -v k="llamacpp:$1" '$1==k {print $2}'; }

measure() { # <prompt-file>
  local f="$1"
  for i in 1 2; do
    local sa1 sd1 sv1 sp1 sa2 sd2 sv2 sp2 acc mlen r
    sa1=$(mval spec_decode_num_accepted_tokens_total); sd1=$(mval spec_decode_num_draft_tokens_total)
    sv1=$(mval spec_decode_num_drafts_total);         sp1=$(mval tokens_predicted_total)
    r=$(python3 - "$f" "$N_PREDICT" "$PORT" <<'PYEOF'
import json, sys, urllib.request
prompt = open(sys.argv[1], encoding="utf-8").read()
payload = json.dumps({"prompt": prompt, "n_predict": int(sys.argv[2]),
                      "temperature": 0, "cache_prompt": False,
                      "stream": False, "samplers": ["temperature"]}).encode()
req = urllib.request.Request(f"http://127.0.0.1:{sys.argv[3]}/completion",
                             data=payload, headers={"Content-Type": "application/json"})
resp = json.load(urllib.request.urlopen(req, timeout=600))
t = resp["timings"]
print(json.dumps({"decode_tps": round(t["predicted_per_second"], 2),
                  "decode_n": t["predicted_n"],
                  "prefill_tps": round(t["prompt_per_second"], 2)}))
PYEOF
)
    sa2=$(mval spec_decode_num_accepted_tokens_total); sd2=$(mval spec_decode_num_draft_tokens_total)
    sv2=$(mval spec_decode_num_drafts_total);         sp2=$(mval tokens_predicted_total)
    read -r acc mlen < <(python3 -c "
sa,sd,sv,sp = ($sa2-$sa1), ($sd2-$sd1), max(($sv2-$sv1),1), ($sp2-$sp1)
print(round(sd and sa/sd or 0, 3), round((sa+sv) and sp/sv or 0, 2))")
    echo "{\"label\":\"$LABEL\",\"prompt\":\"$(basename "$f")\",\"run\":$i,$r,\"acceptance\":$acc,\"mean_len\":$mlen}"
  done
}

measure "$REPO/prompts/code-continuation.txt"
measure "$REPO/prompts/decode-isolation.txt"