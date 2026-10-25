# RTX 2080 cap-280W sustained burn (2026-10-25)

Question: with the power limit raised 165 -> 280 W (board firmware max, `nvidia-smi -pl 280`,
non-persistent), what does the card actually draw and at what temperature under a maximum
power-virus load? Prior box knowledge (`hardware.md`, 2026-10-18 walk) ended at 225 W.

## Conditions

- Driver 615.78.08, CUDA 13.4 UMD, persistence mode on. Power limit 280 W set live this session.
- Standing Bolt E4B serve resident and idle throughout (llama-server, 5,844 MiB VRAM, ~2.3 GiB free).
- Burner: `burn.cu`, cuBLAS fp32 SGEMM 4096^3, `CUBLAS_COMPUTE_32F`, back-to-back with a
  per-iteration device sync, `nvcc -O3 -arch=sm_75`. fp16 tensor-op mode drew 195-200 W in a
  12 s sanity run (compute-bound, not power-bound) so fp32 CUDA-core mode was used.
- 480 s sustained run, `nvidia-smi dmon -s puct -d 1` sampling. Warm start: short validation
  runs preceded the main run, first burn sample already at 51 C.
- Baseline before any load this session: ~18 W idle, 28 C.

## Results (ranges over the run, not best-of)

| Metric | Full 480 s (453 samples) | Last 120 s steady state |
|---|---|---|
| Board power | 222-246 W, avg 238.3 | 244-246 W, avg 244.9 |
| GPU temp | 51-80 C, avg 73.7 | plateau 80 C |
| SM clock | 1860-1935 MHz | fixed 1860 MHz |
| Mem clock | 6800 MHz sustained | 6800 MHz |

Power histogram: 220-230 W x21, 230-240 W x229, 240-250 W x203 samples.

- Throttle state: HW thermal slowdown, HW power braking, SW thermal slowdown all Not Active the
  whole run. "SW Power Capping" was active (expected: the governor rides the V/F curve edge);
  its cumulative counter (~38,214 s at read time) carries all history since driver load, so it
  is not directly attributable to this run.
- Post-run recovery: 19.7 W, 300 MHz, 58 C within seconds; idle unaffected.
- Kernel log for Xid / NVIDIA errors this boot: clean. No visual anomalies, no serve disruption.
- Throughput: 10.62 TFLOP/s avg fp32 (37,099 gemms / 480 s), consistent with the says-nothing
  power question but confirms the load is real compute, not starved.

## Verdict

**280 W is safe on this card, but unreachable by the workload.** Even the fp32 power-virus
load plateaus at 244-246 W and 80 C: the binding constraint is the voltage/frequency curve
(governor settles at 1860 MHz hot), not the 280 W cap. Idle stays ~18-20 W regardless of cap.
The raise therefore costs nothing (no part of the envelope was exercised) but buys no heat
either. To actually move sustained draw toward the cap, the next lever is locking SM clocks
(`nvidia-smi -lgc 2160`, tested separately): P scales roughly with f x V^2 at the fixed max
voltage bin, projected ~270-280 W with temps in the low 80s Cs, still inside governance.

Ops notes: cap resets to 225 W at reboot (never back to the old 165 W unless set). The
2026-10-18 165 W sweet-spot verdict is unaffected: no workload crossed the 225 W mark even
at the 280 W cap, so serving efficiency conclusions stand unchanged.

## Locked-clock run (`-lgc 2160`, 300 s)

Clock lock was applied and confirmed (`gpuClkMin 2160, gpuClkMax 2160`), same burner, 300 s.
**Outcome: byte-for-byte no change versus unlocked.** SM clock 1860-1935 MHz (never 2160),
power 220-245 W (steady state 242-245 W avg 243.8), temp plateau 79 C, throughput 10.66
TFLOP/s vs 10.62 unlocked. The SW Power Capping cumulative counter grew ~421 s during the
run: the card spent essentially all loaded time in active power-cap enforcement, and the power
governor overrides the clock lock rather than granting 2160 MHz. That is protection-by-design,
not a failure of the lock command.

Consequence: the enforced power limit is more conservative than the reported board draw —
at ~245 W measured board power the model already counts itself capped against 280 W
(~12% margin). So the cap is real but unreachable-adjacent in practice:

**Max sustained board draw of this RTX 2080, by software, is ~245 W.** No combination of
`-pl 280` and clock locks moves it; the voltage/frequency table plus power model are the
ceiling. To add room heat beyond that, the levers are CPU load (i5-9600K adds up to ~100-150 W)
or hardware (ambient cooling raises the natural boost bins only marginally at these clocks).

Governor restored with `-rgc` after the run; idle confirmed 300 MHz / 18.1 W / 32 C.

## Serve A/B: prefill/decode vs power cap (2026-10-25, Bolt E4B standing serve)

Four passes against the live Bolt E4B llama-server (llama.cpp b11804-pinned, spec draft
dflash, ctx 65,536, servePort 8080, idle otherwise). Each run: a unique ~32.3K-token
content-neutral prompt (defeats prompt caching without tying decode acceptance to the cap
arm), n_predict 192, temperature 0. Server-reported `timings.prompt_per_second` /
`predicted_per_second` (lab convention). Mirrored schedule 165/280/225 - 225/280/165,
12 s settle per cap change, 15 s cooldown parked at 280 between runs. `prefill_ab.py`,
rows in `prefill-ab.jsonl`, earlier passes archived as `prefill-ab-pass1-nopower.jsonl`,
`prefill-ab-pass2-nopower.jsonl`, `prefill-ab-pass3.jsonl`.

### Prefill tok/s (n=8 per cap, ranges across all passes)

| Cap W | Prefill tok/s range | Board power during run | SM clock | Temp |
|---:|---|---|---|---|
| 165 | 2,025-2,042 | pinning the cap (max 167.6-181.6) | dips to 1,510-1,710 under load | 51-55 C |
| 225 | 2,142-2,153 | riding the cap (max 225.9-229.1) | 1,890-1,935 | 56-58 C |
| 280 | 2,145-2,164 | max 240.1-245.4, never the cap | up to 1,935 | 56-59 C |

**Verdict: the manual 165 W cap was costing the Bolt serve 5.3-5.9% prefill; 225 W (the card
default) recovers all of it; 280 W adds nothing** (225 vs 280 overlap within noise, both
because prefill tops out at ~245 W board draw anyway, matching the virus finding above).
At 225 W the prefill rides the cap, which is exactly what you want from a watts-for-
performance trade: every extra permitted watt is being converted to tokens.

Decode: only single clean 192-token windows per cap with distinct contents, so acceptance
noise dominates (94.5-109.4 tok/s across arms, temperature-0 outputs with content-matched
duplicates identical to the digit). No credible cap effect on decode, consistent with the
2026-10-18 Strata walk showing decode flat to 125 W: decode remains watts-flat.

**Recommendation: leave the cap at the 225 W default and stop re-applying 165 W before
serve sessions of GPU-resident models like Bolt E4B.** No persistence needed; nothing on
this box re-sets the cap at boot (checked systemd units, autostart, shell init) and the
driver default after reboot is 225 W. The 2026-10-18 "165 W sweet spot" verdict is not
contradicted: it was measured on the PCIe-co-bound Flash-Next 125B serve, where the loss
was 1.7-2.4%; GPU-resident Bolt E4B prefill is compute-bound and loses ~3x that at 165 W.
Set per-model as needed.

## Artifacts

- `burn.cu` - burner source (fp16 + fp32 modes; rebuild with `nvcc -O3 -arch=sm_75 burn.cu -lcublas -o burn`)
- `dmon.log` - 1 Hz board telemetry, 500 s window (stock governor, cap 280)
- `dmon-lgc.log` - same at locked 2160 MHz
- `burn-full.out`, `burn-lgc.out`, `f32-4096.out`, `sanity.out`, `sync-check.out` - runs
- `prefill_ab.py` + `prefill-ab.jsonl` - serve A/B harness and canonical pass-4 rows
- `prefill-ab-pass*.jsonl` - earlier passes (pass1/2 without power telemetry)
