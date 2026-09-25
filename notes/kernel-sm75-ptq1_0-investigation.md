# SM75 kernel investigation — PTQ1_0 ternary mat-vec (2026-09-25)

Objective: squeeze the PTQ1_0 (1.75 bpw ternary) decode path on the TU104/SM75 beyond the
fork's (sudoingX/llama.cpp @ 285542d) numbers, per the owner's "squeeze this GPU" directive.

## Calibrated roofline (measured, not spec-sheet)

Pure-streaming-read probe kernel (nvcc -arch=sm_75): **425–427 GB/s achieved** of the
448 GB/s spec on this 2080 → confirmed realistic ceiling for a memory-bound kernel.
Weights are 5.95 GiB → perfect-kernel single-token ceiling = **71.6 tok/s**.

Weighted traffic analysis: activations (2.5 MB, PT layout) are L2-resident with ~1%
DRAM re-fetch; weight streaming dominates; no traffic waste found in the design.

## Baselines (llama-bench, fork @ 285542d, on `Ternary-Bonsai-2-27B-PTQ1_0-MTP-Q8_0.gguf`)

| bench | value | bus utilization |
|---|---|---|
| tg128 (-b 1) | 44.87 ± 0.04 tok/s | 267 GB/s = **62.7% of achievable** |
| pp128 / pp512 | 493 / 574 tok/s | prefill healthy |
| serve MTP d1 (2-col passes), repetitive | 59.3 tok/s, acceptance 1.0 | derived per-pass cost ≈ **1.52× a single token** |

## Experiments (branch `kn-sm75-tune`)

| exp | change | result | verdict |
|---|---|---|---|
| kn-1 | `__launch_bounds__` 128,4 → 128,2 on ncols≤2 (reg cap 64→128; actual usage 102–118 regs at n=1 per cuobjdump) | 44.87 ± 0.09 | **disproven: register pressure is not the n=1 limiter** |
| kn-2 | partials smem 16→8 KiB/CTA (rows_per_cta halves; ~5 resident CTAs given 102 regs) | 45.12 ± 0.28 | **disproven: occupancy is not the limiter either** (+0.6%, within 2σ) |

Both cheap hypotheses killed with clean A/B. The n=1 kernel is latency-tolerant at 63%
of bus — the leftover headroom does not yield to launch-config tuning on SM75.

## Where the loss actually is (evidence so far)

Serve-time MTP is where the card pays: the 2-column pass costs 1.52× a 1-column pass
(same ratio the fork author measured on SM86), so every d1 verification wastes ~35% of
the bus time re-streaming weights for the second token. Reducing the n=2..4 batch-cost
ratio is the highest-value kernel target on this card (serve 59 → 65–70 tok/s class),
more than chasing the last 37% at n=1.

Next: measure the exact n-slope (b=1,2,3,5), then attack the batch path.

## Resolution (2026-09-25 morning)

**The goal's INT8-tensor-core kernel already exists in the fork and runs on this card.**
Proof: `cuobjdump -sass libggml-cuda.so | grep -c IMMA` = **173,049 sites** in our sm_75
build — the PTQ1_0 tile loader (branch-free trit decode feeding `TURING_MMA_AVAILABLE`
mma.sync fragments) and the guarded edge tiles ARE the ternary tensor-core kernel;
`TURING_MMA_AVAILABLE` is defined for `__CUDA_ARCH__ >= 750`.

**Evaluation of the tensor-core path on SM75:**
| path | pp512 | note |
|---|---|---|
| INT8-MMA tiles (fork default) | 580.65 tok/s | accuracy-correct; fork's default validated |
| cuBLAS fp16-dequant (env knob) | 596.05 tok/s | +2.5% at the documented accuracy loss — the fork's accuracy choice holds on SM75 |

**kn-4: SM75 retune of the batch-crossover cap (fork constant was RTX-3060-tuned):**
| n | PT mat-vec (ppN tok/s) | MMQ tiles (ppN tok/s) | winner |
|---|---|---|---|
| 2 | 67.29 | 35.34 | PT 1.9x |
| 3 | 88.51 | 55.52 | PT 1.6x |
| 4 | 85.33 | 74.48 | PT 1.15x |
| 5 (control, both take tiles) | 90.24 | 90.79 | equal — sanity check |

The MMQ tile pass has a flat ~55–56 ms floor (n-independent through 8) vs the mat-vec's
22.2 ms single-token cost: tiles need ≥5 columns to amortize on TU104. **The fork's
cap=4 is correct for SM75** — no change warranted; fork defaults validated on this card
and the kn-sm75-tune branch returned clean to upstream 285542d.

**Serve implications:** Bonsai/Swift MTP d1 (n=2) pays 29.8 ms/pass — 1.34× a single
token, better than the serve-era 1.52× estimate implied; d4 (n=5) rides the tiles at
11.1 ms/token. The d1 serving choice (graft README default) is optimal on this card.

Artifacts: `notes/roofline_probe_sm75.cu` (from-scratch calibration kernel).

## Postscript: TC-32K KV-RAM AG-Bench (2026-09-25, experiment #2 of the backlog sprint)

thinkingcap-27b-q2k-32k-kvram: 4/6 — same pass-set as its 8K profile (React and
JS→TS both fail at the 480 s cap, not from truncation). Conclusion: the family's two
standing failures are reasoning-style, not context-window, limits; the KV-in-RAM
profile (4x context, ~15% decode cost) changes nothing in agent-loop outcomes.
