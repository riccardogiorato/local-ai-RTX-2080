# Xing4.0-29B-A4B · DYN-DIQ4XS 3.31 BPW · shuxiaoqiong xing4_0-port fork — the 4 GB 29B

**Status: 🔬 lab-verified** — the second 30B-class model ever run on this card (after
Qwen3.5-35B-A3B), and a **new VRAM-per-billion record: 4.0 GB for a 29B**. China
Telecom/TeleAI's agentic MoE with MLA and mHC hyper-connections, served with the
same experts-on-CPU recipe class as the A3B.

- Weights: `jmarceno/Xing4.0-29B-A4B-GGUF` @ `6d745c62` —
  `Xing4.0-29B-A4B-DYN-DIQ4XS-GU2XXS-Q8_0.gguf` 12.04 GiB (3.31 BPW), sha256
  `d33dd4172959af2f…` (verified). Dynamic quant: expert gate/up IQ2_XXS, down IQ4_XS +
  published imatrix (WikiText-2 + source + zh-wiki, 820 chunks), token-emb Q8_0,
  output Q6_K, nextn head IQ4_NL — exact recipe published in-repo
- Base: `XingChen-AGI/Xing4.0-29B-A4B` (Apache-2.0): 29B/A4B, top-4 of 64 routed
  experts + 1 shared, **MLA** (q_lora 768 / kv_lora 512 → near-zero KV), mHC
  4-channel hyper-connections, 40 layers, embedded MTP head (blk.40.nextn),
  256K native ctx (YARN → 512K), Chinese-centric reasoning, OpenCode/Claude-Code-adapted
- Runtime: **fork-only** — `shuxiaoqiong/llama.cpp` branch `xing4_0-port` @
  `63c16fb…` (upstream PR #29012; new GGML ops `XING4_0_HC_{PRE,COMB,POST}`).
  Built host-side with `CMAKE_CUDA_ARCHITECTURES=75` — **builds and runs on SM75
  first try**, no SM80+ dependency found. (`jmarceno/llama.cpp-xing4` exists as an
  alternative fork with CUDA MLA-KV-in-FlashAttention changes; not needed this run.)

## The recipe

```bash
systemd-run --user --scope -p MemoryMax=12G \
  build/bin/llama-server \
  --model Xing4.0-29B-A4B-DYN-DIQ4XS-GU2XXS-Q8_0.gguf --alias local-model \
  --host 0.0.0.0 --port 8080 -c 8192 -np 1 -ngl 999 \
  --override-tensor "exps=CPU" --threads 6 --jinja \
  --spec-type draft-mtp --spec-draft-n-max 2 --metrics
```

Same class as `qwen35-35b-a3b-cpuexperts`: experts → system RAM, everything else
(shared layers, MLA attention, embeds, head) resident. The cgroup guard is the
freeze lesson — never serve >12 GB models on this box without it.

## Measured (2026-09-26)

| Phase | Decode | MTP acceptance (mean len) |
|---|---|---|
| Repetitive | **6.79–6.95 tok/s** | 0.91–0.93 (2.84–2.88) |
| Novel prose | **5.36–6.26 tok/s** | 0.72 (2.44–2.46) |
| Prefill (code class) | **346–348 tok/s** — 12× the A3B (MLA's tiny KV band) | — |

## Capabilities — 4/4, and the interesting one

| Probe | Result |
|---|---|
| Trains riddle, thinking ON (budget 1500) | ✅ 95.8 s, 1240 reasoning chars (in Chinese) |
| **Trains riddle, thinking OFF** | ✅ **19.6 s — joins ThinkingCap + Bonsai-2 as the only thinking-off reasoners on the ledger, and the cheapest one** |
| Coding (exec-verified) | ✅ 6.4 s |
| Tools (get_weather) | ✅ 4.3 s, correct call |

Budget trap: ≤64-token chats return empty content (thinking eats it) — the
E4B/A3B budget class.

## AG-Bench: **3/6** at cap 900 s

| Task | Result | Style |
|---|---|---|
| js-bugfix | ✅ 349 s / 30 calls | methodical |
| React contract | ❌ 627 s / 4 calls | **fast-exit** — flails and stops, not cap-ground |
| date-fns upgrade | ✅ **46 s** / 23 calls | fastest dep-upgrade pass on this ledger below 50 tok/s decode |
| python bugfix | ✅ 82 s / 11 calls | surgical |
| TS migration | ❌ 275 s / 8 calls | fast-exit |
| pagination | ❌ 223 s / 18 calls | fast-exit (the A3B ground this to the cap; Xing quits early) |

Same fail set as the A3B-class (React/TS/pagination) but opposite failure style:
the A3B *grinds* into the 900 s cap; Xing *declares early*. Passes are 2–17×
faster than the A3B's (the MLA prefill advantage made real). Score ties
Gemma-12B / the Qwen3.5-35B-A3B at 3/6.

## Storage

On SSD while active; rotates per the storage rule once benched.

Evidence: [evidence/xing4-29b-a4b-mtp.jsonl](../evidence/xing4-29b-a4b-mtp.jsonl)