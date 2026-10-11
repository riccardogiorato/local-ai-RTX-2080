#!/usr/bin/env python3
"""Power-limit sweep for a running Strata serve: decode/prefill speed vs measured GPU power.
Usage: strata-power-sweep.py SERVE_LOG OUT_JSONL  (serve must answer on http://100.110.49.114:8080)"""
import glob, json, os, re, subprocess, sys, threading, time, urllib.request
log_path, out_path = sys.argv[1], sys.argv[2]
URL = "http://100.110.49.114:8080/v1/chat/completions"
LIMITS = [225, 190, 165, 145, 125, 145, 165, 190, 225]
LINE = re.compile(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\)")
REPO = "/home/riccardogiorato/Desktop/github/local-ai-rtx2080"
corpus = "\n\n".join(open(f, errors="ignore").read() for f in sorted(glob.glob(REPO + "/**/*.md", recursive=True))
                     if "node_modules" not in f and "agentic-tasks" not in f)[:108000]
SHORT = ["Write a Python function that merges two sorted lists, with a docstring and three tests.",
         "Explain in plain words how a hash map handles collisions, with a small example.",
         "Write a bash script that finds the ten largest files under a directory and prints their sizes."]
samples, stop = [], threading.Event()
def sampler():
    p = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw,clocks.sm,temperature.gpu", "--format=csv,noheader,nounits", "-lms", "200"],
                         stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        if stop.is_set(): p.kill(); break
        try: w, c, t = (float(x) for x in line.split(",")); samples.append((time.time(), w, c, t))
        except ValueError: pass
threading.Thread(target=sampler, daemon=True).start()
def window(t0, t1):
    s = [x for x in samples if t0 <= x[0] <= t1]
    if not s: return None
    return {"watts": round(sum(x[1] for x in s) / len(s), 1), "sm_mhz": round(sum(x[2] for x in s) / len(s)), "temp_c": max(x[3] for x in s), "n": len(s)}
def ask(content, max_tokens):
    b0 = os.path.getsize(log_path); t0 = time.time()
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": content}], "max_tokens": max_tokens, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    urllib.request.urlopen(urllib.request.Request(URL, body, {"Content-Type": "application/json"}), timeout=900).read()
    t1 = time.time(); time.sleep(1.0)
    with open(log_path, "rb") as f: f.seek(b0); m = LINE.findall(f.read().decode(errors="ignore"))
    r = m[-1]
    prompt_s, gen_s = int(r[3]) / 1000, int(r[6]) / 1000
    return {"prompt_tok": int(r[0]), "read_tok": int(r[2]), "prefill_tps": float(r[4]), "gen": int(r[5]), "decode_tps": float(r[7]),
            "power_prefill": window(t0, t0 + prompt_s), "power_decode": window(t1 - gen_s, t1)}
out = open(out_path, "a")
ask("warm up: say ok", 32)
for i, pl in enumerate(LIMITS):
    subprocess.run(["sudo", "-n", "nvidia-smi", "-pl", str(pl)], check=True, capture_output=True)
    time.sleep(3)
    rec = {"step": i, "power_limit_w": pl, "short": [ask(f"[{i}-{j}] {q}", 192) for j, q in enumerate(SHORT)]}
    rec["long"] = ask(f"[sweep step {i} nonce {time.time()}]\n" + corpus + "\n\nIn one sentence, what is this text about?", 192)
    out.write(json.dumps(rec) + "\n"); out.flush()
    sd = sorted(x["decode_tps"] for x in rec["short"])[1]; sw = sorted((x["power_decode"] or {}).get("watts", 0) for x in rec["short"])[1]
    L = rec["long"]
    print(f"PL {pl:3d} W | short decode {sd:5.1f} tok/s @ {sw:5.1f} W | 30K prefill {L['prefill_tps']:5.0f} tok/s @ {(L['power_prefill'] or {}).get('watts')} W | "
          f"decode@30K {L['decode_tps']:5.1f} tok/s @ {(L['power_decode'] or {}).get('watts')} W | sm {(L['power_prefill'] or {}).get('sm_mhz')} MHz", flush=True)
subprocess.run(["sudo", "-n", "nvidia-smi", "-pl", "225"], capture_output=True)
stop.set(); print("SWEEP-DONE, power limit restored to 225 W")
