# RTX 2080 exact attention-scoring experiment

Local experiment against Strata v0.1.45 (`machine.json` records the exact commit),
Flash-Next 125B GSQ-RCO Q2_0, RTX 2080 8 GiB, 128K context, int8 KV with
32K resident cells. The custom change is opt-in and only dispatches on real
compute capability 7.5 devices.

## What changed

The CUDA prompt scorer's exact thread kernel now accepts compile-time tile
sizes. The selected custom tile (`STRATA_SCORES_TURING=2`) uses 32 queries,
32 staged key blocks and a 256-block range per CTA, with 128 threads rather
than the upstream exact scorer's 256 threads / 64 queries / 512-block range.
The per-score arithmetic and reduction tree are unchanged. This reduces
per-CTA register/shared-memory demand and allows more CTAs to reside on an SM.
Default dispatch and decode dispatch are unchanged.

This retunes an existing upstream exact scorer. Most of the improvement over
the standing default warp scorer comes from that existing scorer; it must not
all be attributed to the new tile. The custom tile additionally improves on
upstream's exact scorer. Alternate 8/16-lane tree partitions were also tried,
matched the reference, and were slower; they were removed from the final patch.
Their measurements remain in `lane-microbench.json`.

## Validation and reproduction

`custom-turing.patch` contains the source and benchmark-harness changes.
`build.log` records the successful CUDA sm_75 build. HIP and SYCL toolchains
were not available; no cross-backend performance claim is made.

Run `python3 bench-kernels.py` with the patched checkout beside this repo.
`kernel-validation.json` records 50 runs (10 references and 40 cross-variant comparisons; stock, upstream exact and
three custom tiles across ten context/query/seed cases). Each run dumps
all logical score bytes and selected IDs, omitting uninitialized buffer padding,
and requires its SHA-256 to match the stock output. All cross-variant comparisons passed.
Timings are CUDA event averages over 30 repetitions, not client wall time.

For 2,048 queries at ~100K context, scoring measured:

- Standing warp scorer: 63.245 ms.
- Existing upstream exact scorer: 8.711 ms.
- Custom tile 2: 8.022 ms (8.6% more scoring throughput than upstream exact).

These are scoring-only figures, not overall model speedups. Top-k and every
other model phase still run. The earlier hypothetical 24% whole-prefill gain
is not a measured claim.

## Real coding workloads

`make-workloads.py` builds two requests from Strata's existing
`tools/agent_turns_bench.py`:

- `expert-cache.3`: a coding conversation containing actual design/interface/
  implementation file reads and search results.
- `server-option.4`: a longer coding conversation containing actual README,
  HTTP server, frontend and documentation file reads, plus tool definitions.

The `code-25k` / `code-100k` filenames are approximate labels. Actual token
counts, prefix reuse and phase timings come from engine logs / JSON responses.
These are reproducible scripted coding-agent histories, not a claim that an
OpenCode or Claude Code client itself was run.

`run-full.py` compares stock, custom scorer, and custom scorer plus Strata's
existing opt-in bitwise Turing series. It also runs the actual installed Pi CLI
on a fresh copy of `task1-js-bugfix`, using an isolated local provider config,
then verifies the tests and checks that protected inputs were not modified.
The pristine task fails its tests. Model loading is excluded from workload
wall time. No tasks run concurrently on the GPU.

## Storage prerequisite discovered by the real workload

The old model alias resolved to `/mnt/archive`, a rotational USB disk. The first
20,053-token real prompt stalled in the PLE path with the GPU idle and an engine
stall report showing `blk_mq_get_tag`. That attempt was stopped; its logs are
preserved as `cold-hdd.*` and are excluded from kernel comparisons.

At the user's request both required GGUF shards were copied to the NVMe, verified against the existing manifest and independently read-back hashed.
The existing dense pack, MTP draft, tokenizer and expert profile were already on
NVMe. Both benchmark arms use the same model/storage/configuration. The existing model alias now resolves to the NVMe directory, so existing configurations use the SSD automatically. The HDD originals remain as backups. Copy hashes
and independent SSD read-back verification are recorded separately.

## Full-model results on real coding histories

One measured sample per arm and workload, in stock / custom / combined order.
These are observed A/B values, not confidence bounds or a hardware ceiling.
All six requests read their complete input (zero cached tokens). GPU clock,
power and temperature samples are retained in `gpu-samples.csv`.

| Configuration | 20,053-token coding history | 121,776-token coding history |
| --- | ---: | ---: |
| Stock default | 656.5 tok/s; 30.54 s | 580.6 tok/s; 209.73 s |
| Custom scorer only | 667.6 tok/s; 30.04 s | 658.4 tok/s; 184.97 s |
| Custom scorer + existing Turing series | 692.2 tok/s; 28.97 s | 696.1 tok/s; 174.94 s |

The combined configuration measured +5.4% prompt throughput at 20K and +19.9%
at 122K. The latter reduces prompt-read time by 34.8 seconds (16.6%). The custom
scorer alone measured +1.7% and +13.4% respectively; the small result is near
normal run-to-run noise. Most scorer-level gain over stock comes from enabling
the upstream exact scorer, with the new tile adding the separately measured
8.6% scorer-throughput gain over upstream's exact tile.

The whole-model greedy reply matches stock on the 20K history. The 122K replies
differ. Its final 937-token batched chunk enters Strata's existing automatic
CPU-share path; that path chooses CPU/GPU expert work using measured timing
and has different rounding. This is a plausible source of full-model variation,
not proof of its sole cause. A separate diagnostic compares the custom and
reference scorer on the real model's actual inputs; its timing is excluded
from performance results.

## Actual Pi coding-agent task

All three configurations solved the shopping-cart task and passed its verifier.
The original fixture fails. Pi used real read / bash / edit tools in isolated
working copies; test files and task/verification instructions stayed unchanged.

| Configuration | Task wall | Tool executions | Generated tokens | Tests |
| --- | ---: | ---: | ---: | --- |
| Stock | 22.98 s | 6 | 598 | PASS |
| Custom | 30.72 s | 7 | 792 | PASS |
| Combined | 18.01 s | 6 | 405 | PASS |

Pi chose different actions and generated different amounts of text. These task
wall times therefore do not establish a fixed-work agent-speed percentage. The
controlled long-input prefill comparisons are the performance evidence.

An initial Pi attempt had a benchmark-only URL error (duplicated `/v1`) and
never reached inference. It was corrected to match the existing working
Anthropic-compatible provider URL shape; the reference test was rerun. The
failed transport attempt is retained under `discarded-transport/` and excluded.

## Direct validation on actual model inputs

The 121,776-token coding history was ingested with
`STRATA_SCORES_TURING_CHECK=1`. For each custom-score call, the engine recomputed
scores with the original warp kernel and compared every valid score bit pattern
(including the tail, excluding unused padding). All **5,712 calls** matched,
covering active block counts from 65 to 30,443: **zero mismatches**.
`real-score-validation.json` records the result; `real-check.engine.log` records
every check. This mode allocates temporary buffers, runs both kernels and
synchronizes; it is disabled in the normal configuration and excluded from
performance numbers. It directly validates scorer arithmetic on real inputs;
it does not claim all adaptive CPU/GPU model execution is bitwise deterministic.

## Adopted local configuration and rollback

The normal `strata-0145/strata-q20-gsq-0145-tailnet.json` and the recipe config
now enable:

```json
"STRATA_SCORES_TURING": "2",
"STRATA_SM75_PERF": "1"
```

The executable is the patched `build-turing-0145/strata`. No normal configuration
enables the diagnostic check. Runtime GGUF paths retain their existing spelling;
`~/models/flashnext-gsq-rco` now points to the verified sibling NVMe directory.
Other needed assets were already on NVMe. The original HDD files remain as backups.

Remove the two opt-in variables to restore stock kernel dispatch. The previous
configurations are retained as `standing-config-before.json` and
`recipe-config-before.json`; the unchanged executable is retained locally as
`strata-stock` (ignored by git). This task does not publish an upstream PR or
start a public server. The temporary localhost benchmark servers are stopped.
