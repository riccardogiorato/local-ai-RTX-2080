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
  data/expert-profile.bin --expert-cache al --spec 4 --spec-min-p 0.5 --kv int8
  --prefill auto:16384 --mtp mtp/rt --max-context 16384`.

## Measured (2026-10-02 → 10-04, n=4 same-config runs, one engine variable at a time)

| Phase | Value |
|---|---|
| AG-Bench v2.1 | **band 8–10/11** (8, 9, 10, 8) — 10/11 = fleet record (only task5-TS failed) |
| Decode (v0.1.38/39) | **36–41 tok/s** (was 31–33 on the 0.1.33-era build) |
| MTP acceptance | 0.75–0.81 (was 0.66–0.72); suffix-draft windows 43/43, 63/63 in-bench |
| Suite wall (8-pass runs) | 23.6 min (0.1.38) → 22.9 min (0.1.39) |
| Context ladder | 16K config native; 128K measured (see the ctx-ladder evidence event) |
| Footprints | ~4.5 GB VRAM / ~34 GB DRAM-class (37.6 hot + PLE mmap) |
| v0.1.39 knobs | A/B-probed: ring/guard/nowait flat, decay≠0.7 and k8v4 WORSE — upstream defaults optimal |

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