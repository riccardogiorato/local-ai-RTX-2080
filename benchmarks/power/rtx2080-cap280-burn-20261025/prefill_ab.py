#!/usr/bin/env python3
"""Prefill/decode A/B vs GPU power cap on the standing Bolt E4B llama-server.

Each run builds a unique ~32K-token prompt (defeats prompt caching), POSTs it
to /completion with n_predict 192, and records SERVER-REPORTED timings (lab
convention: timings.prompt_per_second / predicted_per_second), sampling board
power, SM clock and temp at 1 Hz around each request.

Cap schedule is mirrored (165, 280, 225 -- 225, 280, 165) to cancel warming
drift. Writes prefill-ab.jsonl rows and prints a table.
"""
import json
import subprocess
import sys
import threading
import time
import urllib.request

URL = "http://127.0.0.1:8080/completion"
PARA = ("The silicone-valley lab records every measurement twice and reports "
        "ranges over runs, never best-of, so that drift and ambient noise stay "
        "visible in every table of evidence. ")
SCHEDULE = [165, 280, 225, 225, 280, 165]  # one (cap, round) pair per entry
COOLDOWN_CAP_SW = 12   # settle seconds after a cap change
COOLDOWN_BETWEEN = 15  # cool seconds between requests

samples = []  # (time.time(), power W, sm MHz, temp C) — continuous, sliced by window


def sampler_loop():
    while True:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.draw,clocks.sm,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10).stdout.strip()
            if out:
                parts = [float(x.strip()) for x in out.split(",")]
                if len(parts) == 3:
                    samples.append((time.time(), parts[0], parts[1], parts[2]))
        except Exception as e:
            print("sampler error: %r" % e, file=sys.stderr, flush=True)
        time.sleep(1)


def set_cap(watts):
    subprocess.run(["sudo", "nvidia-smi", "-pl", str(watts)],
                   check=True, capture_output=True, text=True)


def run_probe(cap, rnd, nonce):
    prompt = "%s %s %s" % (nonce, nonce, PARA * 950)
    body = json.dumps({
        "prompt": prompt,
        "n_predict": 192,
        "temperature": 0.0,
        "cache_prompt": False,
    }).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    resp = json.loads(urllib.request.urlopen(req, timeout=600).read().decode())
    t1 = time.time()
    win = [s for s in samples if t0 <= s[0] <= t1]
    tim = resp.get("timings", {})
    row = {
        "cap": cap, "round": rnd, "nonce": nonce,
        "prompt_n": tim.get("prompt_n"), "prompt_s": tim.get("prompt_ms", 0) / 1000.0,
        "prompt_tok_s": tim.get("prompt_per_second") or (
            tim.get("prompt_n", 0) / (tim.get("prompt_ms", 1) / 1000.0) if tim else None),
        "predicted_n": tim.get("predicted_n"), "predicted_s": tim.get("predicted_ms", 0) / 1000.0,
        "predict_tok_s": tim.get("predicted_per_second"),
        "wall_s": round(t1 - t0, 2),
        "power_mean": None, "power_min": None, "power_max": None,
        "sm_mhz_min": None, "sm_mhz_max": None, "temp_max": None,
    }
    if win:
        pw = [s[1] for s in win]
        cl = [s[2] for s in win]
        tp = [s[3] for s in win]
        row.update(power_mean=round(sum(pw) / len(pw), 1),
                   power_min=round(min(pw), 1), power_max=round(max(pw), 1),
                   sm_mhz_min=int(min(cl)), sm_mhz_max=int(max(cl)),
                   temp_max=max(tp))
    return row


def main():
    th = threading.Thread(target=sampler_loop, daemon=True)
    th.start()
    rows = []
    seen = {}
    for i, cap in enumerate(SCHEDULE):
        rnd = seen.get(cap, 0)
        seen[cap] = rnd + 1
        set_cap(cap)
        time.sleep(COOLDOWN_CAP_SW)
        # Content-neutral unique nonce: defeats prompt caching without tying
        # decode-acceptance (content-sensitive, temperature 0) to the cap arm.
        nonce = "evidence-marker%03d" % i
        rows.append(run_probe(cap, rnd, nonce))
        print(json.dumps(rows[-1]), flush=True)
        with open("prefill-ab.jsonl", "a") as f:
            f.write(json.dumps(rows[-1]) + "\n")
        set_cap(280)  # park at 280 during cooldown so idle recovery is uniform
        time.sleep(COOLDOWN_BETWEEN)
    print("\ncap | rnd |  prompt_n | prefill tok/s | decode tok/s | power W avg(min-max) | SM MHz | tmax")
    for r in rows:
        print("%4d | %3d | %8d | %13.1f | %12.1f | %18s | %5d | %3.0f" % (
            r["cap"], r["round"], r["prompt_n"] or 0, r["prompt_tok_s"] or 0,
            r["predict_tok_s"] or 0,
            "%.1f(%g-%g)" % (r["power_mean"], r["power_min"], r["power_max"])
            if r["power_mean"] is not None else "-",
            r["sm_mhz_max"] or 0, r["temp_max"] or 0))


if __name__ == "__main__":
    main()
