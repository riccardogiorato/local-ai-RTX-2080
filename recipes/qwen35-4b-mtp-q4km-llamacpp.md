# Qwen3.5-4B MTP · Q4_K_M · llama.cpp

**Status: ✅ registry-validated** (`recommended` for `rtx-2080-8gb`) — promoted via `accept_recipe.py` 2026-09-23, see [registry/qwen35-4b.md](../registry/qwen35-4b.md)

The fast default: best throughput/capability balance for short, bounded work. Weak on multi-fact reasoning without thinking mode (see Capabilities).

## Identity (registry-compatible)

| Field | Value |
|---|---|
| HF repository | `unsloth/Qwen3.5-4B-MTP-GGUF` |
| Revision (full) | `86835bf9949e4d14d6860f7910b1340ad4f271a9` |
| Artifact | `Qwen3.5-4B-Q4_K_M.gguf` |
| Artifact SHA-256 | `3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630` (verified locally) |
| Size | 2.835 GB |
| Engine | llama.cpp 0.4.1-dev `b11118 / e6ab7c1a4` |
| Image | `ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3` |

## Reproduce

One-time model fetch (pinned revision, verified):

```bash
hf download unsloth/Qwen3.5-4B-MTP-GGUF Qwen3.5-4B-Q4_K_M.gguf \
   --revision 86835bf9949e4d14d6860f7910b1340ad4f271a9 --local-dir ~/models/qwen35-4b-mtp
# verify (sha256 must be 3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630)
sha256sum ~/models/qwen35-4b-mtp/Qwen3.5-4B-Q4_K_M.gguf
```

**Config 1 — 32K context, q8_0 KV** (registry-validated contract):

```bash
sudo docker run --gpus all -p 8080:8080 \
  -v ~/models/qwen35-4b-mtp:/models:ro \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Qwen3.5-4B-Q4_K_M.gguf --alias Qwen3.5-4B-MTP-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 32768 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4
```

**Config 2 — 128K context, q8_0 KV** (max resident context; identical short-fill decode):

```bash
sudo docker run --gpus all -p 8080:8080 \
  -v ~/models/qwen35-4b-mtp:/models:ro \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Qwen3.5-4B-Q4_K_M.gguf --alias Qwen3.5-4B-MTP-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 131072 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4
```

Endpoint: `http://127.0.0.1:8080/v1`, model id `Qwen3.5-4B-MTP-Q4_K_M`.

## Measured configurations (2026-09-23, all fully GPU-resident)

| CTX | KV type | VRAM used | free | decode short-fill | decode filled | prefill filled |
|---|---|---|---|---|---|---|
| 32K | q8_0 | 4.34 GB | 2.8 GB | 181.8–182.2 tok/s | — | 2,327 t/s @2.8K · 2,241 @11.7K |
| 128K | q8_0 | 7.15 GB | 640 MiB | 181.7–181.9 tok/s | 76.7 tok/s @94K | 1,295 t/s @94K |

- Short-fill decode on the fixed 1,987-token [code-continuation prompt](../prompts/code-continuation.txt); MTP draft acceptance 203/208 (97.6%).
- **128K costs nothing at short fill** on this card (181.7 vs 181.8 tok/s): context size only matters once filled.
- Cold start: 51.6 s docker run → model loaded; first request 17 tok/s incl. graph compile (CUDA graphs reused afterwards).
- Acceptance-harness decode (fixed "history of computing" ×32 prompt, thinking on): **112.8 tok/s**, TTFT 71 ms (3 samples). First acceptance with llama.cpp defaults: 113.7 tok/s, TTFT 100 ms — flags change TTFT, not decode (see 9B recipe note).
- Docker vs bare GPU: no measurable decode penalty; all numbers in this repo are from the digest-pinned docker image.

## Build-era comparison (same flags, same fixed prompt)

| build | short-fill decode |
|---|---|
| `b10481 / 9dbc6621a` | 173.3–173.6 tok/s |
| `b11118 / e6ab7c1a4` | 181.7–182.2 tok/s (+5%) |

## Capabilities (2026-09-23, thinking off)

| Probe | Result |
|---|---|
| Multi-fact reasoning (train-transit comparison) | ❌ **fail** — answered "more" (expected "less": 90 vs 91 min). Thinking-off hurts this model class. |
| Coding: fix buggy function, output executed against cases | ✅ pass |
| OpenAI tools: `get_weather("Turin")` + round-tripped tool result | ✅ pass |

Evidence: [../evidence/](../evidence/).

## Notes

- When reasoning quality matters, use the [9B recipe](qwen35-9b-mtp-q4km-llamacpp.md) as the model and keep this one as the fast default — that is exactly how they sit in local-ai-registry (4B recommended, 9B alternate).
- The mmproj vision tensors in the repo are not loaded (`--model` mode); vision is untested for this recipe.