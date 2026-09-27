# NEXT-IDEAS — not in the current test queue

Models and experiments that have **not been tested yet**. Tested models live in
`recipes/` (with evidence); this file is only the untested backlog. They move into the
README queue the moment they're actually going to be run.

- being tested → see [README queue](README.md#test-queue)
- already tested → see [recipes/](recipes/) and the [AG-Bench leaderboard](benchmarks/README.md)


## Swift Flash Next / Qwen3.8-Flash-Next — RESOLVED 2026-09-27 (partial): UltraLite 37GiB SERVED (12.5 tok/s, first 125B here)

The original 65 GB IQ1_S verdict stands superseded for the low end: the 0xKitkat
UltraLite 37GiB (1.80 bpw) was downloaded, SHA-verified, served on the patched
qwen4exp runtime — first 125B-class on the card. Boundary learned: sub-2 bpw
BREAKS THE REASONING CHAIN (EOS-at-reasoning-close; same wall as IQ1_S), so the
frontier scores stay unreachable at this compression. Remaining blockers for a
USABLE Flash-Next slot: a sub-40GB artifact at >=2.2bpw with MTP + intact
reasoning (none exists today); Strata's Q2_0 tier is now sm_75-portable per
the source survey below (soft gate — one tf32 mma + bf16 emulation) — its
remaining blocker is the port work itself plus RAM/bandwidth economics, not
the instruction floor.
See recipes/flashnext-ultralite-125b-llamacpp-fork.md and evidence/flashnext-ultralite-125b.jsonl.
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

## UBBoost cherry-pick build — RESOLVED 2026-09-26 via c9df0ee (claim reproduced 2.4× with plain ubatch on all 3 CPU-offload models; port not needed — kept for the dense-cram cold-prefill profile reference)

DavidAngeloBen's llama.cpp PR #23239 / discussion #23262: RTX 2080 8GB + Qwen
35B-A3B + MTP, the same VRAM-constrained CPU-experts recipe as our A3B/Xing
serves. A second prompt-processing runtime (--promptprocessing-ubatchboost-size
+ -n-cpu-moe + -gpu-layers) runs the prefill with big ubatch (2048-3200) and
extreme CPU-MoE offload (his 389->539 tok/s = ~1.4-2x on the 35B-A3B class).
NOT in any release we run (checked: bonsai2 @285542d, xing4_0-port @63c16fb,
docker b11118 — none carry the flag; closed draft, merge commit a4c31c6).
Getting it = cherry-pick a4c31c6 into a build of the xing4 fork (it touches
server/libllama plumbing, not arch code — should port cleanly) and re-measure
the A3B/Xing prefill classes. Our Bonsai is already GEMM-saturated at ~29% of
the int8 ceiling, so this lever only matters for the CPU-band models — where
Xing's 346 tok/s could double and the A3B's 3.7-6.5 might triple.

## Strata engine (Niko1221, 2026-09-27) — sm_80 gate is SOFT, port is feasible (2026-09-27 source survey)

Custom inference engine for Qwen3.8-Flash-Next on single consumer GPU + RAM:
65 tok/s @128K ctx / 95 short-chat / 539 pp with Q2_0-GSQ-RCO on RTX 5070 12GB
+ 64GB DDR5-5600 (thread post). Linux one-click, OpenAI+Anthropic-compatible
endpoints, PLE n-gram table stays on SSD (RAM need = shard1 + ~10GB):
48GB covers its Q2_0/IQ2_XS tiers — our 46GB qualifies only for Q2_0.

Source survey (shallow clone of the repo, later discarded) overturned the sm_80+ BLOCKED verdict:
- Single hard sm_80 instr in the whole tree: mma.sync.m16n8k8.tf32 in
  native_qsa_score.cu (151 lines, attention scorer only; its ldmatrix loads
  ARE sm_75-legal — Turing introduced ldmatrix). f16 twin m16n8k8.f16.f16.f32
  runs on sm_75 tensor cores: ~30-line cast-the-tiles patch.
- bf16 math: VERIFIED on this box — CUDA 13.3 cudart's cuda_bf16.h
  software-emulates bf16 on sm_75 via fp32 round-trips (nvcc -arch=sm_75,
  compiled + correct results on the 2080). Perf cost in bf16-hot inner
  loops, numerics correct. Fallback to fp16 conversion for ~10 bf16-hot
  kernels (ple, gr, fused_gr, elementwise, bf16_gemv, shared_expert...) if
  it shows.
- No cp.async, no redux.sync, no accessPolicyWindow anywhere. Expert GEMV
  hot path (s_gemv/s2_gemv/i-quants) is llama.cpp-derived fp16 — sm_75-native.
- CMake sm_80 FATAL_ERROR is a plain version check; gate removal trivial.
- Parity tests with oracle vectors for ~every kernel → kernel-by-kernel
  numerics validation built in.
Port shape: patch CMake + scorer, build sm_75, run parity suite, bench Q2_0
(37.6GB model + 29GB PLE on the 110GB free disk — fits). Estimate ~2-3
sessions + downloads. KILL if bench lands ≤15 tok/s (llama.cpp parity).
Perf physics unchanged: DDR4-2400 (~38GB/s vs their ~90) CPU expert path
~2.3x slower; 8GB VRAM = ~half their expert cache (~2800 vs ~5600
resident) → higher miss rate; i5-9600K = AVX2 only (their CPU path has an
AVX2 tier, OK). Realistic cap ~1/3 of their numbers: ~20 tok/s @128K /
~30 short-chat / ~180 pp — still 2-4x the UltraLite llama.cpp expectation
if the cache holds. Worth trying BEFORE any Ampere purchase; an Ampere+
GPU landing here remains the bigger unlock anyway (native bf16/tf32, plus
PQ2_0 Bonsai tier, exl3, DFlash2 windows at a stroke).

Our own Flash-Next attempt continues via UltraLite 37GiB + patched
llama.cpp @250b61446 (generic kernels, sm_75-safe) — every expectation
revised to the honest 5-15 tok/s class; even that = first 125B-class
model on the card.

## Gemma-12B / E4B: token_embd=q4_0 requantize trick (from net_termina's E4B post, 2026-09-06)

"llama-quantize --allow-requantize --tensor-type token_embd=q4_0" trims the
token-embedding table to q4_0: worth ~4% decode and meaningful VRAM on the
8GB-class Gemma serves (their E4B recipe trims 4.3GB of files; our E4B row
measured 181 tok/s without it). Two candidates: (a) E4B re-serve with trim —
cheap re-measure toward their 200-class claim; (b) the more interesting one:
Gemma-12B (evidence-only, ngl 45, 29.4/43.5 tok/s, AG-Bench 3/6) — the freed
VRAM could buy 1-2 more GPU layers and might promote it from "12GB-class
wanting 8GB" to a full recipe. Requires llama-quantize on the host build.

## Handoff additions (from sibling session local-ai-rtx2080-05, 2026-09-27) — run after the current queue

Two performance levers still open after the current queue (UBBoost resolved
via c9df0ee; Bonsai d-depth crowns d2 via d8574bb; token_embd trim already
queued above). Not GPU-urgent — sequence them after Flash-Next/row-12.

### 1. DFlash2 sidecar on the dense 27B crams — the live decode lever

The NEXT-IDEAS live trigger from the Cinference post: a ~600 MB Q2/Q4 drafter
for llama.cpp, applied to the dense-27B crams. DSpark on LFM2.5-8B-A1B proved
the 0.19 GB sidecar class works on this card (221 tok/s record, fully
resident). The untested application is a mid-size drafter accelerating
ThinkingCap-27B Q2_K (9.57 tok/s, acc 0.995, ngl 40) and the IQ1_S row-12
serve once measured. Steps: pick drafter candidate (~600 MB class, checked
against the target's tokenizer), rotate the pair back from the archive drive
if needed, measure acceptance + fixed-prompt decode per house method
(2-3 repeats, ranges, thinking off).

### 2. Recurrent-state snapshots for DeltaNet-class hybrids

The portable idea from
[notes/research-david19p-turing-kernel.md](notes/research-david19p-turing-kernel.md)
§"adoption-worthy ideas": explicit SSM/conv/target_feat snapshots (direct
`lcp=N reused=N`) instead of KV seq-id manipulation for the recurrent-state
part of Qwen3.5/3.8-hybrid multi-turn flows. Pure C++/GGML — b11118 docker or
the bonsai2 fork are candidate hosts. Payoff is per-turn latency on hybrid
chains, not raw tok/s; low risk, no GPU needed to draft the patch.

Housekeeping when convenient: the UBBoost section above (`## UBBoost
cherry-pick build…`) is resolved — plain-ubatch reproduction 2.4× on all 3
CPU-offload models (c9df0ee), port not needed; hardware.md still lists
16 GB RAM — the machine is 48 GB since 9f220a2.

## RESOLVED 2026-09-27: token_embd trim — no-op on our artifact family

net_termina's ~4% trick (token_embd=q4_0 requantize) applies to the OFFICIAL
ggml-org Gemma GGUFs (which carry big F16 embeddings). Our unsloth UD-Q4_K_XL
conversions of the QAT models already ship q4 embeddings — verified by
byte-identical requantize output (COPY + token-embedding-type q4_0 → same
size). E4B re-measure unnecessary (its 181 tok/s row already includes the
effect); Gemma-12B promotion stays blocked on the ngl-45 layer floor, not on
embedding VRAM.

## DFlash2 sidecar — acceptance VALIDATED, economics falsified at 8 GB (2026-09-28)

Experiment complete (evidence/dflash2-iqi-27b.jsonl): DFlash2-Q4_K_M-swa (1.14 GB)
on the head-less IQ1_S target accepts at 0.92/mean 3.76 — the sidecar class is
quant-agnostic and WORKS on this card (Supsurface prism-dflash2 runtime built
and ran first try). But hosting any >1GB drafter forces the dense target into
the CPU band (ngl 44) where decode collapses 19.7→6.2 despite the acceptance.
REMAINING LIVE TRIGGER, now precise: a ≤600 MB Q2-class DFlash2 sidecar could
host beside a FULL-OFFLOAD target (6.70+0.6+ctx_other~0.4 ≈ 8.0 with desktop —
borderline; needs -c 4096 and possibly one shed layer). Watch jmarceno/z-lab
for a Q2_K_XS-swa conversion. CAVEAT on tonight's falsification: it ran the
1.14 GB Q4_K_M-swa drafter — the ~600 MB class itself was never tested;
the conclusion likely survives (ngl-54 OOM math implies IQ1_S full-offload
alone leaves no room for any drafter + compute buffers), but the 600 MB
point remains an open measurement, not a closed one.

## TensorFold exact-spec-decode port — technique extracted, sm_75 probed, queue-opener (2026-09-27)

TensorFold (ashhart, MIT) serves byte-identical drafted decode ("drafts change speed
only") via lane-batched verify windows up to 32 rows. Full technique extraction and our
own GPU probes: `notes/tensorfold-analysis.md`, evidence
`evidence/tensorfold-exactness-probe.jsonl`. Ground measured on this card:

- wmma fp16 lanes are slot-dependent (bits depend on which tile slot a row occupies,
  both axes) → fp16-HMMA lanes are a dead end for exactness on sm_75; dp4a/IMMA
  integer lanes are exact by construction (0/1M mismatches).
- **our own stack already violates today**: E4B+MTP recipe greedy — serial is 6/6
  self-reproducible, drafted is 4/6, drafted-vs-serial only **1/6 byte-identical**
  (near-tie single-token flips, then divergence; 150 vs 91 tok/s is what the drift
  "buys"). Harness: `notes/spec-drift-test-llamacpp.sh` — should become a standard
  column for every spec-decode recipe.
- crossover economics favorable: rows_free ≈ 24-48 ideal (measured peaks @425 GB/s);
  fork-measured tile floor flat through n=8 — 16-32-row windows would ride nearly free.

Queue order (value/effort): (1) drift-test all existing MTP recipes (30 min each, shell);
(2) keyed-Gumbel exact sampling port to llama.cpp sampling layer ();
(3) Bonsai-PTQ1_0 full-lane audit — integer matmul already exact-class, patch the fork so
serial + all verify widths share one kernel path per op class, re-run the drift harness,
target 6/6 drafted==serial; then exploit the flat tile floor with d4-d8 windows (
serve 59 → 65-70 tok/s target from the kn note, with bytes as the acceptance criterion).
Blocked on: nothing — this is pure fork/patch work.
