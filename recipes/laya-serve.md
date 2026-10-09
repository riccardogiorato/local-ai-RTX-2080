# laya (convaiinnovations) · typed-decisions checkpoint · `pip install laya` — decision router

**Status: 🔬 lab-verified** — laya ships a **Jev-compatible `POST /v1/systemone` server**, the
same wire protocol as kev (see [kev recipe](kev-05b-serve.md)) — the two are directly
swappable behind a client. Non-autoregressive: `output_tokens: 0`, single forward pass.

- Checkpoint: `convaiinnovations/laya` revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`,
  subfolder `typed-decisions` — ModernBERT-large encoder + 2-layer head
  (`model.safetensors` 842,609,220 B · hf blob sha256 `891102d372688fc2…`); auto-downloaded
  at first `laya-serve` start (HF cache)
- Runtime: `laya==0.3.20`, `laya-serve` (uvicorn/FastAPI, port 8000), torch 2.8.0+cu128,
  Python 3.12 — installed into the kev venv to share torch
- Env vars: `LAYA_MODELS=typed-decisions` preloads only that checkpoint (default preloads all
  three: english, multilingual, typed-decisions)

## Measured on this box (2026-09-24), identical payloads to the kev test

| Case | Wall (curl) | VRAM |
|---|---|---|
| 3-question request, cold | 0.431 s | — |
| 3-question request, warm ×4 | **0.027 s** — byte-identical, deterministic | 2.66 GB GPU |

**27 ms warm is the fastest inference measured on this card** (vs kev's 240 ms for the same
request). The cost is VRAM: 2.66 GB (fp32 ModernBERT-large + torch context) vs kev's 146 MiB —
18× more for 9× the speed, and 2.66 GB is a third of the card.

### Routing verdict (same two probes as kev)

| State | kev-0.5b (146 MiB) | laya typed-decisions (2.66 GB) |
|---|---|---|
| shoes: late + wrong size + double charge | **returns 0.95** | shipping 0.47 (confidence 0.04) |
| double charge + refund never arrived | **billing 0.86** | returns 0.44 ≈ billing 0.42 (near-tie) |

The control state is ambiguous by construction ("refund" is in the returns criteria), so
neither pick is authoritative — but kev matched the intended routing on both states with high
confidence while laya was a coin-flip on one and disagreed on the other. On these probes the
146 MiB model is the better router; laya's advantage is raw speed if you need sub-30 ms
answers and have VRAM to spare.

Evidence: [evidence/laya-serve.jsonl](../evidence/laya-serve.jsonl)

## Reproduce

```bash
uv venv --python 3.12 && uv pip install --python .venv/bin/python laya fastapi uvicorn
# uv pip install torch separately if not already present (cu128 wheel)
LAYA_MODELS=typed-decisions .venv/bin/laya-serve   # http://0.0.0.0:8000

curl localhost:8000/v1/systemone -H 'content-type: application/json' -d '{
  "state": "…", "model": "convaiinnovations/laya-typed-decisions",
  "questions": { "department": {"type": "choice", "instructions": "…", "criteria": {…}},
                 "escalate":   {"type": "noul",  "instructions": "…"},
                 "frustration": {"type": "score", "instructions": "…", "criteria": ["Calm","Frustrated","Very angry"]} }}'
curl localhost:8000/health
```

## Multilingual checkpoint (2026-09-26) — the best laya, tested in Italian

`LAYA_MODELS=multilingual` (convaiinnovations/laya subfolder, auto-downloaded at
first serve): **22 ms warm median** (vs 27 for typed-decisions), **1660 MiB
process VRAM** (vs 2.66 GB), byte-identical deterministic warm responses — and
it **beats typed-decisions on the exact probes that sibling flunked**, in
Italian:

| State (Italian text) | laya multilingual | laya typed-decisions (English) | kev |
|---|---|---|---|
| shoes: late + wrong size + double charge | **returns 0.956** (conf 0.82) | 0.47 coinflip (conf 0.04) | returns 0.95 |
| double charge + refund never arrived | **billing 0.733** (conf 0.73) | 0.44 ≈ 0.42 near-tie | billing 0.86 |
| same billing state in English | billing **0.997** | — | — |

**Verdict: multilingual replaces typed-decisions as the recommended laya
checkpoint** — non-English routing works, at lower latency and less VRAM. The
router tier choice stays task-shaped: kev for tiniest footprint, laya
multilingual for sub-30 ms + non-English. Startup gotcha extends to every
subcommand: `laya-serve --version` also triggers the full 3-checkpoint default
preload (~5.2 GB GPU) — never launch without `LAYA_MODELS` set.

## Notes

- `laya-serve --help` blocks indefinitely (no output): startup preloads/download checkpoints
  regardless of `--help`. Launch it directly and watch the log; don't expect `--help`.
- `--model convaiinnovations/laya-typed-decisions` pins the checkpoint explicitly; the
  response's `model` field then reads `laya-rl-agent` (the rl-agent bundle name) — cosmetic.
- The full multilingual checkpoint (421 M params, generative variant) was **not tested** —
  preloading only typed-decisions kept the download small while our two GGUFs were in flight.
  A later run can `LAYA_MODELS=multilingual` for the generative router.
- No registry contract applies (Python runtime) — lab-recorded only.

## Storage

Checkpoint lives in the HF hub cache (~2.3 GB on SSD after the typed-decisions pull). Per the
rotation rule it should move to the HDD archive once tested — but the HF cache layout makes
moving single repos brittle, so it stays until the next cache sweep (recorded here as the
deviation from the rule).
## Update 2026-10-09: laya GGUF on llama.cpp vs d1-3B (same tests, same server)

`ggml-org/Laya-GGUF` (converted 2026-10-04): `Laya-Q8_0.gguf` 449 MB sha256 `c06528c5…`, `Laya-BF16.gguf`
844 MB `edeea949…` (both verified). Served by llama.cpp b11514 (`/v1/systemone`, decision model type `laya`),
the same build and settings as [d1-3B](d1-3b-decision-llamacpp.md).

| | laya Q8_0 | laya BF16 | d1-3B Q4_K_M |
|---|---|---|---|
| VRAM | 1.1 GB | 1.5 GB | 3.5 GB |
| 1 question / 3 questions | **10.0 / 18.9 ms** | | 14.4 / 55 ms |
| MASSIVE intent (2,974 rows, 59 options) | 44.2% (45.3% with readable labels) | 44.4% | **84.7%** |
| MASSIVE ECE | 0.49 (mean confidence 0.94) | 0.49 | **0.016** |
| 30 labeled small-choice decisions | 21/30 | | **28/30** |
| Throughput, 8 clients | 52 rows/s | 27 rows/s | 15 rows/s |

- laya is the fastest decision model here (10 ms, and multi-question requests are cheap), but it is far
  less accurate and badly overconfident: on MASSIVE it piles onto a few labels (`calendar_query` 569 times)
  while claiming 94% average confidence. Its errors do not depend on option position, so this is not
  llama.cpp's option-truncation limit.
- Misses on the small set include an obvious positive review, all three language-ID items and neutral
  messages scored as urgent or negative.
- Verdict unchanged and now measured at scale: use d1-3B (or d1-omni-600M at 1.2 GB) for decisions you act
  on; laya only where 10 ms matters more than being right.
