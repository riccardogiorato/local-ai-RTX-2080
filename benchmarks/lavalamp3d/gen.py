#!/usr/bin/env python3
"""One generation of prompt.txt against the server on :8080. Usage: gen.py LABEL ENGINE"""
import json, re, sys, time, urllib.request
from pathlib import Path
label, engine = sys.argv[1:3]
D = Path(__file__).parent
prompt = (D / "prompt.txt").read_text()
body = {"model": "local-model", "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16384, "temperature": 0.7, "top_p": 0.8,
        "chat_template_kwargs": {"enable_thinking": False}}
req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode(),
                             {"Content-Type": "application/json"})
t0 = time.time()
resp = json.loads(urllib.request.urlopen(req, timeout=3600).read())
wall = time.time() - t0
msg = resp["choices"][0]["message"]
text = msg.get("content") or ""
timings = resp.get("timings")
if not timings:
    try: timings = json.loads(urllib.request.urlopen("http://127.0.0.1:8080/v1/status", timeout=10).read()).get("last_timings")
    except Exception: timings = None
(D / "out" / f"{label}.raw.txt").write_text(text)
m = re.search(r"```(?:html)?\s*\n(.*?)```", text, re.S)
html = m.group(1) if m else text[text.find("<"):] if "<" in text else text
(D / "out" / f"{label}.html").write_text(html)
usage = resp.get("usage") or {}
row = {"label": label, "engine": engine, "wall_s": round(wall, 1),
       "completion_tokens": usage.get("completion_tokens"), "prompt_tokens": usage.get("prompt_tokens"),
       "finish": resp["choices"][0].get("finish_reason"), "fenced": bool(m), "html_bytes": len(html),
       "has_closing_html": "</html>" in html.lower(), "timings": timings}
with open(D / "results.jsonl", "a") as f: f.write(json.dumps(row) + "\n")
print(json.dumps({k: v for k, v in row.items() if k != "timings"}))
