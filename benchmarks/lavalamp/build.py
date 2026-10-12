#!/usr/bin/env python3
"""Builds index.html: every model's lava lamp live in a sandboxed iframe, with its generation stats."""
import html, json
from pathlib import Path

D = Path(__file__).parent
NAMES = {
    "strata-125b": "Qwen3.8-Flash-Next Q2_0 125B",
    "strata-coder": "Flash-Next Coder IQ1_M 125B",
    "qwen35-9b": "Qwen3.5-9B",
    "a3b-35b": "Qwen3.5-35B-A3B IQ2_XXS",
    "qwen35-4b": "Qwen3.5-4B",
    "gemma-e4b": "Gemma-4 E4B",
    "mimo-9b": "MiMo-9B distill",
}
rows = {}
for line in (D / "results.jsonl").read_text().splitlines():
    r = json.loads(line)
    rows[r["label"]] = r  # last run per model wins
notes = json.loads((D / "notes.json").read_text()) if (D / "notes.json").exists() else {}


def decode_tps(r):
    t = r.get("timings") or {}
    if t.get("predicted_per_second"):
        return t["predicted_per_second"]
    if r.get("completion_tokens") and t.get("predicted_ms"):
        return r["completion_tokens"] / (t["predicted_ms"] / 1000)
    if r.get("completion_tokens") and r.get("wall_s"):
        return r["completion_tokens"] / r["wall_s"]
    return None


order = sorted(rows.values(), key=lambda r: (-(notes.get(r["label"], {}).get("score") or 0), r["wall_s"]))
cards = []
for i, r in enumerate(order):
    tps = decode_tps(r)
    n = notes.get(r["label"], {})
    flags = []
    if r.get("finish") == "length":
        flags.append("hit token limit")
    if not r.get("has_closing_html"):
        flags.append("no closing &lt;/html&gt;")
    score = f'<span class="score">{n["score"]}/10</span>' if n.get("score") is not None else ""
    note = f'<p class="note">{html.escape(n["note"])}</p>' if n.get("note") else ""
    cards.append(f"""
<article class="card">
  <header><span class="rank">#{i + 1}</span><h2>{html.escape(NAMES.get(r["label"], r["label"]))}</h2>{score}</header>
  <div class="frame"><iframe src="out/{r["label"]}.html" sandbox="allow-scripts" title="{r["label"]}"></iframe></div>
  <dl>
    <div><dt>Time</dt><dd>{r["wall_s"]:.0f} s</dd></div>
    <div><dt>Tokens</dt><dd>{r.get("completion_tokens") or "?"}</dd></div>
    <div><dt>Speed</dt><dd>{f"{tps:.1f} tok/s" if tps else "?"}</dd></div>
    <div><dt>File</dt><dd>{r["html_bytes"] / 1024:.1f} KB</dd></div>
  </dl>
  <p class="meta">{html.escape(r["engine"])}{" · " + " · ".join(flags) if flags else ""} · <a href="out/{r["label"]}.html" target="_blank">open full screen</a></p>
  {note}
</article>""")

prompt = html.escape((D / "prompt.txt").read_text())
page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lava lamp bench · RTX 2080</title>
<style>
:root {{ color-scheme: dark; --bg:#0b0b0d; --card:#151518; --line:#26262b; --ink:#ececf0; --mute:#8b8b95; --acc:#ff8a3d; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, sans-serif; }}
main {{ max-width:1400px; margin:0 auto; padding:32px 20px 60px; }}
h1 {{ margin:0 0 6px; font-size:26px; }}
.sub {{ color:var(--mute); margin:0 0 18px; }}
details {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; margin-bottom:24px; }}
summary {{ cursor:pointer; color:var(--mute); }}
pre {{ white-space:pre-wrap; margin:10px 0 0; font-size:13px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:18px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
.card header {{ display:flex; align-items:baseline; gap:10px; padding:12px 14px; }}
.card h2 {{ font-size:16px; margin:0; flex:1; }}
.rank {{ color:var(--mute); font-variant-numeric:tabular-nums; }}
.score {{ color:var(--acc); font-weight:600; }}
.frame {{ aspect-ratio:3/4; background:#000; border-block:1px solid var(--line); }}
iframe {{ width:100%; height:100%; border:0; display:block; }}
dl {{ display:grid; grid-template-columns:repeat(4, 1fr); margin:0; padding:10px 14px 0; }}
dt {{ color:var(--mute); font-size:12px; }}
dd {{ margin:0; font-variant-numeric:tabular-nums; font-weight:600; }}
.meta {{ color:var(--mute); font-size:13px; margin:8px 14px 12px; }}
.note {{ font-size:13px; margin:0 14px 14px; }}
a {{ color:var(--acc); }}
</style></head><body><main>
<h1>Lava lamp bench</h1>
<p class="sub">Same prompt, one attempt per model, on an RTX 2080 (8 GB) + i5-9600K + 64 GB DDR4-3200. Thinking off, temperature 0.7.
Time is the full request wall clock including prompt processing. Ranked by the visual score, then by time.</p>
<details><summary>Prompt</summary><pre>{prompt}</pre></details>
<section class="grid">{"".join(cards)}</section>
</main></body></html>
"""
(D / "index.html").write_text(page)
print(f"index.html: {len(order)} models")
