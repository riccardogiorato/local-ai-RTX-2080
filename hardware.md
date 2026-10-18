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
| RAM | **64 GB (62 GiB) DDR4-3200 since 2026-10-12**: 4×16 GB Corsair Vengeance LPX CMK32GX4M2E3200C16 (two identical 2×16 kits, 2 DIMMs per channel), XMP 3200 MT/s CL16 trained first boot on ASUS ROG STRIX Z390-F (BIOS 2203). Passed a 4×14 GB parallel memtester pass (56 GB, bus-saturated, all patterns, 0 failures, 1 h 56 min), kernel log clean. Prior eras: 48 GB mixed (G.Skill F4-3200C16-8GVKB + Corsair) at 2533 MT/s from 2026-10-06, at 2400 MT/s from 2026-09-27 (XMP failed on the mixed population), 16 GB before that. Era-bound numbers stay in recipes as measured |
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
## GPU power limit

### Current standing chat: Strata v0.1.45 · Flash-Next Q2_0 125B (2026-10-18)

One pinned calibrated 128K/32K-resident serve, same executable and weights throughout. Two ladder runs per point; the power walk uses both directions and a 60-second cooldown at every checkpoint. All values below are ranges over this run, not best-of or comparisons with historical measurements.

#### Controlled context ladder at 225 W

| Input class | Actual prompt tokens | Prefill tok/s | Decode after fill tok/s | Request wall s | Needle |
|---|---:|---:|---:|---:|---|
| 32K | 32,767 | 701.3–708.9 | 40.5–56.9 | 49.6–51.5 | 2/2 |
| 64K | 65,553 | 708.4 | 47.1–50.6 | 96.4–96.7 | 2/2 |
| 80K | 81,938 | 706.4–709.8 | 48.0–48.3 | 119.5–120.0 | 2/2 |
| 96K | 98,321 | 704.0–705.9 | 45.9–48.4 | 143.3–143.9 | 2/2 |
| 128K | 130,833 | 702.7–704.6 | 42.2–51.2 | 189.5–190.9 | 2/2 |

128K is the assigned 131,072-token context; its prompt leaves space for the requested 192 output tokens. All long inputs use actual code/prose, zero prefix reuse and an exact key at about 10% depth.

#### Power limit versus throughput

| Limit W | Short decode tok/s | 30K prefill tok/s | Decode at 30K tok/s | 100K prefill tok/s | Decode at 100K tok/s |
|---:|---:|---:|---:|---:|---:|
| 225 | 48.9–63.1 | 709.2–714.5 | 48.4–48.8 | 706.9–709.5 | 47.2–49.3 |
| 190 | 48.3–62.6 | 713.0–713.6 | 48.4–50.3 | 701.8–702.1 | 47.2–48.4 |
| 165 | 50.1–63.6 | 707.8–708.3 | 48.1–49.5 | 692.3–694.8 | 46.1–49.9 |
| 145 | 47.4–62.9 | 696.8–698.9 | 45.8–47.3 | 677.1–679.0 | 37.3–48.1 |
| 125 | 49.2–61.4 | 663.3 | 43.6 | 645.0 | 48.3 |

The 145 W 100K range includes the extra recheck on the ascending footstep. The 125 W midpoint has one checkpoint; other limits have two. Short-decode ranges include the three fixed prompt classes.

#### Board telemetry during the 100K arm

| Limit W | Prefill W | Decode W | Prefill SM MHz | Decode SM MHz | Prefill °C | Decode °C | Prefill PCIe RX MB/s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 225 | 206.9–208.1 | 163.8–165.9 | 1,869–1,870 | 1,875 | 72.2–73.0 | 72.0–72.6 | 12,736–12,837 |
| 190 | 181.7–182.4 | 159.9–165.0 | 1,809–1,815 | 1,875–1,890 | 68.7–69.9 | 69.9–70.0 | 12,248–12,569 |
| 165 | 160.4–160.7 | 155.4–155.7 | 1,725–1,733 | 1,879–1,884 | 65.2–66.6 | 67.0–67.9 | 12,415–12,554 |
| 145 | 142.1–142.2 | 135.2–142.3 | 1,632–1,643 | 1,850–1,868 | 61.1–63.7 | 62.7–64.3 | 12,059–12,294 |
| 125 | 122.5 | 123.5 | 1,509 | 1,768 | 58.4 | 59.2 | 11,545 |

Telemetry entries are ranges of per-request window means. Measurement records include window min/max from the raw 200 ms GPU samples; PCIe traffic is sampled at 1 Hz in nvidia-smi’s reported MB/s. GPU board power excludes CPU and RAM power.

#### Ascending 145 W recheck

- Step 3, walk, run 0: 677.1 tok/s prefill, 47.0 tok/s decode, 155.4 s wall; needle passed.
- Step 5, walk, run 0: 679.0 tok/s prefill, 37.3 tok/s decode, 156.1 s wall; needle passed.
- Step 5, recheck, run 1: 678.1 tok/s prefill, 48.1 tok/s decode, 155.1 s wall; needle passed.

All 29 long-context needle checks passed. There was one loaded server instance; cleanup restored 225 W, stopped the owned server and both sampler processes, and verified the standing config was unchanged.

#### Verdict

**Use 165 W as the low-loss sweet spot for this pinned 128K-class Strata serve;
145 W no longer meets the under-4% long-prefill criterion.** At 100K input,
165 W costs **1.7–2.4% prefill throughput** while reducing measured prefill board
power by **22.3–22.9%**. At 145 W, prefill costs **4.2–4.4%** on direction-matched
comparisons for about **31% less board power**. Descending samples are compared
with the initial 225 W checkpoint; ascending samples and the extra 145 W recheck
are compared with the final 225 W checkpoint. Using every possible pairing of
145 W and 225 W samples gives a wider **3.9–4.6%** loss range. The 225 W 100K
references changed only 706.9 → 709.5 tok/s (+0.4%) over the walk.

The 30K 145 W penalty is smaller, **1.5–2.5%** on the same direction-matched
basis. The old 30K recommendation therefore does not fully transfer to 100K
inputs. The 125 W midpoint saves more power but costs **8.8–9.1%** at 100K.
This recommendation is one model/build observation; no persistent power setting
was changed, and the box was restored to 225 W.

Decode shows **no monotonic cap-dependent slowdown down to 125 W**: 100K decode
at 125 W was 48.3 tok/s versus 47.2–49.3 at 225 W. The complete 145 W range does
include one 37.3 tok/s dip; its immediate same-limit recheck returned 48.1, while
the descending sample was 47.0. Keep that dip in the evidence: these observations
support RAM/PCIe-limited decode but do not establish perfectly flat decode on
every request. All settings retained the calibrated adaptive expert cache and
speculative decoding, so output/routing differences remain part of the workload.

The older “prefill is purely GPU-bound” interpretation is too simple here.
At 225 W, 100K prefill averaged **206.9–208.1 W**, **1,869–1,870 MHz**, about
**99.7% GPU utilization**, and **12.7–12.8 GB/s PCIe receive traffic** as reported
by nvidia-smi dmon. At 165 W, clocks fell to 1,725–1,733 MHz while prefill lost
only 1.7–2.4%; at 145 W the repeatable cost crossed 4%. This is consistent with
GPU work co-bound with transfer/host work, rather than long KV streaming making
power savings entirely free. PCIe counters are indicative, not an exact bus-
saturation measurement; isolated raw dmon samples exceed physical line rate.

Discovery selected the fleet-record standing Q2_0 chat recipe and highest adopted
chat config suffix, `0145`, rather than the newer file mtime of the IQ3_XXS quality
candidate. Engine source: `477ac13cbe8e582c20484871ce459d20d82df09d`, tag
`v0.1.45-dirty`; the exact locally tuned binary SHA-256 and both resolved NVMe
weight paths are in the evidence header. Serve: `python3 -u -m serve.server
--engine strata --config <run-local pinned-config.json> --host 127.0.0.1
--port 8080`, from the v0.1.45 checkout, using the standing calibrated engine
arguments unchanged. IQ3_XXS and the separate Qwen3.6 A3B lineage remain future
power-sweep passes.

[Measurement JSONL](benchmarks/power/strata-power-v2-20261018.jsonl) ·
[Pinned protocol and discovery](benchmarks/power/strata-power-v2-20261018/README.md) ·
[Range analysis](benchmarks/power/strata-power-v2-20261018/analysis.json) ·
[Runner](benchmarks/power/strata-power-sweep.py)

### Historical reference: Strata v0.1.43 (2026-10-12)


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

## CPU clock and expert-pool workers (measured 2026-10-12)

Same Strata 0.1.43 chat config on DDR4-3200, `benchmarks/strata-env-probe.py` (3 short prompts + a 32K needle per boot).

| Arm | Short decode | 32K prefill | Decode after 32K | Notes |
|---|---|---|---|---|
| Stock 4.3 GHz all-core | 53.3 / 47.8 / 50.7 | 654 | 31.6 | 55 C core peak, 82 W package |
| MSR 0x1AD 47x6 (asked 4.7) | 53.5 / 37.8 / 47.3 | 657 | 32.6 | ran at 4.53 GHz avg, capped 4.6 by intel_pstate; 67 C, 115 W, 1.341 V |
| 5 pool workers (default) x2 boots | 54.7 / 35.6 / 34.0, 54.9 / 51.0 / 51.7 | 662 / 656 | 31.5 / 33.3 | first boot cold |
| `--pool-workers 6` x2 boots | 36.7 / 34.5 / 36.6, 38.4 / 32.2 / 35.2 | 657 / 655 | 20.4 / 21.9 | 7 threads on 6 cores |

CPU clock does not move decode (+6% clock, flat within noise), and neither did +26% RAM bandwidth (2533 -> 3200).
Decode does scale with worker count up to the 6 physical cores (2/3/5 workers: 36/45/52 tok/s), and the default already
uses all 6 (5 workers + the draining host thread). A 6th worker oversubscribes and costs about 30% (-35% after 32K).
Reading: the CPU expert pool is limited by how many scattered RAM fetches the 6 non-SMT cores keep in flight, not by
clock or bandwidth. Levers left: more hardware threads (i9-9900K, 8C/16T, same socket) or fewer pool fetches.
The synthetic all-core AVX2 burn hit 95 C in 1 s at 47x and self-aborted; Strata itself peaked at 67 C.
Data: [OC monitor](benchmarks/cpu/oc47f-strata-20261012.csv), [stock](benchmarks/results/strata-oc47f-stock-probe-20261012.json) /
[47x](benchmarks/results/strata-oc47f-47-probe-20261012.json) / [workers](benchmarks/results/strata-0143-workers6-probe-20261012.json) probes,
[script](benchmarks/cpu/oc47-strata-only.sh).
