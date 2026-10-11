# Hardware fingerprint

All recipes in this repo run on this machine. If a number here is cited elsewhere, these are the conditions behind it.

## GPU

| Field | Value | Source |
|---|---|---|
| Model | NVIDIA GeForce RTX 2080 | nvidia-smi |
| Chip | TU104 (Turing, SM75) | NVIDIA Turing whitepaper; videocardz spec DB |
| VRAM | 8,192 MiB GDDR6 | nvidia-smi |
| Bandwidth | 448 GB/s | notebookcheck spec DB |
| CUDA cores | 2,944 | notebookcheck spec DB |
| Driver | 610.57.04 (KMD), CUDA UMD 13.3 | nvidia-smi |
| Toolkit | CUDA 13.3.1 (pacman) | pacman |

## Host

| Field | Value |
|---|---|
| CPU | Intel Core i5-9600K — 6 cores / 6 threads @ 3.70 GHz |
| RAM | 48 GB (46 GiB; 4-DIMM 2×8+2×16 DDR4: G.Skill F4-3200C16-8GVKB SR + Corsair CMK32GX4M2E3200C16 DR, 2DPC mixed) — **2533 MT/s since 2026-10-06** (2600/2666 failed to train; 2533 passed a full 4×8 GB parallel memtester battery, bus-saturated, zero failures, MCE/EDAC clean on ASUS ROG STRIX Z390-F). Prior eras: 2400 MT/s from 2026-09-27 (XMP failed on the mixed population; pre-2026-09-27 numbers were 16 GB) — era-bound numbers stay in recipes as measured |
| OS | Arch Linux / Omarchy (kernel 7.2.3-arch1-3), Wayland |
| Desktop baseline VRAM | **0 since 2026-10-06** (desktop moved to the iGPU: i915 drives the display, 2080 fully headless — 2 MiB / 18 W idle receipts). Before that: ~520 MiB (Hyprland + shell) — subtracted from residency numbers for pre-2026-10-06 runs |
| Container runtime | Docker via sudo; nvidia-container-toolkit (CDI mode) installed 2026-09-23 |

## Host ops traps (2026-09-28)

- **Never overlap heavy CUDA compilation (`nvcc -j6`) with a serving GPU session.** Depth-sweep serve runs died mid-suite (graceful llama-server shutdown, no errors) while a parallel `cmake --build` ran elsewhere; `systemd-oomd` is active on this machine. The earlier 24-request surveys that ran with no concurrent build never hit it. Sequence heavy jobs.
- `pkill -f llama-server` inside a compound command kills the invoking shell itself (its own command line matches the pattern). Use `pkill -x llama-server`.
- `/tmp` is tmpfs (24 GiB, RAM-backed): large clones/build trees there spend RAM twice.

## Measurement conventions

- Decode/prefill rates are **server-reported** (`timings.predicted_per_second`, `timings.prompt_per_second` from llama.cpp streaming responses), not client wall-clock.
- "Short-fill" means a ≈2 K-token prompt in a large assigned context; "filled" probes prefill a context-sized prompt to the stated length before measuring decode.
- TTFT = first content token (first streamed delta with non-empty `content`).
- Every speed run repeats at least 2–3 times; the range is reported, never a single best-of run.
- Thinking (`enable_thinking`) is disabled for all comparative/capability measurements unless the row says otherwise; the Qwen3.5 chat template enables it by default.
## GPU power limit (measured 2026-10-12)

Strata 0.1.43, Flash-Next 125B Q2_0 chat config (128K, KV streaming, calibrated), one server start, the limit
changed live in the order 225 -> 190 -> 165 -> 145 -> 125 -> 145 -> 165 -> 190 -> 225 W. GPU board power from
`nvidia-smi` sampled every 0.2 s ([data](benchmarks/power/strata-0143-power-sweep-20261012.jsonl),
[script](benchmarks/power/strata-power-sweep.py)).

| Limit | Short decode | Decode at 30K | 30K prefill | W decoding | W prefilling |
|---|---|---|---|---|---|
| 225 W (default) | 49.0 / 49.7 | 33.3 / 33.3 | 614 / 637 | 137-159 | 189-202 |
| 190 W | 51.8 / 50.5 | 34.4 / 34.6 | 636 / 630 | 141-154 | 177-179 |
| 165 W | 46.9 / 49.2 | 35.4 / 34.0 | 625 / 626 | 142-149 | 158 |
| 145 W | 47.1 / 47.4 | 35.1 / 34.7 | 614 / 612 | 138-140 | 141 |
| 125 W (minimum) | 48.9 | 34.1 | 581 | 123 | 122 |

Decode is RAM/PCIe-bound and does not slow at any limit (differences are run-to-run noise). Prefill is the only
GPU-bound phase: -2-4% at 145 W for ~30% less GPU power, -7% at 125 W for ~38% less. Sweet spot **145 W**
(`sudo nvidia-smi -pl 145`, resets at reboot). GPU board power only; CPU and RAM draw are not in these numbers.
