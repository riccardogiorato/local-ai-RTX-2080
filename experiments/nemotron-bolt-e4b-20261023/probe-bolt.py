#!/usr/bin/env python3
# Capability probes for Nemotron 3.5 Bolt E4B (llama.cpp :8080, --jinja template).
# Probe set matches the Gemma-4-E4B recipe classes; NOTE: the exact trains-riddle
# text used in past probes was never recorded in-repo, so the reasoning probe here
# is the canonical river-crossing puzzle instead (verifiable: goat first, 7 crossings).
# Evidence rows -> lab JSONL conventions: one row per probe, ranges kept raw.
import json, os, re, sys, urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
BASE = f"http://127.0.0.1:{PORT}"
OUT = os.environ.get("BOLT_PROBE_OUT", "/home/riccardogiorato/Desktop/github/local-ai-rtx2080/experiments/evidence/nemotron-bolt-e4b-llamacpp.jsonl")

def chat(messages, tools=None, thinking=True, max_tokens=1500):
    payload = {"model": "local-model", "messages": messages, "temperature": 0,
               "max_tokens": max_tokens,
               "chat_template_kwargs": {"enable_thinking": thinking}}
    if tools: payload["tools"] = tools
    req = urllib.request.Request(f"{BASE}/v1/chat/completions",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))

row = lambda name, passed, **kw: json.dumps({"probe": name, "pass": bool(passed), **kw})

RIVER_Q = "A farmer must cross a river taking a wolf, a goat and a cabbage. The boat holds the farmer and one item. The wolf cannot be left alone with the goat, the goat cannot be left alone with the cabbage. What is the first item the farmer must take, and how many crossings are needed in total if he must bring all three across and end on the far bank?"
MEDIAN_BUG = '''def median(xs):
    n = len(xs)
    return sorted(xs)[n // 2]'''
MEDIAN_TASK = f"The following Python function is buggy:\n{MEDIAN_BUG}\nFix it so it returns the correct median for any list, including even-length ones. The median of [3,1,2,4,6,5] must be 3.5, of [1,2,3] must be 2. Reply with the fixed function in a python code block, nothing else."
TOOLS = [{"type": "function", "function": {"name": "getCurrentWeather",
    "description": "Get current weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]

rows = []

# 1-3: reasoning (river crossing) — thinking ON 1500, thinking ON 300, thinking OFF
for name, thinking, budget in [("river-on-1500", True, 1500), ("river-on-300", True, 300), ("river-off", False, 1500)]:
    try:
        r = chat([{"role": "user", "content": RIVER_Q}], thinking=thinking, max_tokens=budget)
        txt = r["choices"][0]["message"]["content"] or ""
        usage = r.get("usage", {})
        ok = "goat" in txt.lower() and ("7" in txt)
        rows.append(row(name, ok, thinking=thinking, budget=budget, output=txt[:300],
                        completion_tokens=usage.get("completion_tokens"),
                        prompt_tokens=usage.get("prompt_tokens")))
    except Exception as e:
        rows.append(row(name, False, error=str(e)[:200]))

# 4: coding — exec-verified median fix
try:
    median_budget = int(os.environ.get("BOLT_MEDIAN_BUDGET", "1000"))
    r = chat([{"role": "user", "content": MEDIAN_TASK}], thinking=True, max_tokens=median_budget)
    txt = r["choices"][0]["message"]["content"] or ""
    code = re.search(r"```python\n(.*?)```", txt, re.S)
    ok = False
    # Bolt can emit a bare function even when asked for a fenced block.
    # Verify the code itself rather than failing only on presentation.
    code_text = code.group(1) if code else txt.strip()
    if code_text:
        try:
            env = {}
            exec(code_text, env)
            ok = env["median"]([3,1,2,4,6,5]) == 3.5 and env["median"]([1,2,3]) == 2 and env["median"]([5]) == 5
        except Exception as verify_err:
            ok = False
            txt += f" [EXEC-FAIL: {verify_err}]"
    rows.append(row("median-fix-exec", ok, budget=median_budget, extraction="fenced" if code else "raw", output=txt))
except Exception as e:
    rows.append(row("median-fix-exec", False, error=str(e)[:200]))

# 5: tools — OpenAI call + continuation
try:
    r = chat([{"role": "user", "content": "What's the current weather in Rome? Use the tool."}], tools=TOOLS, thinking=False)
    msg = r["choices"][0]["message"]
    tc = (msg.get("tool_calls") or [None])[0]
    ok_call = bool(tc) and tc["function"]["name"] == "getCurrentWeather" and "rome" in tc["function"]["arguments"].lower()
    ok_cont, cont_txt = False, ""
    if ok_call:
        msgs = [{"role": "user", "content": "What's the current weather in Rome? Use the tool."}, msg,
                {"role": "tool", "tool_call_id": tc["id"], "content": '{"temp_c": 18, "condition": "cloudy"}'}]
        r2 = chat(msgs, tools=TOOLS, thinking=False)
        cont_txt = r2["choices"][0]["message"]["content"] or ""
        ok_cont = "18" in cont_txt
    rows.append(row("tools-call-continued", ok_call and ok_cont, call_ok=ok_call, cont_ok=ok_cont,
                    call=json.dumps(tc.get("function") if tc else None), continuation=cont_txt[:200]))
except Exception as e:
    rows.append(row("tools-call-continued", False, error=str(e)[:200]))

with open(OUT, "a") as f:
    for line in rows: f.write(line + "\n")
print("\n".join(rows))
