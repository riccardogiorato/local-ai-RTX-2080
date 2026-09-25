# Qwen3.5-35B-A3B · UD-Q3_K_M + MTP-ONLY head · experts-on-CPU — the first 35B on this card

**Status: 🔬 lab-verified** — the first MoE-with-offloaded-experts recipe on this 8 GB
Turing card, and the largest model (35B) ever measured here. Registry's 8 GB-class recipe
class, reproduced per the SpecPicks-style serving pattern with the hard-of-this-machine
caveat: their recipe assumes 28–32 GB system RAM; this box has 16 GB.

- Main: `unsloth/Qwen3.5-35B-A3B-MTP-GGUF` **UD-Q3_K_M 15.90 GB** · sha256 `c2d46cfa78edb540…`
  (verified)
- Drafter: `a4lg/Qwen3.5-35B-A3B-MTP-ONLY-GGUF` **Q4_K_M 1.51 GB** · sha256
  `14639932a007d1fa` — the extracted standalone MTP head
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned docker
- Architecture: hybrid attention (10 KV layers only) + 48 DeltaNet-like blocks; MoE with
  128 experts/layer, 8 active per token

## The recipe (the whole trick)

```
--override-tensor "exps=CPU"     # experts → system RAM (page cache), CPU-evaluated
--n-gpu-layers 999               # everything else (shared, attn, embeds, head) on GPU
--spec-type draft-mtp --spec-draft-model <MTP-ONLY head> --spec-draft-n-max 4
--ctx-size 8192  --cache-type-k/V q8_0  (KV tiny: hybrid attention keeps it 10-layer)
--threads 6
```

VRAM: **4.57 GB total** for a 35B. The remaining ~11 GB of weights stream from RAM via
mmap (`--load-mode none` recommended by the loader warning; not used this run).

## Measured (2026-09-25)

| Phase | Decode | MTP acceptance (mean len) |
|---|---|---|
| Steady repetitive | **9.29 tok/s** | 0.774 (4.09) |
| Steady novel | **8.52 tok/s** | 0.613 (3.44) |
| Deep agent turns (in-bench) | **1.51 tok/s, 661 ms/tok** | 0.736 (mean held) |
| Prefill effective | 3.65–6.47 tok/s (vs ~200 on the dense 9B) | — |

The acceptance pattern matches the Qwen3.5 family at every size — 0.6–0.8 at mean 3.4–4.1
on the standalone head. The family's drafting scales fine. **What doesn't scale is the
expert band on 16 GB RAM**: context growth + tool results make the paging path the
dominant term, and decode collapses 6× inside agent turns.

## AG-Bench: **3/6** at cap 900 s (raised from 480 for this decode class)

| Task | Result |
|---|---|
| js-bugfix | ✅ 819 s (14 calls) |
| date-fns upgrade | ✅ 864 s (36 calls) |
| python bugfix | ✅ 516 s (11 calls) |
| React contract | ❌ cap |
| TS migration | ❌ cap |
| pagination | ❌ cap — unique: every other passing model finishes it in 14–65 s |

## Capabilities

The riddle passes **only with thinking on** (264 s for one riddle): the same
E4B/Gemma-class reasoning profile. Tools clean. Thinking-off answer was actually wrong
("spends more time…" reclassified honestly after the harness's substring check was
fooled). Budgets ≥ 1500 required for thinking.

## Verdict

**First entry in the "35B class fits in 4.57 GB" club** — the recipe class is real and
llama.cpp executes it cleanly, KV/DSP overhead behaves, the MTP head works. But this
*specific machine* is the wrong host for it: at 16 GB RAM the expert band gates Decode
below every other 27B/35B in the ledger. **If this box grows RAM (32 GB+), this becomes
the smart-slot champion the same evening; as-is, ThinkingCap Q2_K holds the slot at
9.57 tok/s + 3/3 probes because its 10.86 GB is fully-in-RAM dense.**

Evidence: [evidence/qwen35-35b-a3b-mtp.jsonl](../evidence/qwen35-35b-a3b-mtp.jsonl),
[benchmarks/results/qwen35-35b-a3b-mtp-20260925-194626.jsonl](../benchmarks/results/qwen35-35b-a3b-mtp-20260925-194626.jsonl)

## Storage

Both files stay on SSD for now (the 17.4 GB pair is tonight's active experiment); rotates
per the storage rule when its slot is not current.

## Notes

- Loader warns mmap + tensor overrides recommend `--load-mode none` — parking that for a
  possible +few-% follow-up if the slot is revisited.
- `--threads 6` matches physical cores; oversubscription experiments (4/8) not tried.
- The 900 s cap reveals what the 480 s cap hides: this model class *can* complete
  agent tasks, just 13+ minutes at a time.