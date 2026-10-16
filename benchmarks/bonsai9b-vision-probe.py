#!/usr/bin/env python3
# bonsai9b-vision-probe.py <label> <image-path> — GT-scored image probe via
# /v1/chat/completions (base64 data-url). Reports image prefill tps from
# server timings, decode tps, and a GT field-match score for the receipt
# target (the GLM-ocr session's POZZETTO GT: 5 line items + TOTALE 22.50).
import base64, json, sys, time, urllib.request

label = sys.argv[1]
img_path = sys.argv[2]
question = sys.argv[3] if len(sys.argv) > 3 else (
    "Extract this receipt verbatim: every line item with quantity, description "
    "and price, then the total. Output plain text only.")
GT = ["2 GELATO PISTACCHIO 10.00", "1 GELATO NOCCIOLA 5.00", "2 ACQUA MINERALE 4.00",
      "1 CAFFE ESPRESSO 2.00", "1 CORNETTO 1.50", "TOTALE 22.50"]

b64 = base64.b64encode(open(img_path, "rb").read()).decode()
body = json.dumps({"model": "local-model",
                   "messages": [{"role": "user", "content": [
                       {"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                       {"type": "text", "text": question}]}],
                   "max_tokens": 400, "temperature": 0,
                   "chat_template_kwargs": {"enable_thinking": False}}).encode()
req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
t0 = time.time()
r = json.load(urllib.request.urlopen(req, timeout=600))
wall = round(time.time() - t0, 2)
t = r.get("timings", {})
text = (r["choices"][0]["message"].get("content") or "")
norm = " ".join(text.upper().split())
hit = sum(1 for g in GT if " ".join(g.split()) in norm)
print(json.dumps({"label": label, "image": img_path, "wall_s": wall,
                  "prompt_n": t.get("prompt_n"), "prefill_tps": round(t.get("prompt_per_second", 0), 1),
                  "decode_tps": round(t.get("predicted_per_second", 0), 2),
                  "gt_fields_hit": f"{hit}/{len(GT)}", "answer": text[:400]}))