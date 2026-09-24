# NEXT-IDEAS — not in the current test queue

## OrcaSAQ-2-27B (orcarouter, 2026-09-24)

Dense Qwen3.8-27B at 3.21 bpw — same base as our ThinkingCap cram. **Investigated
2026-09-24 (evening):** the "SAQ2" branding is quant_method `exl3` v1.5.1 (QTIP-class:
procedural codebook + tail-biting trellis + Hadamard rotations; spec "not disclosed",
source is the doc). Not runnable on this card, with evidence: **exllamav3's CUDA
extension requires sm_80+** (ptxas rejects the mma instructions for our sm_75 —
confirmed in build logs), its dequant-to-fp16 paths are CUDA kernels, and **no public
exl3→GGUF converter exists** — conversion would be a from-source QTIP decoder
reimplementation. vLLM path equally dead (no SM75). The same base model IS tested here
via Qwen3.8-27B-DT-IQ2_S and ThinkingCap Q2_K. Retry triggers (any one): orcarouter
publishes GGUF; a community exl3→GGUF converter appears; an Ampere+ machine becomes
available to dequant once to fp16 (then standard conversion applies).

**Update (2026-09-25):** two near-miss tools found. [castkit](https://pypi.org/project/castkit/)
is exactly the right converter — "cross-format conversion via automatic FP16 decast",
GGUF and EXL3 backends in one CLI — but its EXL3 backend wraps the same exllamav3
extension (CUDA sm_80+), so on this card it cannot run; on any Ampere+ box the path is
a single `castkit convert <model> -f gguf` command. [trellis-webgpu](https://github.com/Azimml/trellis-webgpu)
reimplements the QTIP/TCQ decoder from scratch outside CUDA (in WGSL) — proof that a
CPU/non-CUDA EXL3 decoder is possible once someone ports the packing differences.

Models and experiments that are interesting but deliberately **not queued right now**.
They move into the README queue only when they're actually going to be tested:

- being tested → see [README queue](README.md#test-queue)

## Ternary Bonsai-2 27B — ✅ TESTED 2026-09-25, verdict overturned

Unparked by owner directive and measured (see
[recipe](recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md)): 3/3 capability probes
thinking-off, AG-Bench 4/6 with the same two family failures as its dense Qwen3.8-27B
siblings, at 59.3/49.9 tok/s fully resident (5–6× every other 27B here). The "community
says ternary is too dumb" hold is empirically refuted on this bench. Residual costs:
fork-only runtime (PTQ1_0 = enum 143; upstream refuses the file) and 8K ctx with MTP.

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