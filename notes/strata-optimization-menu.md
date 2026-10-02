# Strata sm_75 optimization menu — ranked for 8 GB VRAM + i5-9600K AVX2 + 46 GiB DDR4-2400

Researched 2026-10-02 (upstream bench dirs + GitHub PR history + HF/web sweep)
by the optimization agent; parent session A/Bs the entries. Physics anchor from
upstream: decode is bounded by the CPU expert pool — 664.7 MB of expert
bytes/token at ~43-51 GB/s on our class of CPU ("86% exposed, the residual
chain is serial"); our measured floor 22.5 ms/token. Anything that moves
expert bytes to VRAM or feeds the pool faster is the whole game.

## Ranked A/B deltas (on top of the working serve line)

1. **Custom expert profile + warm adaptive cache** (biggest; upstream measured
   88.0 → 105.2 tok/s code decode on a 5080 from warm/adaptive). Run once with
   `--dump-routing trace.bin` → `tools/make_profile.py` → restart with the
   custom profile; keep `--adapt-every 4`. Byte-exact arms use
   `--adapt-swaps 0`. Evidence: bench/results/2026-09-29-layer-split.
2. **VRAM scavenging**: `--vram-reserve-mib 500` + headless run; explicit
   `--expert-cache 3000` to test auto's sizing. ~1 GB ≈ ~700 slots ≈ +34%
   cache. Risk: desktop spikes (issue class #279).
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
9. **`--kv q4_0` at 64K+ only**: +8% decode at 128K (67.4 vs 62.4 tok/s, +146
   slots) but perplexity +8-12% on long docs; irrelevant at ctx 4096. (Also
   feeds the KV-types experiment.)
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
