# Swift-1.5-Qwen3.8-27B · GSQ-RCO IQ2_XS-mtp · llama.cpp — reasoning-efficiency finetune, quant-bound

**Status: 🔬 lab-verified** — UkisAI's Swift1.5 (−58.5% thinking tokens claimed, better
agentic behavior claimed) in the **only quant that fits this card**: the GSQ-RCO
IQ2_XS-mtp build (8.17 GB, embedded MTP head). Sibling of the already-validated
Swift Bonsai 2 entry; the 27B's other quants (IQ3_S-mtp 11.29 GB+) are out of the
8 GB envelope's reach.

- Weights: `ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF`
  `Swift-1.5-Qwen3.8-27B-GSQ-RCO-IQ2_XS-mtp.gguf` 8.17 GB · sha256 `4414bc39d93272af…`
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned upstream docker
- Config: `-c 8192 -np 1 -ngl 40 -b 256 -ub 128 -fa on -ctk q4_0 -ctv q4_0` +
  `--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-ngl all` (cram: 24 of 64
  layers on CPU — the IQ2_XS-on-CPU tax, established in the GSQ-RCO baseline)

## Measured (2026-09-25)

| Class | Decode | MTP acceptance (mean len) |
|---|---|---|
| Repetitive | 4.4 tok/s | 0.745 (2.49) |
| Novel prose | 4.3 tok/s | 0.665 (2.33) |

Acceptance beats the family's DT-IQ2_S embedded baseline (0.745 vs 0.68) — the
finetune drafts well. Decode sits in the known IQ2_XS-on-CPU class; the quant, not
the finetune, is the limiter on this card.

## AG-Bench: **3/6**

Pass: JS bugfix (239 s), date-fns upgrade (468 s), pagination (259 s). Fail at cap:
React contract, **python bugfix — unique to this model: every other 27B family member
passes it**, JS→TS migration.

Interesting signature: the efficiency finetune that keeps thinking short may cut
the deliberation the python task needs — the one AG-Bench datapoint where
"fewer thinking tokens" and "solves the task" diverge. n=1 run; treat as observed,
not proven.

Evidence: [evidence/swift15-27b-iq2xs-mtp.jsonl](../evidence/swift15-27b-iq2xs-mtp.jsonl),
[benchmarks/results/swift15-27b-iq2xs-mtp-20260925-095808.jsonl](../benchmarks/results/swift15-27b-iq2xs-mtp-20260925-095808.jsonl)

## Reproduce

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/swift15-27b:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Swift-1.5-Qwen3.8-27B-GSQ-RCO-IQ2_XS-mtp.gguf --alias local-model \
  --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 --n-gpu-layers 40 \
  --batch-size 256 --ubatch-size 128 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 --jinja --temperature 0 --seed 42 \
  --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-ngl all
```

## Verdict

On 8 GB, Swift1.5-27B is the IQ2_XS tax made visible: good drafting cannot offset
24 CPU layers at 4.4 tok/s, and the efficiency finetune costs it the python task.
For 27B-class agentic work on this card the standings are unchanged —
Bonsai-2 PTQ1_0 (59.3/49.9 tok/s full offload) dominates. Retry trigger: a
**Q2_K-class or sub-7 GB Swift quant** — the quant class, not the finetune, is the
blocker recorded here.

## Storage

SSD workbench copy at `~/models/swift15-27b/` while under test; rotates to the
archive per the storage rule when displaced.