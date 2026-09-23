# 2026-09-23 — Qwen3.5 4B/9B MTP, two llama.cpp builds, context ceilings

Machine: [hardware.md](../hardware.md). Engine: llama.cpp server images digest-pinned (`server-cuda12-b10481 @b2497f88…`, `server-cuda12-b11118 @bfb3264f…`). Decode/prefill are server-reported (`timings.predicted_per_second`), short-fill = fixed 1,987-token [code-continuation prompt](../prompts/code-continuation.txt); "n/a" cells were measured on other prompts and marked as such.

## Decode (tok/s, ranges over 2–3 runs)

| model | build | ctx | KV | short-fill | filled | notes |
|---|---|---|---|---|---|---|
| 4B | b11118 | 32K | q8_0 | 181.8–182.2 | — | acceptance MTP 203/208 |
| 4B | b11118 | 128K | q8_0 | 181.7–181.9 | 76.7 @94K | 7.15 GB resident |
| 4B | b10481 | 32K | q8_0 | 173.3–173.6 | — | era-matched build |
| 4B | b11118 | 32K* | q8_0* | 150–153† / 112.8–113.7†† | — | †novel coding prompt, MTP ~0.75 · ††acceptance prompt, default batch==512 batch A/B |
| 9B | b11118 | 32K | q8_0 | 124.5–124.8 | — | acceptance MTP 204/204 |
| 9B | b11118 | 64K | q4_0 | 124.2–124.4 | 78.8 @37K | 7.27 GB resident |
| 9B | b10481 | 32K | q8_0 | 115.3–117.1 | — | |
| 9B | b11118 | 64K | q8_0 | ⚠️ OOM at load | — | — |

*\* same flags except where marked.*
Key attribution: **decode is prompt-dominated** — identical flags shift ~0.8% between batch settings (113.7 default vs 112.8 with `-b 512 -ub 512`, acceptance prompt, 4B), while switching prompt class (repetitive continuation → novel prose) shifts 40–50% because MTP acceptance drops 1.00 → 0.5–0.75. Compare speeds across machines only on the same prompt file.

## Prefill (tok/s, fresh prompts)

| model | ctx | KV | @2.6K tok | @11.7K tok | large fill |
|---|---|---|---|---|---|
| 4B | 32K | q8_0 | 2,327 | 2,241 | 2,309 @2.0K (continuation prompt) · 1,295 @94K |
| 9B | 32K | q8_0 | 1,578 | 1,529 | 1,559 @2.0K · 1,365 @37K |

## Residency (VRAM, desktop baseline ~520 MiB excluded)

| model | ctx | KV | used | free |
|---|---|---|---|---|
| 4B | 32K | q8_0 | 4.34 GB | 2.8 GB |
| 4B | 128K | q8_0 | 7.15 GB | 640 MiB |
| 9B | 32K | q8_0 | 6.93 GB | 856 MiB |
| 9B | 64K | q4_0 | 7.27 GB | 524 MiB |

Cold start (docker run → "model loaded"): 4B 51.6 s · 9B 56.8 s; first decode request pays graph compilation (17 tok/s in logs) then steady state.

## Acceptance runs (registry harness — fixed 256-token "history of computing" prompt, thinking on, 3 samples, median)

| recipe | decode | TTFT | evidence |
|---|---|---|---|
| qwen35-4b-q4km-mtp-rtx-2080-8gb-llamacpp-tp1 | 112.8 tok/s | 71 ms | `qwen35-4b-acceptance-raw-v2.jsonl` |
| qwen35-9b-q4km-mtp-rtx-2080-8gb-llamacpp-tp1 | 76.4 tok/s | 102 ms | `qwen35-9b-acceptance-raw.jsonl` |

## Windows-parity 1:1 (same card was the Windows lab until 2026-09-21)

Same flags, same 1,987-token continuation prompt, era-matched build (b10481 ≈ the lab's pinned lineage):

| run | engine | decode |
|---|---|---|
| Windows lab (baseline, 32K upstream) | lab-pinned build | 172.26 tok/s |
| **Linux (this run)** | b10481 | **173.3–173.6 tok/s — tie at ±0.1%** |
| Linux (this run) | b11118 | 181.8–182.2 (+5%) |

Conclusion: no OS penalty on identical settings; current llama.cpp is the faster runtime. Docker adds no measurable decode cost on this card (server-reported rates, GPU passed through natively).