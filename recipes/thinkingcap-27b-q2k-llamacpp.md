# ThinkingCap-Qwen3.8-27B · Q2_K (holooo) · llama.cpp — the upgraded slow-smart slot

**Status: 🔬 lab-verified** — bottlecapai's thinking-verbosity finetune of the dense
(non-ternary) Qwen3.8-27B, tested from a community quant after the owner selected Q2_K over
IQ4_XS-MIX (12.5 GB, more CPU offload) and the abliterated i1 builds.

- Weights: `holooo/ThinkingCap-Qwen3.8-27B-Q2_K-GGUF` → `thinkingcap-qwen3.8-27b-q2_k.gguf`
  10,864,592,608 B · sha256 `06063b16c34ebf50…` (verified)
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned image
- **The quant kept the embedded MTP head** (blk.64/nextn) — unlike Xiaomi MiMo's dropped head,
  draft-mtp works here

## Residency boundary (busy desktop, 8 GB)

| Config | ngl | ubatch | VRAM | Result |
|---|---|---|---|---|
| no draft | 42 | 256 | 7.58 GB | ✅ 5.6–5.8 tok/s (baseline) |
| MTP d2 | 42 | — | — | ❌ rs-cache 280 MiB cudaMalloc fails at load |
| MTP d2 | 40 | 256 | 7.65 GB | ❌ loads, crashes at first-request graph capture |
| **MTP d2** | **40** | **128** | **7.65 GB** | ✅ **9.57 tok/s** |
| MTP d2 | 38 | 256 | 7.42 GB | ✅ 9.15 tok/s |

## Measured (fixed code-continuation prompt, temperature 0)

| Config | Decode | MTP acceptance | Prefill (fresh, no-draft) |
|---|---|---|---|
| baseline ngl 42, no draft | 5.6–5.8 tok/s | — | 239 tok/s |
| **MTP d2 ngl 40 / ub 128** | **9.57 tok/s** | **0.995** (mean accepted len 2.99) | — |

**This is the fastest 27B-class partial-offload measured on this card — 2× the DT-IQ2_S cram
(4.6–5.3 tok/s).** Attribution: Q2_K's structured dequant is far cheaper on the CPU band
than IQ2_S bit-unpacking; on this box, where 24 of 64 layers live on CPU, that dominates.
MTP acceptance 0.995 on the repetitive prompt (d2 cap ≈ 3.0 mean) doubles it further.

## Capabilities

| Probe | thinking off | thinking on |
|---|---|---|
| Chat reasoning (trains riddle) | ✅ PASS | ✅ PASS — "Less.", 93 tokens total (incl. ~237-char reasoning), 14.9 s wall |
| Coding (exec-verified) | ✅ PASS | — |
| Tools + continuation | ✅ PASS | — |

Notable: it passes the reasoning probe with **thinking off** — which Qwen3.5-4B and
thinking-off Gemma both fail. And in its signature thinking mode it short-tracks easy
problems (93 tokens) instead of padding — the verbosity finetune evidently scales with
difficulty, wasted tokens aren't forced.

Evidence: [evidence/thinkingcap-27b-q2k-llamacpp.jsonl](../evidence/thinkingcap-27b-q2k-llamacpp.jsonl),
[evidence/thinkingcap-27b-q2k-nodraft-capabilities.jsonl](../evidence/thinkingcap-27b-q2k-nodraft-capabilities.jsonl)

## Reproduce (best config)

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/thinkingcap-27b:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/thinkingcap-qwen3.8-27b-q2_k.gguf --alias ThinkingCap-27B-Q2K-MTP \
  --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 \
  --n-gpu-layers 40 --batch-size 256 --ubatch-size 128 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 --cache-ram 0 --jinja --no-warmup --fit off \
  --load-mode none --backend-sampling --prio 1 --poll 100 \
  --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-ngl all --prio-draft 1 --poll-draft 1
```

Thinking control: `chat_template_kwargs {"enable_thinking": false}` (same as Qwen family).
Approx ~24/64 layers on CPU: expect heavy CPU load during decode; `--prio 2` needs extra
container capabilities, `--prio 1` is the working value.

## Notes

- Q2_K vs IQ2_S for CPU-band crams is now an empirical rule on this card: **if >30% of
  layers must live on CPU, prefer Q2_K over IQ2_XS-class bit-packed quants** — this run
  doubled decode for a bigger file.
- The old DT-IQ2_S recipe remains in the repo as the prior baseline; this one supersedes it
  as the slow-smart slot.
- The registry does not apply (partial offload); lab-recorded.

## Storage

Rotated 2026-09-24 to /mnt/archive/local-models/rtx2080-tested-2026-09/thinkingcap-27b/
(SHA 06063b16… verified). Two 27B sets remain deliberately on SSD: the DT-IQ2_S file
(active bench) and the live Qwen3.5 pair.