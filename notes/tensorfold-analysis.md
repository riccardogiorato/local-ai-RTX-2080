# TensorFold — the exact-speculative-decoding secret sauce, probed for sm_75 (2026-09-27)

Source: github.com/ashhart/TensorFold, MIT. Read in full (clone + kernel-level read of
 mlx, CUDA families, engine, drafters, docs, tests). This note is the extraction that
 matters for THIS lab plus what we measured on our own card tonight. Artifacts:
 `notes/mma_bitslice_probe_sm75.cu` (probe source, run below), `notes/spec-drift-test-llamacpp.sh`
 (the drift harness), evidence in `evidence/tensorfold-exactness-probe.jsonl`.

## What it is

Local-LLM server with one property nobody else ships: **drafted decode is byte-identical
to serial decode — drafts change speed only.** Speculative verification of up to 32 lanes
(draft-tree candidates) in one multi-row forward pass, OpenAI-compatible endpoint, Apple
Silicon (MLX) first with a CUDA/Blackwell path for DGX Spark. Benchmarks: 4–4.7× serial
with drafts on M5 Max / M3 Ultra; claimed 1.6–3× over vLLM+MTP on Spark.

**They can prove bytes because every layer of the stack is built to make it provable.**
That's the sauce. Not a kernel trick — a discipline.

## The exactness discipline (portable rules, in their own code)

1. **One arithmetic per op, parameterized by weight shape only, never by row count.**
   Split-K/chunk counts are functions of (N, K) — "it sets the bits"
   (`simd_qmm.py:304-308`). Rows are padded (out-of-range rows read row R−1, results
   dropped: `simd_qmm.py:155-156`). Invariant: `lane_qmm.py:22-25` — "rows 1..M of any
   call equal the same rows computed one at a time (tested for M = 1..48 and all
   projection shapes)".
2. **Serial decoding goes through the same kernels** — serial *defines* the reference
   bits (`lane_glue.py:17-21`). There is no separate fast serial path.
3. **Anti-fast-math:** adds that could reassociate are `fma(a, one, b)` with `one` read
   from a GPU buffer; CUDA extensions compile with `--fmad=false`; constants baked into
   kernel source, not template args (MLX runs a std::regex over template args per call,
   ~7 µs); TF32 banned on the reference path.
4. **Exact dequant trick:** nibbles are never shifted — `q' = word & (0xF << 4s)` against
   `x' = x * 2^-4s` (exact power of two) so `x'q' = xq` exactly (`simd_qmm.py:20-22, 61`).
5. **Empirical, per-architecture bit-stability checks at install/load time with fallback
   routing:** `check()` per weight shape (~5.12M outputs); if MMA ≠ scalar chain on some
   chip, *one-row calls route through the MMA kernel too* (`mma_one_row`)
   (`simd_qmm.py:379-387, 425-448`). Their whole lane stack rests on one measured fact:
   on M3 Ultra, fp32 MMA == the forward FMA chain, bit for bit.
6. **Kernel-source hashes in every cache/snapshot key** — "a snapshot computed by other
   kernels has other bits". Comments in kernel source are part of the hash.
7. **Exact attention:** absolute-position chunking (CHUNK=512/TILE=64, "fixed: part of
   arithmetic"), chunks merged in chunk order, fp32 online softmax, all-masked tiles are
   provable no-ops; KV **rollback trims, never pads** — padded-then-masked layouts flipped
   near-ties against serial (their own bug, mine is #A3 below).
8. **Recurrent layers (GDN):** tree nodes walked with the serial kernel's arithmetic
   verbatim ("copied from mlx_lm's gated_delta_step"), no state stored; the accepted path
   is *replayed* to commit.
9. **Exact sampling:** the token at position p = argmax over kept candidates of
   `logit_i/T + g(seed, p, i)` where g = Gumbel from a splitmix64 hash of
   (seed, position, token-id) — an exact draw that depends only on the row's own logits
   and position, and ties break by token id
   (`engine/exact_sampling.py:8-18`, "checked against `choose` on 46,750 rows, ties
   included"). **A draft is accepted exactly when it equals that token** — acceptance
   becomes equality, so drafting can never change output bytes.
10. **fp32 routers, ties broken by id** (MoE top-k), radix-select top-k on the GPU,
    atomic-free reductions everywhere, fixed warp shuffle trees.

## Perf techniques worth stealing (orthogonal to exactness)

- `tile_weight`: regroup packed weights so a lane reads one contiguous NT×64 block per
  op — "same values, same op… 8-15% faster at 1-32 rows"; on their CUDA target this took
  the 27B matmuls from 107-130 to 200-220 GB/s (of 240 measured).
- Prologue fusion: norms/activations folded into the matmul's load. "Everything after the
  load is unchanged, so a row's bits are the unfused call's" — perf without touching bits.
- Glue fusion: ~1,400 small kernels/forward → "each step between two matmuls is one
  kernel"; live 60.02 → 58.30 ms/round.
- Prefill grid alignment (`prefill_align = 2048`) + on-disk prefix snapshots keyed by
  tokens + kernel fingerprint. For an agent harness sending the same system block, new
  sessions resume from an exact, store-bought prefill.
- **Window economics:** `_paying_drafts` sizes draft windows from *measured* per-width
  pass costs; `cheap_window=4` guard — "unguarded 32-token windows ran 17 tok/s against
  ~30 plain". (Note for us: our fork's measured tile crossover at n=5 shows the same rule
  holds on TU104 — kn-4 in `notes/kernel-sm75-ptq1_0-investigation.md`.)
- Live A/B flips of bit-identical kernel variants (`TF_KERNEL_AB`), decided by replaying
  agent turns "to the same sha". Bizarre and excellent.
- CUDA path notes: cuBLAS/`torch.matmul`/`F.linear` are **banned from the verify path**
  ("choose algorithms and K splits by the number of rows"); draft vocab truncation;
  CUDA-graph capture for launch-bound models; drafters per-request by measured
  tokens-per-ms; fixed rank-order partial sums for 2-GPU instead of NCCL all-reduce order.

## Testing infra (the part that keeps it honest)

- `torch.equal`, never `allclose`, across ROWS=[1..128] + a permutation test on real
  kernels; history-dependent fake targets (`lane_fakes.py`) where any rollback/padding
  mistake shows as byte divergence from the fake's own serial decode.
- On the wire: request flag `"draft": false` gives the serial reference; the usage
  payload carries `token_sha`; **drafted and serial replies must hash equal** on every
  benchmark run, sampled and greedy.

## Our probes on the RTX 2080 (TU104, sm_75) — run tonight, all reproducible

### P1 · fp16 MMA bit-stability (`mma_bitslice_probe_sm75.cu`)

| question | result |
|---|---|
| **negative result:** plain `mma.sync.m16n8k8…f32.f16.f16.f32` on sm_75 | ptxas (CUDA 13.3) *accepts and executes* it, but a one-hot calibration gives D[3][2]=7.03906 for exactly 7 with structured garbage in every other slot — the sm_80 form silently misdecodes on Turing. Use `wmma.sync.m16n16k16` (the documented fp32-acc path here) or f16-acc mma. |
| wmma vs ascending-K scalar FMA chain (A1) | **not bit-equal**: 16.2% eq @K=64, 2.6% @512, 0.2% @5120 → their M3-Ultra property does NOT transfer. Fine for us: `mma_one_row` fallback (rule #5) exists precisely for this. |
| row-neighbor invariance (A2) | **100% pass** (all K) — a row's bits are unchanged by garbage in other rows |
| row-slot invariance (A3) | **100% FAIL** — same data at tile row 9 ≠ tile row 0 (exactly 15/16 rows differ, i.e. every slot but the reference row) |
| column-slot invariance (A5) | **100% FAIL** — the N axis is also slot-dependent on this arch |
| duplicate-slots mirror (A6) | 15 of 16 rows differ from row 0 even with all rows identical — slot-dependence is total |
| determinism (A4) | 0 mismatches across trials |

   **Verdict: fp16 tensor-core lanes are DEAD for exactness on sm_75.** A lane kernel on
   this card must live on the integer path — dp4a/IMMA — where integers associate and
   every invariance holds by construction (dp4a sanity: 0/1,048,576 mismatches). The
   fork's PTQ1_0 IMMA kernels (173k sites, kn-note) are already on the right path;
   up to ~16 free bits of launch geometry are the lane-amortization headroom our
   probes measure, not new arithmetic.

### P2 · crossover math (probe section C/D + fork kn-4)

Measured peaks (min..max of 5 reps after warmup): wmma fp16 70–92 "FLOPs" (=35-46 G-MAC),
scalar FFMA 5.5–5.66 G-MAC (≈11.3 TF ≈ spec 10.06 ✓), dp4a 43–45 G-MAC ≈ the card's
89-TOPS INT8 rating ✓. For a 17408×5120 4-bit layer (44.6 MB) at the measured
425 GB/s: weight-stream time 104.9 µs vs HMMA row-time ≈2-5 µs ⇒ **rows_free ≈ 24-48 at
ideal kernel arithmetic** — comfortably beyond the 16-32 lane windows TensorFold serves.
The fork's measured reality (kn-4): tiles have a flat 55-56 ms floor from n=1 through 8
(weights streamed once), mat-vec wins below n=5. Ideal vs real gap (55 vs 22 ms single
pass) is the engineering target if we ever want a homegrown lane kernel; the *economics*
already hold.

### P3 · the drift test on our own stack (`spec-drift-test-llamacpp.sh`)

The E4B QAT recipe (b11118 digest, MTP d2), greedy, 6 prompts, each mode run twice:

| comparison | identical |
|---|---|
| serial vs serial (B1–B2) | **6/6 — serial serving is fully deterministic on this card** |
| drafted vs drafted (A1–A2) | **4/6 — the drafted path is not even self-deterministic** |
| drafted vs serial (A1–B1) | **1/6 — drafting changes output bytes today** |

Divergence style: single-token near-tie flips deep in the answer ("condition **of**" vs
"condition **for**", "**Answer:**" vs "**Conclusion:**"), then wholesale divergence — the
exact signature TensorFold's `exact_attention.py` documents fixing
("diverged from its own serial decode at characters 591, 1,439 and 1,664 on three prompts").
Speeds in the same test: 150 tok/s drafted vs 91 serial (1.64×) — so today we pay for our
speedup with non-reproducible agent transcripts. Prime suspects given P1: f16 tile
kernels in the verify batch (fattn tile / any M-mma op) and atomics/geometry that depends
on batch shape; attribution needs a fork-level kernel A/B, not argued here.

## What we can actually take, ranked by value-per-effort

1. **The drift harness — DONE, in-tree** (`notes/spec-drift-test-llamacpp.sh`). Every
   spec-decode recipe here should get an A/B drift row: serial vs drafted hashes on a
   fixed prompt set. This is TensorFold's `draft:false`-sha protocol, 100 lines of shell.
2. **Exact keyed sampling (port `exact_sampling.py`)** — splitmix64 Gumbel-max keyed
   (seed, position, token-id), ties by id, into llama.cpp's sampling layer. ~1-2 days of
   C++. Makes temp>0 decode reproducible and turns spec acceptance into equality for
   sampled runs — independent of matmul exactness.
3. **Bonsai/PTQ1_0 full-lane audit** — the ternary matmul is integer-exact ALREADY
   (P1 + fork IMMA); the remaining drift surface is attention + sampling + launch
   geometry. Patch the fork so both serial and every verify width share one kernel path
   per op class, then re-run P3 on Bonsai: target ≥ 6/6 drafted==serial greedy. If
   the 55-56 ms flat tile floor is exploited (windows ≥ 5), d4-d8 drafting becomes
   nearly free passes — the "serve 59 → 65-70 tok/s" target from the kn note, now with
   byte-exactness as the acceptance criterion instead of acceptance-rate photonics.
4. **Attention discipline** ( TensorFold's absolute-position chunking + trim-don't-pad
   rollback) — medium effort in a fork; do it after 2-3 prove insufficient.
5. **Perf items, non-blocking:** `tile_weight`-style weight regroup for the PTQ1_0 tile
   loader (probably already close), prefix-snapshot prefill grid for the agent recipes
   (the AG-Bench harness re-sends big system blocks), stall guard = `cheap_window`
   economics already empirically set on this card (n≈5).
6. **No-go for this card:** all MLX/Metal paths (specifications only), Triton bf16
   `tl.dot` and `mma.m16n8k16.f32-acc` (sm_80 floor — probe P1), EXL3 trellis (format),
   DFlash2 vendored MLX code (pattern only), second-GPU NCCL tricks (need a second GPU).

## Model-by-model

| slot | current bit-invariance status | lane-exactness path |
|---|---|---|
| Bonsai-2 27B PTQ1_0 (fast-27B champion) | matmul integer-exact; drift surface = attn/glue/sampler | items 2+3, biggest win on the card |
| Gemma-4 E4B QAT (MTP d2, 181 tok/s) | drifts (P3, measured 5/6) | needs attention-path pinning first (f16 tile kernels) |
| Qwen3.5-4B/9B MTP (registry pair) | not yet measured — run P3 on them | harness + samplers apply as-is |
| Qwen3.5-35B-A3B (CPU experts) | CPU float paths deterministic per-row in principle; unmeasured | low priority — not speed-critical |
| Flash-Next / IQ-below-2bpw tier | thinking already broken at these bitrates | exactness moot until capability passes |

Honest caveats on P3: one evening, one model, six prompts (20-token prompts → 150-260-token
greedy answers, flash-attn on, cache_prompt reuse). The rates are directional, not tight —
but the qualitative finding is unambiguous, because the two control comparisons bootstrap
it: serial is 6/6 reproducible (so the machine and stack are deterministic without
drafts), while the drafted path cannot even reproduce itself (2/6 unrepeatable). Also
note: the MTP *acceptance-rate* numbers in our earlier recipes were "draft predicts
target argmax" statistics — they can be ~0.99 while bytes still drift, because one
near-tie flip in the verify batch poisons every token after it.