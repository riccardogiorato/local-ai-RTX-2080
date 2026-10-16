#!/usr/bin/env python3
# bonsai9b-multislot.py <label> <concurrency> — measure what N concurrent
# requests do to decode on the served model (server must ALREADY be up on
# :8080, started with a matching --parallel >= N). One arm = N clients
# racing /completion on distinct prompts, pool counter before/after for
# spec-acceptance deltas. 2 runs, JSONL rows to stdout.
# Mirrors measure-decode.sh conventions: temp 0, cache_prompt off, no stream,
# server-reported rates. Wall-clock is reported separately (batch overhead
# is visible as wall >> per-request time).
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
label = sys.argv[1]
conc = int(sys.argv[2])
port = 8080
url = f"http://127.0.0.1:{port}"

prompts = [open(f"{REPO}/prompts/code-continuation.txt", encoding="utf-8").read(),
           open(f"{REPO}/prompts/decode-isolation.txt", encoding="utf-8").read()]

def mval(k):
    with urllib.request.urlopen(f"{url}/metrics", timeout=3) as r:
        for line in r.read().decode().splitlines():
            if line.startswith("llamacpp:" + k + " "):
                return float(line.split()[1])
    return 0.0

def one(args):
    i, prompt, barrier = args
    barrier.wait()
    body = json.dumps({"prompt": prompt + f"\n\n(note {i})",
                       "n_predict": 128, "temperature": 0,
                       "cache_prompt": False, "stream": False}).encode()
    req = urllib.request.Request(f"{url}/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    t = r["timings"]
    return {"client": i, "prompt_n": t["prompt_n"],
            "prefill_tps": round(t["prompt_per_second"], 1),
            "decode_tps": round(t["predicted_per_second"], 2),
            "predicted_n": t["predicted_n"]}

for run in (1, 2):
    sa0, sd0 = mval("spec_decode_num_accepted_tokens_total"), mval("spec_decode_num_draft_tokens_total")
    barrier = Barrier(conc)
    jobs = [(i, prompts[i % len(prompts)], barrier) for i in range(conc)]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=conc) as ex:
        rows = list(ex.map(one, jobs))
    wall = round(time.time() - t0, 2)
    sa1, sd1 = mval("spec_decode_num_accepted_tokens_total"), mval("spec_decode_num_draft_tokens_total")
    acc = round((sd1 - sd0) > 0 and (sa1 - sa0) / (sd1 - sd0) or 0, 3)
    decodes = [r["decode_tps"] for r in rows]
    print(json.dumps({"label": label, "concurrency": conc, "run": run,
                      "wall_s": wall, "decode_tps_per_client": decodes,
                      "decode_tps_min": min(decodes), "decode_tps_max": max(decodes),
                      "acceptance": acc}))