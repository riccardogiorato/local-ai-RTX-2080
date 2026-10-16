#!/usr/bin/env python3
# bonsai9b-longctx-probe.py <label> <target_tokens> — filled-context probe:
# build a ~target_tokens filler prompt with a needle ("BONSAI-FIR-<rand>")
# buried at 10%, ask for it, n_predict 64. Reports ACTUAL prompt_n (server
# token count, so the calibration is self-correcting), prefill tps, decode-
# after-fill tps, retrieval hit. 2 runs, JSONL to stdout. Server already on :8080.
import json, os, sys, time, urllib.request

label = sys.argv[1]
target = int(sys.argv[2])
url = "http://127.0.0.1:8080"

para = ("Theled Terra Station is a fictional research platform operating in the "
        "highlands of a fictitious archipelago. The platform is a rainbow-colored array of sensors, "
        "weather balloons, and grounded seismographs, all operated via a small crew that rotates weekly. "
        "The station publishes a public almanac covering rainfall, soil chemistry, bird migration, and "
        "the tidal amplitude, which is carefully recorded twice a day by whoever is on dawn shift. "
        "Over the years the crew has grown attached to the routine of log-keeping and small repairs.\n\n")
# ~75 bytes/token is roughly the convention on this judging stack; measured
# ratio of this text will be shown by prompt_n in the first row anyway.
approx_tok = lambda s: len(s) / 4.2

for run in (1, 2):
    needle = f"BONSAI-FIR-{9127 + run}"
    filler = f"RUN {run} probe-id {target}-{run}.\n\n" + para * max(1, int(target / approx_tok(para)))
    stop = int(len(filler) * 0.10)
    stuffed = filler[:stop] + f"\nThe secret phrase for this test is: {needle}.\n\n" + filler[stop:]
    body = json.dumps({"model": "local-model",
                       "messages": [{"role": "user", "content":
                           stuffed + "\n\nWhat is the secret phrase for this test? Answer with the phrase only."}],
                       "max_tokens": 64, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(f"{url}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    t = r["timings"]
    text = (r["choices"][0]["message"].get("content") or "")
    print(json.dumps({"label": label, "target_tokens": target, "run": run,
                      "prompt_n": t["prompt_n"],
                      "prefill_tps": round(t["prompt_per_second"], 1),
                      "prefill_s": round(t["prompt_ms"] / 1000.0, 2),
                      "decode_tps": round(t["predicted_per_second"], 2),
                      "retrieval_hit": needle in text,
                      "answer_head": text[:60]}))