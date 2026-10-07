# Strata sm_75 optimization menu — ranked for 8 GB VRAM + i5-9600K AVX2 + 46 GiB DDR4-2400

Researched 2026-10-02 (upstream bench dirs + GitHub PR history + HF/web sweep)
by the optimization agent; parent session A/Bs the entries. Physics anchor from
upstream: decode is bounded by the CPU expert pool — 664.7 MB of expert
bytes/token at ~43-51 GB/s on our class of CPU ("86% exposed, the residual
chain is serial"); our measured floor 22.5 ms/token. Anything that moves
expert bytes to VRAM or feeds the pool faster is the whole game.

## Ranked A/B deltas (on top of the working serve line)

0. **KV upload prefetch** — ADOPTED 2026-10-07 (`STRATA_KV_PREFETCH=1` in the
   chat config's env): overlaps the streamed-KV RAM→VRAM uploads with prefill
   compute. Deep 90K fill 534→602-603 t/s on two independent boots (+13%),
   real 30K 558-583→608-625, deep decode stabilized 35-38 (was wobbly to 20.8).
   Quality-neutral (scheduling only). The one surviving knob of the 2026-10-07
   full-repo inventory sweep; the rest measured flat or false — see below.

1. **Custom expert profile + warm adaptive cache** (biggest; upstream measured
   88.0 → 105.2 tok/s code decode on a 5080 from warm/adaptive). Run once with
   `--dump-routing trace.bin` → `tools/make_profile.py` → restart with the
   custom profile; keep `--adapt-every 4`. Byte-exact arms use
   `--adapt-swaps 0`. Evidence: bench/results/2026-09-29-layer-split.
   (2026-10-07 update: `--adapt-every 4 --adapt-async 1` +
   `STRATA_EXCHANGE_ROTATE=1` probed FLAT on short probes, sizing unchanged —
   its claim is in-session routing drift; only a full suite gate can judge.
   SUITE-ONLY CANDIDATE, not adopted.)
2. **VRAM scavenging** — MEASURED 2026-10-06 (headless + 2533 MT/s):
   `--vram-reserve-mib 500` **adopted for the 16K bench class**: synth prefill
   +55–65% (420→620–702 t/s, reproduced on a second boot), real-text
   540→732–838 t/s, decode flat; auto's own sizing stays optimal, explicit N
   not needed. Floor found: r300/r400 trip the engine's LOW warning (<200 MiB
   free, gen-160 rejected at 94 MiB), r200 kills the MTP head (-6 MiB).
   **Falsified at 128K chat class**: the prompt chunk is pinned at 512 by
   design (prompt buffers must fit in every expert cache; explicit 1024 is
   clamped down), so no VRAM-side knob moves 128K prefill at kv-int8. 128K
   levers that would work all trade quality or context: `--kv q4_0` (#9) or a
   lower `--max-context`. Evidence: `vram_scavenge_headless_ab`.
3. **`--ple-row-cache 268435456`** (256 MiB vs 1 MiB default): the tail-stall
   shave; PLE idle stalls of 50-150 ms documented (ple_reader.hpp).
4. **`--prefill auto:16384`** — TTFT lever (PR #282 +15% on 32K prompts).
5. **`--pcie-frac` sweep 0.15/0.35/0.50** around auto's 0.25-0.26 — few-%.
6. **`--pool-workers 4/5/6`** — machine-specific; 4 may win on this desktop.
7. **Spec stack after warm acceptance**: `--spec 4 --spec-min-p 0.5`, then
   `--suffix-draft 5` on code/repeat workloads (+6-11% code edits upstream);
   suffix drafting widens verify to spec+2 — sequence AFTER acceptance warms.
8. **Turing kernel variants**: `git pull` to 0.1.33 (`a1eb951`) — `0bea892`
   fixes the fused-GR two-half split ON TURING (`STRATA_GR_V3=1`);
   `STRATA_HC_SPLIT=0/1`; `--no-fused-gr`; `--shared-late`; `--no-token-graph`.
9. **`--kv q4_0` at 64K+ only**: MEASURED 2026-10-07 (128K class, with KV
   streaming on): **falsified** — no prefill gain over int8 streaming
   (561-564 vs 558-583 t/s) despite freeing the most VRAM, so its +8-12%
   long-doc perplexity buys nothing here. The winning KV lever is
   **`--kv-resident 32768` streaming itself** (adopted: chunk 512→2048,
   real prefill ~2.8×, outputs bit-identical, ~1.7 GB RAM), and
   **`--kv k8v4` + streaming** is the measured optional next +8-15%
   (two boots, needles pass; value rounding — user's call). 16K-class
   context: irrelevant at ctx 4096. (Also feeds the KV-types experiment.)
10. **Measured negative — do not spend**: TC-GEMV on sm_75 (1.3-2.2x SLOWER,
    their own tc-gemv-sm75 bench, PR #343); `--gpu-only-full` is a floor probe
    not a mode; STRATA_KQ256 dead; `--native-bf16*` are diagnostics;
    STRATA_QSA_WARP is a pre-sm_80 arm; CJK draft vocab (+14% decode) only
    for Chinese output.

## Host-side (receipted)

- **RAM speed is the top physical lever**: DDR4-2400 after the XMP failure on
  mixed DIMMs; the pool is DRAM-bound, so a matched 3200 kit = +22-33% memory
  bandwidth ≈ est. +10-20% decode. Upstream's own troubleshooting row says the
  same ("RAM below rated speed slows the CPU half").
- **memlock/ulimit**: their 3090 bench ran LimitMEMLOCK=infinity; our ctest
  flagged the ulimit — check how much of the 31.64 GiB arena pins (mlock
  denied may cost GPU miss-copy speed and reclaim-shield).
- **PCIe healthy** (11.9-12.3 GB/s H2D probe = Gen3 x16); nothing to tune.
- **ReBAR impossible on Turing** — cross off permanently.
- **THP already [always]** on this Arch install; no action.
- **Clocks hygiene only**: `nvidia-smi -pm 1`, optional `-lgc` lock to
  de-variance A/B arms — decode's GPU share is small.

Full source list: agent report in the session; key: bench/results/* (repo),
DETAILS.md:176-178/300-309/740, PRs #279/#282/#343, commit 0bea892 (Turing GR
fix), HF discussion 14, xhinker Medium write-ups.
