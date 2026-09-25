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