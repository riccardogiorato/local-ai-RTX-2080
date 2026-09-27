# MLX.fast Bonsai2 contest — the 79-submission technique ladder, probed for our stack (2026-09-27)

Source: https://www.yukon.org/mlxfast (leaderboard) + https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine
(the "engine" repo; every leaderboard row is a PR there by `app/yukon-autoresearch`, merged = promoted).
Read from the PR bodies ("Submitter note" write-ups: technique, base, attribution, bitwise self-test
gates, measurements, negative results). This note extracts what transfers to the RTX 2080 stack.
Related: `notes/tensorfold-analysis.md` (the sibling exactness program), `notes/kernel-sm75-ptq1_0-investigation.md`
(the open fork-kernel item this connects to).

## The one fact that makes this relevant

**The contest model is our champion model**: Ternary Bonsai 2 27B — the PTQ1_0 ternary we serve
via the `sudoingX/llama.cpp` bonsai2 fork (5.96 GB MTP graft, 55–59 tok/s fully resident,
71.6 tok/s single-token roofline at our measured 425–427 GB/s). Their box: paired runs against a
no-speculation control on an M5 Mac, score = prefill^0.25 · decode^0.75, single stream. Record as
of 2026-09-27: **505.4% = 580.0 decode tok/s**, top of the board at **14.2 tok/round stock DFlash**
with acceptance `[16,16,16,…]` on the ranked prompts. So the board is a performance map for the
exact weights we run, on a bigger chip and a different scheduler.

Both platforms are decode weight-streaming-bound (their floor analysis: 7.7 GB/round vs ~345 GB/s
≈ 22 ms of a ~51 ms round at verify width; ours: 5.96 GB vs 425 GB/s ≈ 14 ms). Every top-line gain
on their ladder is one of: (a) more accepted tokens per weight pass, (b) fewer launches/copies on
the latency path, (c) draft tokens that cost nothing to propose.

## The core parallel (davidtai's boundary = our cap=4)

davidtai spent five submissions establishing that per-round cost on MLX is
`cost(M) = 0.04246 + 0.0125·M` — flat-slope because M=13 is exactly where `quantized.cpp`'s
`get_qmv_batch_limit` switches the qmv (vector) kernel to the qmm (matrix) kernel; extra verified
rows ride tiles the matrix path pays for anyway. The contest converged to depth 14–16 on this.
**We measured the same crossover on our card: batch cap=4 between the PT mat-vec path and the
IMMA MMQ tile path** (kn-4, `kernel-sm75-ptq1_0-investigation.md`). Turing IMMA tiles are 8/16-row,
so on the MMQ path **verify rows 5→16 are free**. The fork has never been validated past d4. This
is the same lever, one generation of hardware over.

## Item-by-item verdicts

Verdict scale: ✅ COPY (logic-level, no kernels) · 🔧 PORT (needs CUDA/fork code, integer path only)
· 🧪 MEASURE-FIRST · ❌ N/A (arch- or harness-specific).

### A. Speculation shaping — COPY or ours-already

| # | Technique (solver) | Verdict |
|---|---|---|
| 1 | **Verify width past the kernel crossover** (davidtai, i34-9) — push accepted/round 2→16 once extra rows are free | 🔧 **biggest lever.** Requires the already-open geography-pinned split-K invariance patch for ≥5-column MMQ tiles (extends `GGML_CUDA_BATCH_INVARIANT` to d5–d8). **Gate first: acceptance-vs-depth curve of the graft head, d1→d8** (`benchmarks/measure-decode.sh` + `/metrics` counters; evidence → `evidence/`). If acceptance dies past d2, this lever dies before any kernel work. Ceiling math if it doesn't: 71.6 × mean-accepted. |
| 2 | **Lookup-round drafter skip** (terrapinelf) — skip the draft forward when the proposal came from the prompt | ✅ COPY, pure scheduler logic. |
| 3 | **Prompt-span lookup proposals** (newjordan) — suffix-match committed tokens against the prompt, propose the prompt's own continuation; **unique** long-span match only | ✅ COPY and expect it **stronger here**: AG-Bench decode constantly echoes repo files just read. Their failure mode is instructive — a false short match costs a whole round (winglock's lookup-opener rule: 5.0963 vs 5.3028 base). |
| 4 | **Continued block along quoted prompt span** (DPZZxlz) | ✅ COPY, same family as 3. |
| 5 | **Leading verify boundary / early submission** (pochita0, Subflatus3, cefika) — start the verify stream behind the draft so the GPU never idles between host steps | 🧪 CUDA analog = draft/verify stream overlap or graphs. Their host gaps were 0.45–0.93 ms; on our 12–18 ms tokens the same absolute gap is proportionally *larger*. nsys census first. |
| 6 | **Trained-block mask on the drafter** (Meganpark) | 🧪 only if the graft head trains a block span. |
| 7 | **Frequency-ranked draft vocab** (terrapinelf) | 🧪 small; batch-verify already prunes by greedy. Low priority. |

### B. Kernel-level — integer path only

| # | Technique (solver) | Verdict |
|---|---|---|
| 8 | **Packed 2-bit codes fed to the matrix unit, no dequant** (polymorf, +58.5% lineage) | Ours already: the fork's PTQ1_0 IMMA path *is* this on sm_75. Their transferable lesson: the **verify-width** route (≤16 rows) wins in situ on every tower projection even where isolated microbenchmarks say otherwise — polymorf's inclusion test: 1336–1350 ms excluding gate|up vs 1300–1307 with it. Feeds item 1. |
| 9 | **Register-weight / plane-copy weight layout** (Meganpark, DPZZxlz — lane loads only its 32 bytes, ~2 ms/prompt-forward) | 🧪 their gain is simdgroup load coalescing. Our yardstick already exists: `notes/roofline_probe_sm75.cu`. If the fork's MMQ tile path streams materially below 425 GB/s, a plane-permuted PTQ1_0 tile layout is a legitimate candidate; otherwise skip. |
| 10 | **Row-tiled activation constants** (polymorf, −5% prefill; epilogue loads are the cost: 95 TF/s bare vs ~80 with) | 🧪 CUDA analog is a float4-coalesced constant layout; only if the profile shows epilogue loads dominating. Prefill matters least for a single-user box. |
| 11 | **Split-K bodies + per-shape in-situ trials, adopt only on a box win** (i34-9, DPZZxlz; winglock: in-place KV trial adopted at 1419→1288 µs) | ✅ COPY as an idea; directly entangled with 1. The trial discipline is our ranges-not-best-of rule already. |
| 12 | **Fused boundary kernel: RMSNorm + rotation + quantize in one launch** (ercumentyildirim `Qwen35FusedBoundaryQ8`) | 🔧 PORT-worthy for **decode**: single-token decode is latency-bound, launch-count reduction buys real % at 55–59 tok/s. Target the paste/pre-cast chains around the fork's MMQ call sites. |
| 13 | Softmax barrier cuts (ssalmeock), vectorized stores (dukemawex, Grok bot) | 🧪 micro-wins; check what the fork's attention epilogue already does before spending anything. |
| 14 | **FP16 activation reads at verify width** (fkiene) | ❌ **for byte-exact: forbidden here.** Our own probe: fp16 `mma.sync` lanes slot-dependent on both axes on sm_75 (0/1,048,576 exact); ptxas also silently misdecodes sm_80 forms on Turing. Only dp4a/IMMA is exact. This lab is stricter than the contest — keep it that way. |

### C. Copy/memory elimination — mostly N/A (MLX graph artifacts)

| # | Technique (solver) | Verdict |
|---|---|---|
| 15 | In-place KV append (winglock P5) | ❌ llama.cpp writes KV in place natively. Their 32 slice-copies/round was an MLX graph artifact. |
| 16 | One-launch concat + small/quad variants (winglock P6) | ❌ ggml graphs don't have that class of intermediate concat copy. |
| 17 | Narrowed asyncEval lists avoiding whole K/V buffer copies (winglock P6) | 🧪 the CUDA analog does exist — avoidable scheduler memcpys / backend splits. One nsys pass on verify rounds; cheap to falsify. |
| 18 | Residency touch behind prompt forward (Subflatus3 ~38 ms, generalized by i34-9) | ❌ N/A for fully-resident serve (that was UVM eviction under an idle gate on Apple silicon). Real analog exists only for the `exps=CPU` offload tier: prefetch experts via cudaMemcpyAsync-ahead. Side quest. |
| 19 | Host gather of embedding rows (terrapinelf, 44.1→2.6 ms seed gap) | ❌ pure harness artifact (358 MB table restore behind an idle GPU). |

### D. Methodology

- **Load-time bitwise self-tests with stock fallback, serialized in-situ trials with a ≥1% adoption threshold, per-item kill switches, "the box decides."** One step further than us: they run per-shape trial *selection* at runtime. Adoptable whenever items 1/11 land. Otherwise this is our byte-exact discipline already (`GGML_CUDA_BATCH_INVARIANT`, `spec-drift-test-llamacpp.sh` 6/6, keyed-Gumbel).
- **Cumulative-union tickets with co-author attribution** — how the top turned into a shared ladder (winglock's 505.4% record credits four other solvers byte-for-byte). Not directly portable; the reference-worthy part is that every item is independently switch-gated and exact, so unions can't regress each other.
- **Their published negative results are free information for us:** prompt-forward concurrency, command-buffer batching (100→5 buffers/round), and fused FP32 attention all measured 1.000× or slower — **CUDA-graph batching of decode rounds is known-dead, don't spend on it.** Also their toolchain probe pattern (compile-check a kernel at init, fall back on error) is the VRAM-safe way to try risky fork patches.

## How the contest tests accuracy (read from TASK.md + docs/participant-contract.md)

Two levels, and the difference matters for us:

- **Official gate: 10% token TOLERANCE, not equality.** A per-stream token-tolerance gate with
  a 10% budget; the contract states it "accepts similar output. It does not certify lossless
  output," explicitly because a multi-row speculative forward rounds differently from a
  single-row one at near-tie argmax. The candidate at depth D is checked against `live_golden_speculative{D}`
  — a per-depth oracle taped by the organizer, staged out of band (never in git) — not
  against the serial trajectory. Golden shape: one prompt, `(512 prompt_tokens,
  129 expected_tokens)`, 128 checked decode steps, single stream. All gating is done by
  `benchd`, a pinned prebuilt binary; verification/measurement code is outside the editable
  surface. Target quantization is frozen ("a lossier target substitutes a degraded model").
  Paired serial-control leg on the same box, quiescence + thermal gates on timing.
  (Track currently unarmed: `official_scoring_enabled: false`, pending-organizer sentinel.)
- **Solver culture: far stricter, self-enforced.** Every promoted PR claims emitted tokens =
  the target's greedy tokens, acceptance trace identical to base, and **every kernel variant
  load-time self-tested bitwise against stock with automatic fallback on any single-bit
  mismatch**; in-situ trials adopt only bit-identical forms. Motivation (winglock #621): union
  tickets stack strangers' changes, so bit-identical forms guarantee "a different pick costs
  microseconds, never tokens."

Consequences for this port program: their speed numbers do not depend on the loose gate
(their big wins are exactness-neutral constructions), but their 14.2 tok/round was never held
to drafted==serial bytes — byte-exactness at depth is ours to prove alone. This is why the
ranked plan puts the split-K invariance patch BEFORE depth (GGML_CUDA_BATCH_INVARIANT coverage
at d5-d8), gates every depth step at 6/6 on `spec-drift-test-llamacpp.sh`, and why their
load-time-bisect + stock-fallback + in-situ-trial pattern (§D) is the one accuracy mechanism
to copy wholesale — safe-by-construction kernel variants fit our exactness bar, which is
stricter than the contest's own.

1. sm_75 exact arithmetic lives **only** on dp4a/IMMA (measured, `mma_bitslice_probe_sm75.cu`).
2. ptxas accepts but misdecodes sm_80 `mma.sync` forms on Turing — never trust the compile.
3. 8 GB: DFlash2 sidecar economics falsified here (acceptance 0.92 real, 1.14 GB + explain cost
   not paying; `evidence/dflash2-drafter-qwen38-27b.jsonl`). Depth increase of the **embedded**
   graft costs ~nothing (draft KV rows + M=17 activations), but do the KV arithmetic at target
   context before starting. Their 14.2 tok/round is DFlash-on-Metal; our realistic candidate is
   the MTP graft at whatever depth its acceptance curve supports.
4. oomd: never `nvcc -j6` while a serve is up (both die); /tmp is 24 GiB tmpfs.

## Ranked plan (each step gated by the previous)

**Primary port target: the Ternary-Bonsai-2-27B-PTQ1_0 MTP-graft serve** (5.96 GB,
`recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md`, 55–59 tok/s), on the `sudoingX/llama.cpp`
bonsai2 fork — the same model the contest runs (Qwen3.8-27B base, 16 attention + 48 GDN layers,
same drafter class), and the only local model on the fork's IMMA batch-invariant path where the
cap=4 crossover, 71.6 tok/s ceiling and every kernel-level item were measured. Caveats: their pack
is 2-bit Hadamard-folded, ours is PTQ1_0 ternary — we take structural experiments, not kernel
source (their rotation kernels don't apply); their 3.85 GB DFlash2 sidecar stays falsified here,
so the depth rider is OUR grafted MTP head (acceptance curve = step 1). The logic-level A-family
items (lookup proposals/skip, depth declaration) are model-agnostic and spill over to every
spec-decode serve (Gemma E4B + Q8_0 MTP pair, ThinkingCap d2, Xing4).

1. **(free)** Acceptance-vs-depth curve, graft head d1→d8, `measure-decode.sh`, evidence →
   `evidence/mtp-graft-depth-curve.jsonl`. Decides item 1's entire value. Success shape:
   mean-accepted still rising at d4, ideally toward ×4 tokens/weight-pass (their board proves
   the *model family* sustains ~16/16 with the right drafter — on faster silicon).
2. **(free)** Prompt-span lookup proposals + lookup-skip in the fork's spec path (items 2–4).
   Expect high hit rates on AG-Bench decode. Uniqueness rule mandatory.
3. **(the port)** The split-K invariance patch (already the open item), unlocking d5–d8
   batch-verify on the MMQ path — davidtai's boundary trick transplanted one arch over.
   Byte-exact gate: 6/6 drift harness at every depth step.
4. **(medium)** Fused norm/quant launches on the decode path (item 12) + the one-nsys-pass
   copy census (items 5, 17).
5. **(gated)** Plane-copy / tile-layout work (items 9–10) only if the roofline probe shows the
   fork's tile path below the 425 GB/s ceiling, and the acceptance curve justified depth in step 1.

## What we are deliberately NOT taking

fp16-anything on the exact path (item 14); Metal graph-bandwidth tricks (15–16); UVM residency
 folklore (18–19); their z-verification split-K specifics (Metal threadgroup shapes); CUDA-graph
decode batching (their measured negative). Each either violates our byte-exact bar, is an
Apple-scheduler artifact, or is measured-dead on their side already.