# Research: David19p/custom-llm-kernel-2080 (goal #2, 2026-09-25)

Read-only analysis (see agent transcript for provenance). MIT, 3 commits, single author,
last touched 2026-05-20, hard-locked to Qwen3.5-9B-class hybrid (48 DeltaNet + 16 KV
layers). Built for sm_75; BF16 banned; FP16 storage + FP32 draft compute.

## Reading verdict
Research-grade design document, not adoptable software: draft GGUF artifacts not published/bundled;
no Linux/2080 end-to-end proof; tool-parity incomplete (target decoding is greedy argmax —
top_p/top_k/min_p logged not applied); custom server (not llama.cpp). **Watch, don't build.**

## Its measured 2080 numbers (the only published set)
| Benchmark | baseline AR | DFlash+DDTree | accepted len | speedup |
|---|---|---|---|---|
| HumanEval | 46.35 tok/s | **145.04 tok/s** | 5.89 | 3.13× |
| Math500 | 49.54 tok/s | **126.70 tok/s** | 5.16 | 2.56× |

Per-prompt peaks 208-210 tok/s at AL 8.5. Baseline 49.54-consistent with our Qwen3.5-9B no-draft
60.7-class measurement — their 2.5-3× DDTree speedup factors apply on top of the same-silicon
baseline we already know.

## Key mechanisms
- **DDTree** (Ringel & Romano paper port): diffusion drafter emits per-position distributions for
  a whole block (16 nodes), tree is verified in ONE target forward pass with ancestor-only attention
  mask. Avoids the single-trajectory prune-on-mismatch penalty.
- **PFlash**: 3-token-runs-through-a-0.6B-drafter block-sparse attention to alpha-select blocks
  (default 0.12, NIAH 0.85-0.99), np.percentile-score keep (NIAH keep_ratio 0.05). Honest self-note:
  parks target+draft weights while the 0.6B runs ("may cost more than it saves"); auto-off with tools.
- **KV**: asymmetric K/V type pairs (Q4_0-K + Q8_0-V), tq3_0 ternary-KV experiment, GGML_CUDA_FA_ALL_QUANTS forced
- **Recurrent-state checkpointing**: explicit SSM/conv/target_feat snapshots for hybrid models — proves KV
  seq-id manipulation is the wrong abstraction for the recurrent-state part; direct snapshot (lcp=N
  reused=N) is right.

## Three adoption-worthy ideas for our stack (b11118 + bonsai2 fork)
1. **Recurrent-state snapshots for DeltaNet-class paths** — portable pure C++/GGML; helps any
   Qwen3.8/3.5-hybrid multi-turn flow.
2. **Asymmetric K/V KV pairs as default** (e.g. Q4_0-K / Q8_0-V): the direct middle ground for our
   measured "9B needs q4_0 KV for 64K" finding — K quantized harder, V at Q8 keeps value-reconstruction
   precision.
3. **FlashPrefill block-sparse head (WMMA sm_70+)**: mean_K → score → block-select prefill path is
   Turing-legal; contained, low-risk port candidate for the fork's long-prompt path.

None applied tonight; recorded as design-informed leads. Sources: [repo](https://github.com/David19p/custom-llm-kernel-2080),
[DDTree paper](https://liranringel.github.io/ddtree/DDTree.pdf), [ddtree code](https://github.com/liranringel/ddtree),
[NVIDIA forum thread](https://forums.developer.nvidia.com/t/ddtree-plus-diffusion-drafting-dflash-to-optimize-gb10/366643).