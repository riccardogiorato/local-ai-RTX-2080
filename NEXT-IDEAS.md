# NEXT-IDEAS — not in the current test queue

Models and experiments that have **not been tested yet**. Tested models live in
`recipes/` (with evidence); this file is only the untested backlog. They move into the
README queue the moment they're actually going to be run.

- being tested → see [README queue](README.md#test-queue)
- already tested → see [recipes/](recipes/) and the [AG-Bench leaderboard](benchmarks/README.md)


## Swift Flash Next (UkisAI) — blocked, cannot run on this card

~250 GB-class model; the smallest public quant (IQ1_S, 65 GB split) exceeds any
mmap/RAM path on this machine (16 GB RAM). Same verdict family as Diffusion Gemma.
Retry trigger: an ultra-low-bpw sub-8 GB build appears or a much larger machine.

## OrcaSAQ-2-27B (orcarouter) — blocked, triggers recorded

SAQ2 = exl3 v1.5.1 (QTIP-class). Cannot run here as shipped: exllamav3 requires
sm_80+ (ptxas-confirmed), no CPU dequant path, no public exl3→GGUF converter
(castkit does FP16-decast conversion but its exl3 backend needs Ampere+;
trellis-webgpu proves non-CUDA TCQ decoders are coming). Retry triggers (any one):
orcarouter publishes GGUF; a community converter appears; an Ampere+ machine
dequants once to fp16. The same base IS tested here via Qwen3.8-27B-DT-IQ2_S /
ThinkingCap Q2_K / Bonsai-2.

## Diffusion Gemma (26B-A4B) — blocked, verdict: cannot run today

No GGUF, vLLM has no SM75, 26B MoE exceeds 8 GB even at extreme low-bpw. Retry if
Google ships an E2B/E4B-class diffusion variant or a GGUF appears.

## ThinkingCap / dense-27B: 32K KV-in-RAM profile through the AG-Bench

The KV-in-RAM profile (32K, ngl 41, owner experiment) is decode-measured but never
agent-benched: do long-context tasks flip any of the family's two standing failures
(React contract, TS migration)? Cheap: one serve + one bench run.

## Hard-reasoning probe for ThinkingCap's verbosity claim

The finetune short-tracks easy problems (trains riddle in 93 tokens); its
thinking-verbosity design should only engage at difficulty. Pending: a hard
reasoning probe (multi-step math/logic) to see whether verbosity scales with
difficulty as claimed — micro-probe tier, no download.

## GLM-OCR: real-photo GT regression set

The prior campaign's KFC/CIAO GT sets did not survive the migration; recipes run on
synthetic images. Pending: a new photographed GT set for the receipt/label class
(regression-grade, human-verifiable).

## llama-bench micro-tier (internet-comparable numbers)

Optional: add llama-bench pp/tg rows alongside the server-class measurements so our
numbers are directly comparable with public tables. CPU-only effort, zero risk.

## laya multilingual checkpoint

Recipe tested typed-decisions only; `LAYA_MODELS=multilingual` (the generative 421M
variant) is untested. Low priority: 2.66 GB VRAM for a router whose typed-decision
sibling already trails kev on our probes.