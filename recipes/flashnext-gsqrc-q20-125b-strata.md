# Qwen3.8-Flash-Next GSQ-RCO Q2_0 125B · Strata engine — the fleet-record row

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