# Gemma 4 E4B QAT · UD-Q4_K_XL + assistant-MTP drafter · llama.cpp

**Status: 🔬 lab-verified** — the fast-resident chat model slot. Gemma 4 E4B is a
thinking model (reasoning-first output) with an effective-params layout (KV layers 0–3
share with 40/41 — the full 4.22 GB tensor file runs ~2.9 GB resident), leaving the card
mostly free.

- Main: `unsloth/gemma-4-E4B-it-qat-GGUF` → `gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf`
  4,215,695,776 B · sha256 `df0fd4ee07072c60…` (verified)
- Drafter: `gemma-4-E4B-it-qat-assistant-MTP-Q8_0.gguf` 98,671,040 B (external MTP head,
  separate file — unlike Qwen3.5's embedded MTP, this one needs `--spec-draft-model`)
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned as everywhere here

## Measured on this box (2026-09-24, fixed code-continuation prompt, temperature 0)

| Config | Decode | Prefill (fresh) | VRAM (total GPU) |
|---|---|---|---|
| No draft, 8K ctx | 88.85 tok/s | — | ~3.5 GB |
| **MTP d2 draft, 8K ctx** | **181.1–181.7 tok/s** | **2,762 tok/s** | 3.64 GB |
| MTP d2, 32K ctx | (same decode class) | — | 4.65 GB |

**MTP d2 doubles decode (2.04×)** with draft acceptance 0.64–0.88 and mean accepted
length 2.28–2.74 — healthy for a d2 cap. Prior Windows lab recorded ~145 tok/s MTP d2 on
this same card: the b11118 build + this drafter beat it by ~25%.

The first request after load pays ~20–26 s of CUDA-graph compile (its "prompt eval" reads
86 tok/s — noise); real fresh-prompt prefill is 2,081 tokens in 753 ms.

## Capabilities (capability harness, thinking default ON)

| Probe | Result |
|---|---|
| Chat reasoning (trains riddle), thinking ON, 1500-token budget | ✅ PASS — "Less." (318 tokens incl. ~240 reasoning, 1.9 s wall at 180.5 tok/s) |
| Same probe, 300-token budget | ❌ budget fail — reasoning alone consumes 300 tokens, content empty |
| Same probe, thinking OFF (`enable_thinking: false`) | ❌ answer fail — says "same" |
| Coding (exec-verified fix) | ✅ PASS |
| OpenAI tools + continuation | ✅ PASS |

**This model needs its thinking mode on** for reasoning, and thinking makes it the
fastest-resident reasoner on the card: the trains riddle that Qwen3.5-4B fails at
non-thinking speed costs Gemma 1.9 s total. `enable_thinking: false` works via
`chat_template_kwargs` with `--jinja` (same kwarg as Qwen) — use it only for trivial
churn, not reasoning.

Evidence: [evidence/gemma4-e4b-qat-llamacpp.jsonl](../evidence/gemma4-e4b-qat-llamacpp.jsonl)

## Reproduce (MTP d2)

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/gemma-4-e4b-qat:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf --alias Gemma4-E4B-QAT-MTP \
  --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --jinja --no-warmup \
  --spec-type draft-mtp --spec-draft-model /models/gemma-4-E4B-it-qat-assistant-MTP-Q8_0.gguf \
  --spec-draft-n-max 2
```

`--ctx-size 65536` fits at 4.65 GB and `--ctx-size 131072` at 5.81 GB — **128K fully resident with the drafter is the largest context measured on this card** (~2.3 GB still free).

## Notes

- External drafter flags: `--spec-draft-model` (`-md`) + `--spec-type draft-mtp`; the
  embedded-MTP style used for Qwen3.5 does not apply — Gemma's MTP head ships as a
  separate GGUF.
- Thinking control: `chat_template_kwargs: {"enable_thinking": false}` (needs `--jinja`).
  With thinking off, decode throughput is unchanged but reasoning quality drops (fails
  the trains probe it passes with thinking on).
- QAT quality: this is Google's QAT build — the Q4_K_XL quantization is the intended
  serving quality (QAT-trained for 4-bit); no quality regression measurements beyond the
  capability probes were run.

## Storage

Rotated 2026-09-24 to /mnt/archive/local-models/rtx2080-tested-2026-09/gemma-4-e4b-qat/
(SHA-verified per file; SSD workbench copy deleted after the recipe was committed).