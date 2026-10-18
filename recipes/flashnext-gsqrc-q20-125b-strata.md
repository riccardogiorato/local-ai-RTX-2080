# Qwen3.8-Flash-Next GSQ-RCO Q2_0 125B · Strata engine — the fleet-record row


## IQ3_XXS same-engine probe: the quality tier, with a decode tax (2026-10-18)

The repo's "great" tier, downloaded as the standing Q2_0 replacement candidate (shard 1 only, 43.8 GiB:
shard 2 is byte-identical to Q2_0's and symlinked). Same v0.1.44 engine and chat knobs (0.35/80, spec-min-p
0.70, KV int8, 128K/32K resident), two probe boots, `q3xxs-probe.py` (strata_bench --long + needle 32k/128k):
2 boots dissent-free, needles **12/12 byte-exact**.

| Phase | Q2_0 standing | IQ3_XXS | Delta |
|---|---|---|---|
| Short decode | 51.8-54.9 tok/s | 34.2-35.4 | **-35%** |
| 32K prefill | 644-659 t/s | 522.8-528.0 | -19% |
| 16K / 4K prefill | (same band range) | 530-551 / 515-519 | ~-20% |
| Agent turn decode | 36.6-37.7 tok/s | 30.6-31.6 | -17% |
| Agent turn TTFT | ~8.8 s | 9.5-9.6 s | +8% |
| 128K needle fill | 476.6 t/s (0144 chat) | 295-299 | -38% |

Fit is honest on 64 GB: 10-11 GiB RAM headroom during serve, VRAM 5.7/8 GiB, no cache thrash.
Reading: the docs' -25-30% prediction holds for prefill, but decode pays ~35% because the whole
expert pool (43.8 vs 34 GB) crosses PCIe per token; prefill amortizes reads. Retrieval quality intact.
Status: **🧪 lab-tested (probe tier)**, adoption decision pending: chat stays Q2_0-day/coder-fast;
IQ3_XXS is the pick when answer quality outweighs round-trip speed. Weights: `~/models/flashnext-gsq-rco-iq3xxs/`
(shard-1 sha `219ea929…` verified vs HF; shard-2 symlink to the Q2_0 blob, sha `316b46f3…`); pack
`strata-port/packs/iq3_xxs-gsq`; config [strata-q3xxs-gsq-0144-tailnet.json](strata-configs/strata-q3xxs-gsq-0144-tailnet.json).
Evidence: `iq3_xxs_probe_vs_q2_0` in [evidence/strata-q20-sm75-port.jsonl](../evidence/strata-q20-sm75-port.jsonl) ·
raw rows [benchmarks/strata-multiagent/results/q3xxs-20261018-195009](../benchmarks/strata-multiagent/results/q3xxs-20261018-195009).

**AG-Bench v2.2 same night (128K suite config, cap 900, 0.35/80): 11/11 passed at 1465 s, 0 suspect**
(Q2_0 same protocol: 11/11 at 1135 s). The quality tier holds the perfect score; the wall pays the
predicted +29%. Suite config `strata-port/suite-0144-q3xxs-128k.json`; runner
`benchmarks/strata-multiagent/q3xxs-v22.py`; rows
[benchmarks/results/strata-0144-q3xxs-r0-20261018-211126.jsonl](../benchmarks/results/strata-0144-q3xxs-r0-20261018-211126.jsonl).
Updated verdict: **IQ3_XXS matches Q2_0's 11/11 on the eleven-task bench; choose per use-case, not quality risk.**


## Local Turing scorer and SSD runtime (2026-10-18)

The standing 0.1.45 config now enables the local exact-score tile
`STRATA_SCORES_TURING=2` together with the existing upstream
`STRATA_SM75_PERF=1` series. Real coding-session histories, zero prefix reuse,
same 128K / int8 KV / 32K resident setup on the RTX 2080:

- 20,053 tokens: **656.5 → 692.2 tok/s (+5.4%)**.
- 121,776 tokens: **580.6 → 696.1 tok/s (+19.9%)**, prompt read **209.7 → 174.9 s**.
- Custom scorer alone: 667.6 / 658.4 tok/s respectively. Most scorer-level gain
  versus the standing warp scorer comes from the existing upstream exact scorer;
  the new tile separately improves its 2,048-query / 100K scoring throughput by 8.6%.

One full-model sample per configuration and workload; observed gains, not a
physical ceiling or confidence interval. Actual Pi bug-fix tasks passed on stock,
custom and combined builds with test files unchanged. Pi changed its actions and
generated token counts, so its task wall times are not a controlled speedup.
The custom scorer matched the reference bit-for-bit on every valid score of
**5,712 calls over the real 121K history**, as well as 40 cross-variant synthetic
comparisons. Whole-model long replies vary with the existing adaptive CPU/GPU
paths; the 20K greedy reply matched on all three builds.

The real prompt exposed cold PLE reads from the external rotational HDD. Both
required GGUF shards now live on NVMe, independently read-back verified against
the original SHA-256 manifest. The canonical model symlink was switched, keeping
existing configuration paths valid. Dense pack, MTP, tokenizer and expert profile
were already on NVMe. All final kernel comparisons use the same SSD placement;
no storage gain is attributed to the kernel. HDD originals remain as backups.

[Measurements, patch, scripts and rollback](../experiments/rtx2080-prefill-20261018/README.md).

## Current runtime: v0.1.45 (2026-10-18)

Stock tag `v0.1.45` built for sm_75 by the standard flags (`strata-0145/build-turing-0145`; kquants off as before).
This release carries **PR #1821's Turing prompt-attention kernel** (the GitHub PR is still marked open, but the work is in
the tag: `qsa_prompt_attn.cu`, 37.9 -> 29.2 KB shared memory = two blocks/SM, int8 K/V register prefetch, K/V union buffer).
Own-card A/B against 0.1.44 on the standing chat config, same bodies, quiet box: **24.7K fill 485.8 -> 636.5 tok/s (+31%),
99.9K fill 476.6 -> 582.7 tok/s (+22%)**, decode parity (quiet-box top band 54.9-55.7 both engines). Adopted; [chat config](strata-configs/strata-q20-gsq-0145-tailnet.json), knobs unchanged from the 0.1.44 line.

New v0.1.45 knobs probed on this rig (all neutral, none adopted): `--prefill-pipe` is layer-split only (n/a single GPU);
`STRATA_ADAPT_EVICT_SYNC=0` decode 41.4 vs 39.4 median, fill 586.4 vs 582.7 (keep the default ON); `--prompt-cache-spread`
identical reuse on a mid-history edit probe (49,152/50,769 both policies). The 4-cpu-kquant-kq plugin that ships in both
0145 build dirs is inert for this model (flashnext runs without it; see the qwen36 recipe for the one model where it mattered).

Noise trap re-confirmed: a `ps2run` (~1 core, load 4.7-5.6 on 6c) cut BOTH engines' decode medians ~30% during first probes;
stopping it restored the 54.x band. Same class as the orphaned-vite record in the host-ops memory.

## Current runtime: v0.1.44 (2026-10-13)

Stock tag `v0.1.44` (`ed4773eb`) built for sm_75 with the same flags and ggml pin as 0.1.43
(`strata-0144/build-turing-0144/strata`, MMQ kquants off); [chat config](strata-configs/strata-q20-gsq-0144-tailnet.json)
is the 0.1.43 one with the new engine. Upstream says GSQ-RCO answers are byte-identical to 0.1.43.1.
Same-night ABBA probe on the chat config: short decode median 0.1.43 **52.8**, 0.1.44 **51.8** tok/s (noise), tail skip
off 42.4; 32K prefill 657 tok/s on both; needle passes on both. Greedy outputs match on 2 of 4 cases; the other two vary
from boot to boot within each engine, so the probe cannot confirm byte identity. Full v2.2 suite: **10/11 at 709 s**,
86 requests, aggregate decode 47.3 tok/s (0.1.43: 11/11 at 1009 s, 105 requests, 44.8). The miss is task10 (bank filter):
prompt grew to 16,435 tokens, past the 16K bench context. ABBA task10-only repeats: 0.1.44 pass 115 s / pass 91 s,
0.1.43 fail (same overflow) 108 s / pass 106 s. Verdict: flaky task, not a regression.

**Recalibrated 2026-10-15**: `tools/calibrate.py` on 0.1.44 (891 s) picked **pcie-frac 0.35** (sweep median
47.2 vs the standing 0.20's 42.4) and **adapt-swaps 80** (53.5/54.8 vs default 51.4/51.7); the fourth calibrate
probe of the pcie knob since the RAM-3200 upgrade and the first ABBA confirm to separate cleanly: short decode
**51.7/51.8 → 54.8/54.9 tok/s (+6%)** on a 4-boot ABBA (`benchmarks/strata-multiagent/knob-probe.py`, 18 chats per
boot). spec-min-p 0.70 and 5 workers confirmed unchanged. Both chat configs now carry 0.35/80. Evidence:
`strata_calibrate_0144` in `evidence/strata-q20-sm75-port.jsonl`, raw calibrate + ABBA in
`benchmarks/strata-multiagent/results/`.

An earlier probe the same evening read ~25% slower decode on **both** engines: an orphaned `vite dev` preview server
from the lava-lamp one-shot bench was spinning one core. Kept in `benchmarks/results/contended/` as a cautionary record.

## Previous runtime: v0.1.43 (2026-10-11)

Stock tag `v0.1.43` built for sm_75 (`strata-0143/build-turing-0143/strata`), serve from the `strata-0143`
worktree; [chat config](strata-configs/strata-q20-gsq-0143-tailnet.json) is the 0.1.42 one with the new engine.
Same-night ABBA probe on the chat config, short decode median: 0.1.42 **49.8**, 0.1.43 **52.5** tok/s, 0.1.43
with tail skip off 39.9 (the tail skip is worth ~30% on this card); 32K prefill unchanged (643-648). Full v2.2
suite: **11/11 at 1009 s** (0.1.42: 10/11 at 815 s); the longer wall is more agent work (105 vs 91 requests,
+28% tokens generated) at a faster per-token decode (44.6 vs 43.8 tok/s).

## Previous runtime: v0.1.42 (2026-10-10)

Built the stock tag `v0.1.42` (`61b3fb5d`) for CUDA sm_75 with native experts,
MMQ kquants off and ggml pinned at `3cf03257`. Source worktree: `strata-0142`;
binary: `build-turing-0142/strata`. The standing `strata-port` checkout now uses
that tag's Python server too; its previous source remains on branch `main`.

Adopted for chat after repeated short probes, the full AG-Bench comparison and
diagnostic repeats. [Chat config](strata-configs/strata-q20-gsq-0142-tailnet.json)
retains the calibrated PCIe share **0.20**, draft floor **0.70**, adaptive cache,
128K context, 32K KV-resident window and KV prefetch. Tail skipping is explicitly
set to **7**, the new CUDA default; it changes answers. Set
`STRATA_ROUTE_TAIL_SKIP=0` to disable that approximation. The standing older-named
`strata-q20-gsq-01401-tailnet.json` also points to the new engine so existing
launch commands pick it up.

Full same-day v2.2 bench: 0.1.41 **11/11 at 871 s** after a documented guard
correction; 0.1.42 **10/11 at 815 s**, aggregate decode **37.0 → 43.8 tok/s**.
The bank-task miss passed on a fresh repeat with PCIe share pinned at 0.34.
There is insufficient repetition to call the miss a quality regression or to
claim quality parity. See the [full comparison and caveats](../benchmarks/README.md#strata-0141-vs-0142-2026-10-10).

Same 43,244-token prompt on the calibrated chat settings, one run per engine:
both recalled `violet-harbor-731`; decode **35.0 → 41.3 tok/s (+18%)**,
prefill **68.48 → 68.85 s (flat)**. Evidence:
[streaming probe](../benchmarks/results/strata-0142-streamed-probe-20261010.jsonl).
Short probes had two boots per engine in ABBA order, plus a tail-off control;
the control returned to the old speed range. One baseline sample coincided with
the hung Pi wrapper, so the full suite and streaming results are the cleaner
performance evidence.

The new automatic PCIe share adjustment did run on this native Q2_0 pack in
the bench (0.34 → 0.30); the chat's explicit 0.20 overrides it.
The established 16K bench launch config also points to v0.1.42; its historical
settings remain unchanged. The exact 0.1.41 reference is saved separately as
`strata-q20-gsq-0141-bench-reference.json`.

Rollback chat engine: restore
`strata-port/strata-q20-gsq-01401-tailnet.pre-0142.json` over the standing config.
The pinned 0.1.41 binary remains installed. To restore the original Python
server as well, switch the `strata-port` checkout back to branch `main`.
The server was stopped before the upgrade and is left stopped after local API
verification. The historical measurements below are retained as recorded.

**Status: 🧪 lab-tested (bench tier)** — the highest-scoring configuration ever
measured on this card (10/11 on AG-Bench v2.1), and the current 8–10/11 band row.

- Weights: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` Q2_0 tier — backbone
  37,623,740,192 B sha256 `69820c02…` + PLE shard 28,800,138,432 B sha256
  `316b46f3…` (both verified against HF).
- Engine: **stock upstream Strata** (github.com/Niko1221/Strata), pinned tag
  builds only — v0.1.38 (worktree `strata-0138`) and v0.1.39 (worktree
  `strata-0139`, the LAB STANDARD since 2026-10-04). Our only local commit on the
  clone touches docs + a compile-probe script, zero engine source.
- Pack: `packs/q2_0-gsq` via `tools/iq_pack.py --gguf SHARD1 --out packs/q2_0-gsq`
  (needs `STRATA_GGUF_PY=<llama.cpp>/gguf-py` and python-regex). MTP head: the
  repo's `mtp/rt` (built via mtp_fetch.py + mtp_pack.py + mtp_rt.py).
- Config (tracked verbatim): [recipes/strata-configs/strata-q20-gsq-0139.json](strata-configs/strata-q20-gsq-0139.json)
  (the v0.1.38-era one is kept beside it for A/B). Key engine args: `--pack
  packs/q2_0-gsq --native SHARD1 --ple-gguf SHARD2 --ple-io mmap --expert-profile
  data/expert-profile.bin --expert-cache auto --spec 4 --spec-min-p 0.5 --kv int8
  --prefill auto:16384 --mtp mtp/rt --max-context 16384`.

## Measured (2026-10-02 → 10-04, n=4 same-config runs, one engine variable at a time)

| Phase | Value |
|---|---|
| AG-Bench v2.1 | **band 8–10/11** (8, 9, 10, 8) — 10/11 = fleet record (only task5-TS failed) |
| Decode (v0.1.38/39) | **36–41 tok/s** (was 31–33 on the 0.1.33-era build) |
| MTP acceptance | 0.75–0.81 (was 0.66–0.72); suffix-draft windows 43/43, 63/63 in-bench |
| Suite wall | 23.6 min (0.1.38, 8/11) → 22.9 (0.1.39, 8/11) → **20.6 (0.1.40, 9/11 @ 1238s — fastest suite ever on this card)** |
| Context ladder | 16K config native; 128K measured (see the ctx-ladder evidence event) |
| Footprints | ~4.5 GB VRAM / ~34 GB DRAM-class (37.6 hot + PLE mmap) |
| v0.1.39 knobs | A/B-probed: ring/guard/nowait flat, decay≠0.7 and k8v4 WORSE — upstream defaults optimal |
| VRAM scavenge (headless 2533 era) | **Adopted `--vram-reserve-mib 500` for the 16K bench class (2026-10-06)**: synth prefill 420→620–702 t/s (+55–65%, two boots), real-text 540–740→732–838 t/s, decode flat. Falsified at 128K chat class: prompt chunk is pinned at 512 by design ("buffers fit in every expert cache"), r500/1024-chunk both flat; r300/r400 flagged LOW, r200 kills the MTP draft head (-6 MiB). Details: evidence `vram_scavenge_headless_ab` |
| KV streaming at 128K (2026-10-07) | **Adopted `--kv-resident 32768` for the chat config**: real 30K-token prefill 202→558–583 t/s (**~2.8×**), chunk 512→2048, slots 403→1389, ~1.7 GB RAM cost, outputs bit-identical. k8v4 variant measured +8–15% on top (615–656 t/s, two boots, needles pass) but not adopted (value rounding); q4_0 falsified (no gain over int8-streaming, keeps its perplexity tax); 64K-ctx falsified (dominated). Details: evidence `kv_streaming_128k_arms` |

## Reproduce

```bash
# engine (once): git worktree + CUDA build per the upstream tag, sm75
cp recipes/strata-configs/strata-q20-gsq-0139.json ~/Desktop/github/strata-port/
cd ~/Desktop/github/strata-port
python3 -m serve.server --engine strata --config strata-q20-gsq-0139.json --port 8080
bash $THIS_REPO/benchmarks/agentic-bench.sh strata-q20-gsq-125b 600
```

Evidence: [evidence/strata-q20-sm75-port.jsonl](../evidence/strata-q20-sm75-port.jsonl)
(18+ events: port, ctx ladder, KV types, spec sweeps, scored runs, engine
re-baselines, A/B probe sets) · baseline history: the llama.cpp-fork path in
[flashnext-gsqrc-q20-125b-llamacpp-fork.md](flashnext-gsqrc-q20-125b-llamacpp-fork.md)
(the pre-Strata record of the same weights).

## Storage

SSD: `~/models/flashnext-gsq-rco/` (66.4 GB pair + sha.txt); archive copies on
`/mnt/archive/local-models/`. The Coder's PLE shard is hardlink-deduped against
this copy (sha `316b46f` identical).
## v0.1.40 (2026-10-06): adopted

307 commits over 0.1.39 — the PR #783 series (A-K: batched verify-window K/V, multi-token
router + k=10 combine, drafter catch-up skipping rejected rows, sub-warp expert kernels,
fused per-head RMSNorm+RoPE in the verify window/drafter; sm_120-only defaults we inherit
as opt-in). Same-protocol bench: **9/11 @ 1238s** (prev 8/11 @ 1374/1413s), fails
{task2-React, task5-TS} (the model-scope fail pair, not task8 this time), decode windows
34.1-41.7, **acceptance 0.79-0.86** (prev 0.75-0.81), first probe run after boot reads
~13 tok/s cold (page-cache warmup artifact, bench unaffected). Configs:
`recipes/strata-configs/strata-q20-gsq-0140.json` (+ `-tailnet` variant for the
standing chat; the tailnet config's engine log field renamed to `chat-tailnet.log`,
which also fixes the bench/chat telemetry mixing from 2026-10-04).

### Full-suite verification after Turing tuning (2026-10-18)

Both stock and combined-optimized v0.1.45 returned 11/11 audited verifier passes
on Pi 1.3.0 with the same calibrated 128K settings and verified NVMe files.
Ten tasks excluding flagged task8 took 771 → 577 s, a 25.2% observed reduction
for one paired suite with different trajectories. Full 11-task time: 1,190 → 998 s.
Task8 already passes before agent work, and its optimized agent inspected stock
logs; it is excluded from the headline comparison. Repeated standard probes:
32K prefill 644.8 → 695.4 tok/s (+7.8%), short decode 42.9 → 47.1 tok/s (+9.8%).
These combined results include upstream SM75 options, not only our custom tile.
[Dashboard](../benchmarks/index.html) ·
[Full method and evidence](../experiments/strata-0145-agbench-20261018/README.md).
