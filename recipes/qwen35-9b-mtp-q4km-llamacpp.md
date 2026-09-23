# Qwen3.5-9B MTP · Q4_K_M · llama.cpp

**Status: ✅ registry-validated** (alternate for `rtx-2080-8gb`) — promoted via `accept_recipe.py` 2026-09-23, see [registry/qwen35-9b.md](../registry/qwen35-9b.md)

## Identity (registry-compatible)

| Field | Value |
|---|---|
| HF repository | `unsloth/Qwen3.5-9B-MTP-GGUF` |
| Revision (full) | `9716a636ee4bddc3fed678220b7a33dd2a4160ae` |
| Artifact | `Qwen3.5-9B-Q4_K_M.gguf` |
| Artifact SHA-256 | `e8dd94817e95d6c0939102049d068418269978377b13616c4726235e232841fe` (verified locally) |
| Size | 5.869 GB |
| Engine | llama.cpp 0.4.1-dev `b11118 / e6ab7c1a4` |
| Image | `ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3` |

## Reproduce

Prerequisites: Docker + NVIDIA container toolkit. One-time model fetch (pinned revision, verified):

```bash
hf download unsloth/Qwen3.5-9B-MTP-GGUF Qwen3.5-9B-Q4_K_M.gguf \
   --revision 9716a636ee4bddc3fed678220b7a33dd2a4160ae --local-dir ~/models/qwen35-9b-mtp
# verify (sha256 must be e8dd94817e95d6c0939102049d068418269978377b13616c4726235e232841fe)
sha256sum ~/models/qwen35-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf
```

**Config 1 — 32K context, q8_0 KV** (registry-validated contract):

```bash
sudo docker run --gpus all -p 8080:8080 \
  -v ~/models/qwen35-9b-mtp:/models:ro \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Qwen3.5-9B-Q4_K_M.gguf --alias Qwen3.5-9B-MTP-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 32768 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4
```

**Config 2 — 64K context, q4_0 KV** (max resident context; identical short-fill decode):

```bash
sudo docker run --gpus all -p 8080:8080 \
  -v ~/models/qwen35-9b-mtp:/models:ro \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Qwen3.5-9B-Q4_K_M.gguf --alias Qwen3.5-9B-MTP-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 65536 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --batch-size 512 --ubatch-size 512 \
  --cache-type-k q4_0 --cache-type-v q4_0 --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4
```

Endpoint: `http://127.0.0.1:8080/v1`, model id `Qwen3.5-9B-MTP-Q4_K_M`.

## Measured configurations (2026-09-23, all fully GPU-resident)

| CTX | KV type | VRAM used | free | decode short-fill | decode filled | prefill filled |
|---|---|---|---|---|---|---|
| 32K | q8_0 | 6.93 GB | 856 MiB | **124.5–124.8 tok/s** | — | 1,578 t/s @2.6K · 1,529 @11.7K |
| 64K | q4_0 | 7.27 GB | 524 MiB | **124.2–124.4 tok/s** | 78.8 tok/s @37K | 1,365 t/s @37K |
| 64K | q8_0 | ⚠️ **OOM** | — | — | — | — |

- Short-fill decode is measured on the fixed 1,987-token [code-continuation prompt](../prompts/code-continuation.txt) with `-b 512 -ub 512`; MTP draft acceptance 204/204 (100%) on that prompt.
- **Decode speed is prompt-dominated, not flag-dominated**: on the acceptance prompt, `-b 512 -ub 512` vs llama.cpp defaults gave 112.8 vs 113.7 tok/s (same within noise); the flags trimmed TTFT from 100 → 71 ms. They are kept to match the prior-lab convention, not for decode. The large reported deltas between "fast" and "slow" runs on this card come from MTP acceptance: 100% on repetitive continuation text (~124 tok/s), ~50–75% on novel prose (~76–100 tok/s).
- Cold start: **56.8 s** docker run → model loaded; first request decodes 17 tok/s incl. graph compile; warm steady-state after.
- Acceptance-harness decode (fixed "history of computing" ×32 prompt, thinking on): **76.4 tok/s**, TTFT 102 ms (3 samples).

## Build-era comparison (same flags, same fixed prompt)

| build | short-fill decode |
|---|---|
| `b10481 / 9dbc6621a` (era-matched to prior Windows lab) | 115.3–117.1 tok/s |
| `b11118 / e6ab7c1a4` (current) | 124.5–124.8 tok/s |

## Capabilities (2026-09-23, thinking off)

| Probe | Result |
|---|---|
| Multi-fact reasoning (train-transit comparison) | ✅ pass |
| Coding: fix buggy function, output executed against cases | ✅ pass |
| OpenAI tools: `get_weather("Turin")` + round-tripped tool result | ✅ pass |
| Agent-harness tool use (opencode build agent via T3 → local server) | ✅ pass — bash tools executed (`free -h`, `lscpu …`) |

Evidence: [../evidence/](../evidence/), raw JSONL per run.

## Notes

- Thinking mode is ON by default in this chat template; pass `chat_template_kwargs {"enable_thinking": false}` for deterministic coding/agent use.
- The embedded nextn MTP head needs no separate drafter; `--spec-type draft-mtp --spec-draft-n-max 4` engages it (log line: `creating MTP draft context against the target model`).