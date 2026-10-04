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

**COMPLETE 2026-10-01: all 8 Tier-1 items resolved** (1.1 negative-with-triggers:
120/120 clean strace'd hunt; 1.2 E4B d3 crown 93.3 p/h; 1.3 pinned baselines;
1.4 cache determinism rules; 1.5 lookup-prompt byte-exact + Bonsai 7/11;
1.6 A3B 9/11 tied fleet best; 1.7 mHC-on-SM75 works, official not adopted;
1.8 Flash-Next reasoning intact at 2.40 bpw). Verdicts inline below.

1. ✓ **RESOLVED 2026-10-01 (negative, triggers recorded) — pi zero-byte hunt.**
   The surgical run the prior session was stopped before making: 120 strace'd
   pi iterations + kernel-stack sampler against a live pinned MiMo serve —
   120/120 clean (~3.2 s/iter, healthy thinking-mode sessions throughout);
   the stall did NOT reproduce. Root cause remains unknown; caveats: bare-pi
   environment ≠ the AG-Bench scaffolding where all 3 strikes happened, and
   strace latency may mask a race. Operations covered by the harness
   zero-byte auto-retry (Tier 0.1). REOPEN if a bench ever double-strikes
   inside the auto-retry. Evidence `evidence/pi-hang-hunt-2026-10-01.jsonl`.
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

**Ledger 2026-10-02: 2.1 ✓ 2.2 ✓ 2.3 ✓(watch) 2.4 partial-open 2.5 ✓ 2.6 ✓
2.7 ✓ — the only engineering item left is 2.8 (fusion/kernel work).**
Verdicts inline below; evidence
`strata-q20-sm75-port.jsonl` + `bonsai-followups-t2-2026-10-01.jsonl`.

1. ✓ **2.1 RESOLVED 2026-10-02 — STRATA PORT LIVES, 22–24 tok/s.** Upstream
   landed their own Turing port (v0.1.32, 09-29/30) so our patch plan
   collapsed to build+parity+bench: 52/55 ctest (3 non-sm_75), pack via
   iq_pack, clean-lane decode 22.0/23.9 tok/s on Q2_0-GSQ-RCO vs
   llama.cpp's 7.9–8.3 — **~2.8×, fastest Flash-Next serve measured on
   this card, kill-gate (>15) passed**. Physics wall: the AVX-2 CPU expert
   pool (22.5 ms/token floor), not the port. Open: spec-4 warm pass,
   strata-server AG-Bench row.
2. ✓ **2.2 RESOLVED 2026-10-02 — keyed-Gumbel ON THE FORK (cf44169).**
   Byte-identical temp>0 replay across serve restarts on the byte-exact
   fork; zero regression at greedy; TensorFold's exactness program is 100%
   transferred to this card. Flag: `--keyed-gumbel`/request `keyed_gumbel`.
3. ✓ **2.3 checked 2026-10-01** — trigger untriggered (z-lab floor still
   Q4_K_M 1.14 GB); stays on the watch-list.
4. ◐ **2.4 PARTIAL (44c2d3e)** — `--recurrent-snapshots N` patched, built,
   non-regressive (canary byte-identical, cached accounting unchanged);
   **trigger-validation open**: the validation conversation reused an exact
   prefix so the snapshot path never fired; needs a true divergent-tail
   turn (agent-retry shape) to observe lcp/rollback/reused. VRAM law
   learned: rs cache = (1+N) state planes — 38.5 GB @rsn256/ctx8K, only
   small models or low-N fit 8 GB.
5. ✓ **2.5 RESOLVED 2026-10-01** — E4B mystery attributed (cached-path
   class 5/6, survey's 4/6) + the ANTI-PIN discovery: upstream-docker
   server `--temperature/--seed` flags DESTROY same-prompt reproducibility
   (0/6 vs 6/6 without); forks honor them. Protocol corrected in
   benchmarks/README determinism rules.
6. ✓ **2.6 RESOLVED 2026-10-02 (measured)** — Xing router-tie drift test:
   serial 6/6 self-repro, drafted 6/6 self-repro, drafted-vs-serial
   **6/6 mismatch** under the standard recipe — drift is real and total;
   both forks are pins-stable within-mode (unlike upstream serves).
   Router-tie isolation unseparated without a batch-invariant arm (open
   refinement).
7. ✓ **2.7 RESOLVED 2026-10-01 (nsys census)** — decode is GEMM/GDN-bound
   (63.6% PTQ tiles + 11.2% GDN, avg mmq 1.5 ms); the 2.8 fusion target
   quantified at **~9% small-kernel launch tax** (fwht 13k + quantize 13k +
   silu + rms_norm); one 31-ms H2D memcpy stall flagged.
8. **2.8 fusion + pass-tax — the remaining engineering item, now
   evidence-backed:** fuse the norm/quant/fwht chain and hunt the 31-ms
   H2D stall (census says ~9% ceiling; 2-column pass-tax ~10-15% on top);
   single kernel-surgery session queue when picked up.

## Tier 3 — backlog (run when lanes free up)

**Intake 2026-10-03 (wide scan — Reddit + GitHub + HF, 3-week window):**

- ✓ **Strata v0.1.38 bump + re-baseline — RESOLVED 2026-10-04**: built
  pinned v0.1.38 (worktree strata-0138, old binary kept for A/B),
  single-variable 11-task re-baseline: **8/11 (band 8–10 held), decode
  36–41 tok/s (was 31–33), MTP acceptance 0.75 (was 0.66–0.72)** — engine
  bump kept; new config `strata-q20-gsq-0138.json`. Evidence:
  evidence/strata-q20-sm75-port.jsonl (engine_0138_rebaseline).
- **v0.1.38 falsification probes** (official A/B switches, all cheap):
  STRATA_TOPK_CAPACITY_GUARD, STRATA_ADAPT_NOWAIT, `--adapt-decay` sweep,
  expert_profile_save warm-start, k8v4-vs-int8 at 16K/32K.
- ~~**FrogNano-4B-2609 Q4_K_M (2.8 GB)**~~ — PARKED by owner call 2026-10-04
  (no new small-model testing for now); unpark on request.
- ~~**Holo4-35B-A3B IQ2_XXS (10.8 GB)**~~ — PARKED by owner call 2026-10-04,
  same.
- **Ling-3.0-flash-VL IQ2_XXS (36.7 GB)** — 124B/A5.1B hybrid
  linear-attention record-row challenger in-pool; IQ1_S 28.1 GB doubles as
  a sub-2bpw reasoning-wall probe. No native MTP.
- **K2-Horizon-7B** — scores between Qwen3.6-27B and 35B-A3B on AA index;
  KV is 18 GiB/128K → quantized-KV mandatory; GGUF ready.
- ~~**jadidbourbaki lookup-drafting port**~~ — PARKED by owner call 2026-10-04
  (focus on Strata v0.1.39 for now). Recon report done + the five PR diffs
  fetched to /tmp/port/; note from recon: their PRs rework the ngram-cache
  drafter family, NOT our unique-span lookup-prompt matcher — the 165→1.18 µs
  numbers apply to the -lcs static-cache path. Resume on request.
- **sudoingX hybrid recurrent spec-rollback fix transplant** — spec
  decoding over DeltaNet-class was falling back to whole-KV restores
  (~15x drafter cost); not upstream yet; matches our
  recurrent-snapshots finding.
- **llama.cpp fork rebase (later session)** — onto post-#28549 base
  (CUDA graphs for MTP); cherry-pick spec-correctness #29638/#29019;
  expect churn from #29393 next to our Tier 2.8 fusion patch; upstream
  #27694 probabilistic drafting is the closest external cousin to our
  keyed-Gumbel work — worth an acceptance A/B after rebase.
- **2080 power-limit sweep (owner-side)** — 2080 Ti data: 95% speed at
  190 W, peak efficiency at 167 W; never benchmarked here.
- **External negatives to keep honest:** Bonsai −2 logit bias
  (44/50→43/50, Reddit-falsified 10-02); DFlash2 vs Flash-Next built-in
  MTP on 27B (built-in drafter won 5/10 quality tests, 10-02).

**Pre-existing Tier 3:**

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
| DFlash2 sidecar ≤600 MB (2026-10-03 recheck) | closest yet: rasyosef/gemma-4-E2B-it-dflash2 **646 MB** (safetensors, NOT GGUF) — over budget and unconvertible-off-the-shelf; Anbeeld Q2_K 705 MB; rasyosef Qwen3.5-2B 708 MB; MiMo quant-cliff data unchanged | a true ≤600 MB high-acceptance GGUF, or a lab-side safetensors→GGUF conversion of the 646 MB E2B head (first self-trigger candidate) |
| Aleph-Alpha Kolibri-1 (78.1B/A3.46B, 262K ctx, Apache-2.0, 2026-10-03) | FP8 weights only (~78 GB), no GGUF, no Strata pack support | any low-bpw GGUF or DASLab-class conversion lands in the 20-26 GB range; then it is a record-row aspirant (same 3.5B-active class as the 125B) |
| MiMo-V2.6-Flash-MOPD (309B/A15B, native 5-layer DFlash-style MTP, MIT) | all quants ≥3 bpw = 116 GB+, far over the 46 GB pool | a ~1.5 bpw learned quant (GSQ-RCO-class) appears; then a legitimate 125B-row challenger with a native drafter |
| Flash-Next usable tier | ~~65 GB IQ1_S doesn't fit; sub-2 bpw breaks the reasoning chain~~ **RESOLVED 2026-10-01 (half)**: the ≥2.2 bpw artifact EXISTS and reasoning is INTACT (GSQ-RCO Q2_0, recipe `recipes/flashnext-gsqrc-q20-125b-llamacpp-fork.md`) — only the MTP-head half stays open | a Flash-Next MTP head GGUF (~4 GB class) appears; then the agentic tier math is RAM + the 9 t/s novel-prefill wall |

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