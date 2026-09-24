# NEXT-IDEAS — not in the current test queue

## OrcaSAQ-2-27B (orcarouter, 2026-09-24)

Dense Qwen3.8-27B at 3.21 bpw via a proprietary "SAQ2" mixed-precision quant (12.3 GB,
+0.02% perplexity claim, MTP head included, 90 tok/s @ 16 GB, SWE-bench 70.0 /
Terminal-Bench 58.4). Not runnable here as shipped: **safetensors-only for vLLM +
custom kernel; vLLM has no SM75/Turing support**; their envelope is 16 GB. A GGUF
conversion would re-quantize away the mixed-precision design anyway (→ lands in the
class our ThinkingCap Q2_K recipe already measures). Retry trigger: orcarouter
publishes GGUF or the SAQ2 spec, or a llama.cpp port appears.

Models and experiments that are interesting but deliberately **not queued right now**.
They move into the README queue only when they're actually going to be tested:

- being tested → see [README queue](README.md#test-queue)

## Ternary Bonsai-2 27B (PTQ1_0 / PQ2_0 + MTP drafters)

Weights already on NVMe. On hold: community reports on the ternary family question its
generation quality in open-ended user tests, and the PrismML runtime is not a registry contract.
Retest trigger: a mainstream-quality eval showing ternary parity, or a rainy weekend.

## Qwen2.5-Coder 7B Instruct Q4_K_M

In the HF cache backup. Legacy retest candidate (Windows lab: ~72 tok/s, 0/3 short agent tasks)
— engines moved since; the verdict probably hasn't changed, but it would be cheap to re-run.

## MiniCPM5-2B DSpark

In the HF cache backup. Tiny-class sanity check; Windows lab called it "fast but weak" and
DSpark made it slower. Low priority until a small-model slot is free.

## Diffusion Gemma (26B-A4B)

Honest verdict: **cannot run on this GPU by any supported path today.**
26B MoE with 4B active; registry instances are bf16 (58 GB) and fp8 (Hopper/Blackwell) only —
no GGUF exists, vLLM does not support SM75, and a 26B MoE exceeds 8 GB VRAM even at extreme
low-bpw. Revisit if Google ships an E2B/E4B-class diffusion variant or a GGUF appears.

## Earlier 27B-drafter experiments (DFlash2 / Swift / Escha W2 heads)

Windows-era drafters for the Qwen3.8-27B family sit in the archive. Superseded by the
embedded-MTP DT-bpw2.48 profile unless the base-IQ2_XS retest shows drafter paths winning again.