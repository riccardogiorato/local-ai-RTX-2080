# NEXT-IDEAS — the prioritized open-work backlog

Everything open across the lab's task threads, handoffs, and research notes,
merged into one ranked list. Restructured 2026-09-30 from the Strata,
TensorFold, TernaryBonsai2-leaderboard, MiMo-9B-DFlash, setup-advisory, 48GB,
Xing4, Splash, and Spark-X2.5 threads plus this file's previous backlog.
Tested models live in `recipes/` (with evidence); this file is only
unstarted work.

- being tested → see [README queue](README.md#test-queue)
- already tested → see [recipes/](recipes/) and the [AG-Bench leaderboard](benchmarks/README.md)
- resolved → moved to the [Archive](#archive--resolved-verdicts) with evidence pointers

Tier order = value/effort, top item first. When an item resolves, check it off
with the date and a pointer, then compress it into the Archive on the next
restructure.

## Tier 0 — record fixes & housekeeping (minutes, no GPU)

**ALL RESOLVED 2026-10-01** — findings, including two where the item itself
turned out stale:

1. ✓ **Zero-byte auto-retry shipped in `agentic-bench.sh`** — each task
   retries once on an empty `pi-session.jsonl` (the ~1/75 pre-header startup
   stall; root-cause hunt stays open in Tier 1), rows carry a
   `zero_byte_retry` flag, ceilings unchanged.
2. ✓ **`notes/mlxfast-bonsai2-portability.md` amended** — ranked plan
   reordered to (1) prompt-span lookup, (2) drafter class, (3) split-K
   patch parked behind it, (4) fusion/census; item-1 table verdict now
   records the 2026-09-28 falsification (acceptance 0.845→0.540 by d4,
   d4 slower) instead of "biggest lever".
3. ✓ **`hardware.md` was already correct** — the 48 GB line (with the
   XMP-failed-at-2400 retrain note) landed with a sibling commit before
   this checklist ran; no change needed.
4. ✓ **Results-ledger reconciliation in `benchmarks/README.md`** — with a
   correction to the claim that prompted it: `qwen35-35b-a3b-mtp` was NOT
   an interrupted partial, it is the complete 3/6 "a3b first run (16GB
   era)" retro-v2 row (walls sum 4899 s = 81.7 min) — the note now breaks
   that label-swap trap. `qwen25-coder-7b-q4km-20260925` stays INVALID
   with no leaderboard row (all 6 tasks dead in 1–43 s, 0 tool calls —
   the pre-/slots-gate 503 window, not a model measurement;
   Qwen2.5-Coder-7B has genuinely never been benched here).
5. ✓ **Idle-serve sweep** — no llama processes on the box; GPU at 556 MiB
   (desktop only). The 7 GB hold from 2026-09-25 is long gone.
6. ✓ **CPU governor "powersave" — resolved as a NON-ISSUE** — measured
   rather than blindly changed: this is intel_pstate active+HWP, where the
   real knob is EPP = `performance` (set), power-profiles-daemon profile =
   `performance` (active), and cores boost to ~4.5 GHz under the bench
   load class. The governor string is cosmetic under HWP; forcing
   `scaling_governor=performance` would change nothing and would fight
   power-profiles-daemon. The setup advisory's flag is retired.
7. ✓ ~~Stale "Strata Q2_0 tier needs sm_80+" lines~~ resolved 2026-09-30 by
   the restructure (soft-gate survey preserved verbatim in the Archive).
8. ✓ ~~DFlash2 falsification caveat~~ resolved 2026-09-30 by the
   restructure — the 1.14 GB Q4_K_M-swa drafter was tested, the ~600 MB
   class itself was not; the caveat travels inside the Tier 2 sidecar
   entry (and the original evidence file's numbers stand as measured).

## Tier 1 — measurements (hours, high value/effort)

**Progress 2026-10-01: items 2, 3, 4, 5 RESOLVED** (verdicts below);
1.6 running, 1.7 awaiting download, 1.8 downloads chained, 1.1 staged to
run when the GPU lane frees.

1. **Pi zero-byte hang — catch with evidence.** Struck 3× in MiMo benches;
   narrowed to a pre-header startup stall, ~1/75 manual rate, serve-state
   correlation excluded, 150–210 clean no-serve iterations. The v2 hunt
   (120 iterations, full syscall trace against a live MiMo serve) was
   stopped by user request before catching one. Harness now auto-retries
   zero-byte tasks (Tier 0.1) but the ROOT CAUSE is still unknown.
   STAGED: /tmp/pi-hang-hunt.sh (strace + kernel-stack sampler, 120 iters
   against a live MiMo serve). Run when the GPU lane frees. (MiMo thread.)
2. ✓ **RESOLVED 2026-10-01 — d3 CROWNS E4B.** Depth sweep: code-class
   acceptance RISES at d3 (0.818/mean 3.55, +25% decode), novel peaks at
   d1; v2.1 bench: d3 7/11 @ 270 s vs d2 @ 302 s, identical pass set —
   NEW card efficiency record 93.3 pass/h. E4B serve depth is now 3.
   Recipe updated. Evidence `evidence/gemma4-e4b-mtp-depth.jsonl`.
3. ✓ **RESOLVED 2026-10-01 — pinned baselines recorded.** 5-task
   drift-stamped task matrix + fresh Bonsai pinned hard reference in
   benchmarks/README ("Drift-pinned 5-task baseline"). Side finding:
   pinning itself flips Bonsai outcomes (task11→fail, task7→fail,
   task8→pass) — pinned runs are their own baseline rows.
4. ✓ **RESOLVED 2026-10-01 — cache determinism rules.** Turn-extension
   cache reuse is bit-identical (agent-loop noise CLEARED); ubatch
   128/512/2048 bit-neutral; cache_prompt=true vs false deterministically
   perturbs identical-prompt bytes — pin it for same-prompt comparisons.
   Determinism-rules section in benchmarks/README. Evidence
   `evidence/promptcache-ubatch-drift.jsonl`.
5. ✓ **RESOLVED 2026-10-01 — lookup-prompt IMPLEMENTED + VALIDATED.**
   Fork branch `prompt-span-lookup` @aacb5ba: byte-exact vs serial (6/6)
   at envelope-safe n_max 3, zero idle cost, task7 flip + task8 3× in the
   pinned 5-task A/B; full pinned 11-task run: **Bonsai-8K 5/11 → 7/11
   (6-7 band) @ 582 s, 43.4 pass/h**. Evidence
   `evidence/bonsai2-lookup-prompt.jsonl`. Leaderboard row updated.
   Follow-up now lives in Tier 2/3 (wider-than-4 lookup windows need the
   MMQ ≥5-col invariance patch first).
6. **35B-A3B re-bench on 48 GB, verbatim recipe** — the "smart-slot
   champion, agent turns hold ~7–9 tok/s" claim (deep-agent collapse
   9.3/8.5 → 1.51 tok/s at 16 GB) is unmeasured since the RAM landed.
   Same session: one `--cache-ram 32768` run to quantify the prompt-cache
   effect. RUNNING (2026-10-01, labels a3b-iq2xxs-v2-rebaseline /
   -cram32). (48GB thread.)
7. **Xing4 build + bench on the fork with the official IQ4_NL ladder** —
   48 GB now hosts the whole ladder (IQ4_NL 20.1 / Q6_K 23.9 / Q8_0
   30.9 GB; Q8 MMLU-Δ only -3.1). The mHC (4-channel hyper-connections)
   CUDA path on SM75 has never been benchmarked on any pre-Ampere card.
   Caveat: Chinese-centric model, interpret AG-Bench accordingly. Probe
   tier same as the Qwen3.5 campaign. OFFICIAL IQ4_NL downloading —
   staged script `/tmp/xing4-official-bench.sh`. (Xing4 thread.)
8. **Strata Q2_0-GSQ-RCO quant test on our patched llama.cpp** — RESOLVED
   AS TESTABLE by research: ISTA-DASLab GSQ-RCO Q2_0 is a standard GGUF
   (2.40 bpw backbone, 37.6 GB hot + 28.8 GB mmap PLE shard), loads
   unchanged on the qwen4exp runtime; no MTP heads in the repo and a
   community quality-degradation report temper expectations. Shards
   downloading (chained); staged script `/tmp/strata-gsqrc-test.sh`.
   (Strata thread.)

## Tier 2 — engineering (sessions)

1. **Strata sm_75 port — the big one.** 3 phases: (1) CMake guard patch +
   f16-MMA twin for the single hard sm_80 instr (`mma.sync.m16n8k8.tf32`
   in `src/kernels/cuda/native_qsa_score.cu`, ~30 lines; its ldmatrix
   loads ARE sm_75-legal) + parity suite on the 2080; (2) Q2_0 bench
   (37.6 GB model + 29 GB PLE on the 110 GB free disk — fits; our 46 GiB
   RAM qualifies only for the Q2_0 tier) — **KILL if ≤15 tok/s**
   (llama.cpp parity); (3) bf16→fp16 conversion for the ~10 bf16-hot
   kernels (ple, gr, fused_gr, elementwise, bf16_gemv, shared_expert…) if
   the fp32-round-trip emulation shows, + expert-cache tuning for 8 GB
   (~2800 vs their ~5600 resident). Physics cap ~1/3 of the 5070
   numbers: ~20 tok/s @128K / ~30 short-chat / ~180 pp — still 2–4× the
   UltraLite llama.cpp expectation. **Run before any Ampere purchase.**
   Full survey preserved in the Archive. (Strata thread.)
2. **Keyed-Gumbel sampler port into the Bonsai fork** (flagship — full
   byte-exactness at temp > 0). Module done and validated
   (`notes/keyed_gumbel_sampler.h`, 16/16 test classes; cross-restart
   replay 2/2; stock 2/2 → keyed 1/2, residual = logits-bits). Remaining:
   llama.cpp splice per
   `notes/keyed-gumbel-llamacpp-integration.md`, server-schema wiring,
   patched build, repro/drift rerun (~half session). ⚠️ the previous
   patched tree lived at `/tmp/llama-upstream-keyed` (tmpfs — gone on
   reboot); rebuild from the notes, not /tmp. (TensorFold + MiMo.)
3. **DFlash2 ≤600 MB Q2-class sidecar beside a full-offload IQ1_S
   target** (6.70 + 0.6 + ctx_other ~0.4 ≈ 8.0 GB with desktop —
   borderline; needs `-c 4096`, possibly one shed layer). CAVEAT
   (2026-09-28 falsification): the 1.14 GB Q4_K_M-swa drafter forced ngl
   44 and collapsed decode 19.7 → 6.2 tok/s *despite* 0.92/mean 3.76
   acceptance; the ~600 MB class itself was never tested, and ngl-54 OOM
   math suggests even it may not fit — this stays OPEN as a measurement,
   not a closed verdict. Watch jmarceno/z-lab for a Q2_K_XS-swa
   conversion. Same sidecar class on ThinkingCap-27B Q2_K (9.57 tok/s,
   acc 0.995) also untested. Evidence `evidence/dflash2-iqi-27b.jsonl`.
   (Splash + Strata + MiMo threads.)
4. **Recurrent-state snapshots for DeltaNet-class hybrids** — design doc
   done (`notes/design-recurrent-state-snapshots.md`), implementation
   never committed. Explicit SSM/conv/target_feat snapshots (direct
   `lcp=N reused=N`) instead of KV seq-id manipulation for
   Qwen3.5/3.8-hybrid multi-turn. Pure C++/GGML, no GPU needed to draft;
   b11118 docker or the bonsai2 fork as hosts. Payoff = per-turn latency
   on hybrid chains. (setup advisory / David19p research,
   `notes/research-david19p-turing-kernel.md`.)
5. **E4B self-repro mystery** — the only model whose drafted fast mode
   can't reproduce itself (serial 6/6, drafted 4/6, drafted-vs-serial
   1/6 byte-identical; 150 vs 91 tok/s is what the drift buys).
   Attribution rerun with flags toggled / flash-attn off. (TensorFold.)
6. **Xing4 router-tie drift test** — weights on the archive drive;
   acceptance 0.91 recorded but the drift column never measured.
   (TensorFold.)
7. **nsys copy/launch census of Bonsai verify rounds** — ~1 h profiling,
   never run. Tile-path floor is 55 ms vs ~22 ms ideal single-pass;
   register-weight/plane-copy layout only if a lane kernel is reopened
   (blocked on the drafter class, see Tier 3). (TernaryBonsai.)
8. **2-column pass-tax kernel patch** (1.34×→1.0 row-boundary tax, worth
   ~10–15% serve) + fused norm/quant launches on the decode path. The
   remaining pure-speed fusion items. (TensorFold + TernaryBonsai.)

## Tier 3 — backlog (run when lanes free up)

- **ThinkingCap 32K KV-in-RAM AG-Bench** — one bench; could flip the
  family's two failures. (Splash advisory.)
- **llama-bench pp/tg rows** for the serve recipes — makes our numbers
  internet-comparable. (Splash advisory.)
- **Swift-1.5 acceptance at Q2_K/Q4_K** on the same model (now 4.4 tok/s
  at 0.745) — half a day. (Splash advisory.)
- **Spark-X2.5-4B (XHToken) serve** — never tried; distinct from
  LiquidAI's DSpark drafter. (Spark thread.)
- **MiMo 32K pinned serial re-baseline** — separates pin-vs-ctx for the
  morning 9/11 headline; mid-value, only if ranking finality is needed.
  (MiMo thread.) Reopens the 32K+drafter door only if a ≤400 MB
  high-acceptance z-lab drafter (Q1/IQ2_KS lineage) appears.
- **Accuracy-coverage deepening for the Bonsai fork** — sweep the drift
  harness across every declared depth (d1–d8) and both prompt files; add
  a shape-complete load-time bitwise kernel self-test with stock fallback
  (the contest's pattern). (TernaryBonsai.)
- **Pre-commit the escape-hatch strictness rule** — for unpinned split-K
  tuning: relax serial-equal to batch-invariant only if ≥X% speed win,
  AG-Bench unchanged, drift harness compares drafted vs drafted-baseline.
  (TernaryBonsai.)
- **GLM-OCR real-photo GT regression set** — the KFC/CIAO GT sets did
  not survive the migration; recipes run on synthetic images. New
  photographed receipt/label GT set (regression-grade, human-verifiable).
- **Tweet + PR the winning recipes to 0sero/local-ai-registry** —
  promised in the Spark-X2.5 thread.
- **Higher-acceptance drafter class for Bonsai** — a smaller DFlash2 or
  any better head is the only path back to depth gains (d4–d8 dead with
  the current grafted head: acceptance decays ~0.13/depth and d4 is
  slower *and* drifts). Effectively watch-list grade. (TernaryBonsai.)

## Watch-list — blocked, passive triggers (no action until one fires)

| Family | Blocked by | Reopens when |
|---|---|---|
| OrcaSAQ-2-27B (exl3 v1.5.1, QTIP-class) | exllamav3 requires sm_80+ (ptxas-confirmed), no CPU dequant, no public exl3→GGUF converter (castkit's exl3 backend needs Ampere+) | orcarouter ships GGUF; a community converter appears; an Ampere+ box dequants once to fp16. Same base IS tested here via IQ2_S / ThinkingCap Q2_K / Bonsai-2 |
| trymirai Qwen3.8-27B-S ("27B in 8.45 GB at 60 tok/s on a 3090") | uzu runtime Apple-silicon-only; vLLM `mirai_s` plugin needs CC 8.0+ (and vLLM has no Turing); QTIP/trellis codec → conversion destroys the size point; 8.45 GB > 8 GB VRAM anyway | trymirai ships a GGUF/llama.cpp path or Turing kernels (unlikely by design); Ampere+ dequant. Our dense 27B rows already record the experience |
| fafastmobel / Cinference (23.8 GB NVFP4/FP8, embedded MTP + DFlash2) | sm_120a-only kernels; NVFP4/FP8 Ada-native; custom NInfer format, no GGUF route | Turing kernel build / sub-8 GB class / one-shot Ampere+ dequant. Design leads (verify trees, prompt lookup, in-file DFlash2) already on the David19p watch-list |
| Diffusion Gemma 26B-A4B | no GGUF, vLLM no SM75, exceeds 8 GB even at extreme bpw | Google ships an E2B/E4B-class diffusion variant or a GGUF appears |
| PQ2_0-MTP tier (2.13 bpw, 7.66 GB + trained head; 86/98/75 tok/s on an 11 GB Pascal) | can't go resident with useful context on 8 GB — measured 2.2 tok/s at ngl 46 partial, ngl 60 OOMs at load; trained head proven compatible (0.717/0.585 acceptance via their PQ2_0-MTP file) | an 11 GB+ card lands here (the giveaway 1080 Ti is exactly that); a sub-8 GB PQ2_0 derivative appears |
| MiMo 32K + drafter | no ≤400 MB drafter exists (HF floor = Q2_K 482 MB); drafted arm 0.85× slower (see Archive) | z-lab Q1/IQ2_KS lineage, or a fork with slimmer draft-pp buffer |
| Flash-Next usable tier | 65 GB IQ1_S doesn't fit; sub-2 bpw breaks the reasoning chain (EOS-at-reasoning-close) | a sub-40 GB ≥2.2 bpw artifact with MTP + intact reasoning — Tier 1.8 now tests whether Q2_0-GSQ-RCO is it |

**Standing note:** an Ampere+ GPU landing in this lab remains the single
biggest unlock — native bf16/tf32, the PQ2_0 tier, exl3, and the DFlash2
windows all open at a stroke. The Strata port (Tier 2.1) is the last big
thing to try *before* buying one.

## Archive — resolved verdicts

- **Flash-Next UltraLite 37GiB (0xKitkat, 1.80 bpw) — boundary record
  2026-09-27.** Served on patched qwen4exp @ 250b61446: 12.5 tok/s, 218–233
  tok/s pp, first 125B-class on the card. Boundary learned: sub-2 bpw
  BREAKS THE REASONING CHAIN (EOS-at-reasoning-close; same wall as IQ1_S).
  Recipe `recipes/flashnext-ultralite-125b-llamacpp-fork.md`, evidence
  `evidence/flashnext-ultralite-125b.jsonl`. Our own Flash-Next expectation
  class: honest 5–15 tok/s at best.
- **UBBoost cherry-pick — superseded 2026-09-26 via c9df0ee.** Claim
  (llama.cpp PR #23239, RTX 2080 + 35B-A3B + MTP) reproduced 2.4× with
  plain ubatch on all 3 CPU-offload models; port not needed. Kept as the
  dense-cram cold-prefill profile reference. Our Bonsai is GEMM-saturated
  at ~29% of the int8 ceiling — the lever only mattered for the CPU-band
  models (Xing 346 tok/s pp, A3B).
- **token_embd=q4_0 requantize trick — no-op on our artifacts 2026-09-27.**
  net_termina's ~4% trims the OFFICIAL ggml-org F16-embedding GGUFs; our
  unsloth UD-Q4_K_XL conversions already ship q4 embeddings (byte-identical
  requantize output). E4B re-measure unnecessary (181 tok/s row already
  includes the effect); Gemma-12B promotion stays blocked on the ngl-45
  layer floor, not embedding VRAM.
- **MiMo-9B + DFlash sidecar — VALIDATED 2026-09-28.** z-lab
  Qwen3.5-9B-DFlash Q4_K_M (766 MB) drafts at 0.794 / mean 7.31 →
  56.7 → 134.6–138.3 tok/s code (2.4×, 8K) beside a FULLY-RESIDENT target
  — first spec pair on this card with both models resident. 16K pinned
  pair AG-Bench: serial 7/11 @998 s vs drafted 7/11 @601 s — per-task
  IDENTICAL, 1.66× wall, 25.3 → 41.9 pass/h. **32K + drafter =
  net-negative for agents** (7/11 @739 s vs 8/11 @872 s; think-heavy
  acceptance collapse + drift-inflated tool-call counts, task8 77→151).
  **Fork-exactness for this pair FALSIFIED** (drift 0/6 at n_max 8 and 2,
  inside the fork's 4-col envelope — Bonsai 6/6 exactness is specific to
  the MTP/PTQ1_0 kernel profile; parity needs real kernel work; measured
  capability cost of drift so far 0 to +1). New findings: draft-side is a
  steep nonmonotonic quant cliff (Q4 0.794 / Q2 0.442 / Q3 0.294 — requant
  from BF16, never the Q4); q4_0 KV is code-neutral but perturbs novel-class
  trajectories; ONE main CPU layer collapses novel decode; MiMo warm-up
  gate derails are stochastic always-thinking under no-params requests →
  harness WARM_BYPASS=1; **thinking-off falsified as a fix (6/11, tool
  thrash)**. Recommended profiles: 16K+Q2_K (agents, capability-neutral),
  8K+Q4_K_M (speed). Evidence `evidence/mimo-9b-dflash-drafter.jsonl`.
- **DFlash2-sidecar economics on 8 GB — falsified at 1.14 GB, open at
  ~600 MB** (measurement preserved as Tier 2.3). Acceptance itself
  validated: 0.92/mean 3.76 on the head-less IQ1_S target; the sidecar
  class is quant-agnostic and works on this card (Supsurface
  prism-dflash2 runtime built and ran first try). Evidence
  `evidence/dflash2-iqi-27b.jsonl`.
- **TensorFold queue-opener 2026-09-27/28 — three of four done.**
  (1) Drift survey DONE: every upstream-docker MTP recipe drifts
  (qwen35-4b 3/6, qwen35-9b 1/6, g12b 2/6), while Bonsai fork +
  `GGML_CUDA_BATCH_INVARIANT=1` is 6/6 drafted==serial at zero cost
  (59.2/43.0 tok/s; env unset drops to 2/6) — the 59 tok/s row reads
  "byte-exact serve" retroactively. (2) keyed-Gumbel module DONE+validated,
  splice remains (Tier 2.2). (3) Fork audit DONE; deployment rule active:
  Bonsai draft depth ≤3 (d1–d3 6/6; d4 drifts 4/6 AND is slower — 45.7 vs
  58.1 tok/s — acceptance decays 0.845/0.726/0.588/0.540, so the MMQ
  ≥5-col invariance patch is PARKED, payoff-free at this acceptance
  profile). Ground probes: fp16-HMMA wmma lanes are slot-dependent on
  sm_75 (dead end for exactness); dp4a/IMMA integer lanes exact (0/1M
  mismatches); crossover economics favorable (rows_free ≈ 24–48 ideal at
  425 GB/s; tile floor flat through n=8). Harness
  `notes/spec-drift-test-llamacpp.sh` is a standard column for every
  spec-decode recipe. Notes `notes/tensorfold-analysis.md`, evidence
  `evidence/tensorfold-exactness-probe.jsonl`.
- **Strata source survey 2026-09-27 — sm_80 gate is SOFT, port feasible.**
  Engine: Qwen3.8-Flash-Next on single consumer GPU (65 tok/s @128K / 95
  short-chat / 539 pp with Q2_0-GSQ-RCO on a 5070 12 GB + 64 GB DDR5-5600;
  OpenAI+Anthropic endpoints; PLE n-gram table on SSD). Survey (shallow
  clone, later discarded): single hard sm_80 instr in the whole tree (tf32
  `mma.sync.m16n8k8` in `native_qsa_score.cu`, 151 lines, attention
  scorer only; ldmatrix IS sm_75-legal); f16 twin runs on Turing tensor
  cores (~30-line patch). bf16 VERIFIED on this box — CUDA 13.3 cudart
  software-emulates on sm_75 via fp32 round-trips (compiled + correct on
  the 2080). No cp.async, no redux.sync, no accessPolicyWindow; expert GEMV
  hot path llama.cpp-derived fp16 (sm_75-native). CMake gate a plain
  version check. Parity tests with oracle vectors for ~every kernel. Desk
  research feeding the port = Tier 2.1.
- **Bonsai2 MLX.fast leaderboard analysis 2026-09-27.** Yukon contest:
  record 505.4% / 580 decode / 1901 prefill tok/s (winglock); top-8 all
  stock DFlash at 14.2 tok/round. Every row is a PR write-up in
  `Layr-Labs/mlxfast-bonsai2-27b-engine`. The contest model IS our
  served model; davidtai's M=13 qmv→qmm crossover ≡ our cap=4 IMMA-MMQ
  crossover. Their strictness pattern (load-time bitwise self-tests,
  stock fallback) validated our 6/6 bar but our coverage is thin (6
  prompts × 2 repeats) → Tier 3 deepening. Notes
  `notes/mlxfast-bonsai2-portability.md` (commits eeab971, b5d29c0,
  664fe75).
- **A3B pack A/B — RESOLVED 2026-09-30** (lane-coordinated with sibling
  local-ai-rtx2080-05). Speed tier recorded 2026-09-28; the then-missing
  IQ3_XXS quality tier ran after a Twitter tip: 7/11 with task4 re-judged
  PASS (7–8 band) vs IQ2_XXS 8/11, at −15% decode / −10% prefill /
  +2.5 GB — zero of IQ2's three failing tasks rescued, tip falsified,
  **IQ2_XXS stays recommended**. Write-up in the recipe's "IQ3_XXS quality
  tier" section, evidence `evidence/qwen35-35b-a3b-iq3xxs.jsonl`. The
  measure harness now tolerates metrics-less foreign servers.
- **Gemma-E4B v2.1 — 7/11 @ 302 s, 83.4 pass/h** (card efficiency record,
  40e2c45). MiMo 9/11 headline survives as an 8–9 band (8/11 at 64K;
  greedy pinning costs task11, 1de77db-era). Fork-exactness for DFlash
  falsified (d91d553).