# NEXT-IDEAS — not in the current test queue

Models and experiments that have **not been tested yet**. Tested models live in
`recipes/` (with evidence); this file is only the untested backlog. They move into the
README queue the moment they're actually going to be run.

- being tested → see [README queue](README.md#test-queue)
- already tested → see [recipes/](recipes/) and the [AG-Bench leaderboard](benchmarks/README.md)

## Qwen3.8-27B + DFlash2 drafter (unblocked by the 2026-09-25 MiniCPM-DSpark run)

The DFlash2 ~1.1 GB sidecar drafters exist as public GGUFs (incoai Q4_K_M;
andrew-paul Q3_K_M/Q2_K calibrations, claimed acceptance 64–66%). We now know how
to serve `--spec-type draft-dflash -md` on this engine (proven with MiniCPM's DSpark).
Test: dense Qwen3.8-27B and/or ThinkingCap with the DFlash2 drafter vs their
embedded-MTP profiles — the drafter family the earlier lab never de-blocked.
Owner approval needed for the ~0.7–1.1 GB download.

## Swift1.5-27B and Swift Flash Next (UkisAI)

The rest of the Swift family (owner approved only Swift Bonsai 2 so far). Swift1.5-27B
claims −58.5% thinking tokens with better Terminal-Bench 2.1; Flash Next −63.4%.
GSQ-RCO quants announced for both. Test after owner approval + quant landed.

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