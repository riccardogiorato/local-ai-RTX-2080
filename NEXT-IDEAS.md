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

## GLM-OCR: real-photo GT regression set

The prior campaign's KFC/CIAO GT sets did not survive the migration; recipes run on
synthetic images. Pending: a new photographed GT set for the receipt/label class
(regression-grade, human-verifiable).

## laya multilingual checkpoint

Recipe tested typed-decisions only; `LAYA_MODELS=multilingual` (the generative 421M
variant) is untested. Low priority: 2.66 GB VRAM for a router whose typed-decision
sibling already trails kev on our probes.

## PQ2_0-MTP tier — blocked on card size, direct unlock if a bigger card lands

PQ2_0 (2.13 bpw, 7.66 GB) + trained head = the artifact the 1080 Ti post measured
86/98/75 tok/s on (11 GB Pascal). On 8 GB it cannot go resident with useful context.
**2026-09-26 measured boundary** (while falsifying the trained-head-onto-PTQ1_0
graft, see the Bonsai-2 recipe): partial offload at ngl 46 / ctx 4096 loads but
decodes at **2.2 tok/s** — worse than every 27B cram on the ledger; ngl 60 OOMs
at load. Also proven there: the trained head accepts 0.717/0.585 on our fork via
their PQ2_0-MTP file (runtime fully compatible). Retry triggers: an 11 GB+ card
lands in this lab (the giveaway 1080 Ti would be exactly that), or a sub-8 GB
PQ2_0 derivative appears.

The "27B in 8.45 GB at 60 tok/s on a 3090" tweet model. Same graveyard as OrcaSAQ, three
doors and all closed on this card: (1) uzu runtime is Apple-silicon-only; (2) the vLLM
`mirai_s` plugin explicitly requires compute capability **8.0+** (README-documented — our
sm_75 Turing is below the floor, and vLLM 0.30 itself has no Turing support); (3) **no GGUF
and no llama.cpp path** — the codec is QTIP/trellis-family (the uzu branch is
`ryan/qtip-s-agent`), so a conversion would have to dequantize it, which destroys the whole
size point. Also 8.45 GB > 8 GB VRAM — even a hypothetical GGUF would be a partial-offload
cram like ThinkingCap. The whole trymirai family (Qwen3.5-4B/9B-M/L included) is tagged
uzu/safetensors/mirai only. Retry triggers: trymirai ships a llama.cpp/GGUF path, a Turing
build of the plugin (unlikely — the trellis kernels use sm_80+ ops by design), or an Ampere+
box dequantizes it once like castkit would for OrcaSAQ. Until one lands: our dense Qwen3.8-27B
rows already record the "slow-smart 27B" experience this model family promises.

## fafastmobel / Cinference (satellitedown, 2026-09-26) — blocked, triggers recorded

"Qwen3.8-27B delta-transplant (Huihui−Qwen onto UkisAI Swift) in NVFP4/FP8, single
23.8 GB NInfer v3 file with embedded MTP + z-lab DFlash2 drafter; Cinference fork
claims rewritten DFlash2 verify kernels +21–37% (8K–131K ctx) and verify-trees +
prompt lookup up to 895 tok/s, 262K ctx + vision." Four closed doors for this lab:
(1) kernels compile for **sm_120a only** (Blackwell; README: only 5090 32 GB
validated, nothing below); (2) NVFP4/FP8 are Ada/Blackwell-native tensor formats —
SM75 has no hardware path; (3) custom NInfer format, **no GGUF/llama.cpp route** —
dequant-to-GGUF would destroy the size point (same argument as trymirai); (4) 23.8 GB
artifact cannot fit 8 GB VRAM under any cram. Design leads (verify trees, prompt
lookup, in-file DFlash2) join the David19p watch-list — no code adoption. Retry
triggers: cinference ships a Turing kernel build, a sub-8 GB artifact class, or an
Ampere+ box dequants once — none likely; our own DFlash2 sidecar trigger (~600 MB
Q2/Q4 drafter for llama.cpp) remains the live one from this announcement.
