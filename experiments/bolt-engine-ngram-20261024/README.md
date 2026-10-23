# Bolt engine and ngram follow-up — 2026-10-24

Scope: update the engine and test ngram drafting for prose. Main weights remain
Unsloth UD-Q4_K_XL and the drafter remains Q8_0. The owner explicitly excluded
an AtomicChat AD-Q4_K_M weight swap; it was not attempted.

## Engine selection

The GitHub releases API returned b11840 as the latest release. The GHCR registry
had no `server-cuda12-b11840`, `server-cuda-b11840`, or
`server-cuda12-b11808` image. Paginating the registry's tag list identified
b11804 as the newest published CUDA 12 server image. Both `server-cuda` and
`server-cuda12-b11804` resolved to the following digest at test time:

```
ghcr.io/ggml-org/llama.cpp:server-cuda12-b11804@sha256:490d8cd8000203a3ab8fdfce14ef931e2aa85affd4dd4447bcc75f299f00fd9a
```

The binary reports build 11804, commit `c7fc50941`; image labels record full
revision `c7fc5094179bf8a9c73c18593db714f8da41a402`. Prior engine: b11118,
digest `bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3`.

Sources: [release catalog](https://api.github.com/repos/ggml-org/llama.cpp/releases),
[pinned speculative implementation](https://github.com/ggml-org/llama.cpp/blob/b11804/common/speculative.cpp).
The implementation gives ngram methods priority, falling back to the model
speculator when no ngram draft is available; ordering names on the CLI does not
change that priority.

## Method

`measure.py` saves complete request prompts, completion responses, timing fields,
metrics deltas, output hashes, and wall times. Every prompt gets one excluded
warmup and two retained measurements; temperature 0, seed 42, cache_prompt false,
only the temperature sampler. No best-of selection. Configurations run serially
on the same GPU, 8192 context, fp16 KV, DFlash depth 4.

The historical fixed code prompt and short prose prompt use a 256-token cap.
Short prose naturally stops around 48–49 tokens; the added essay prompt uses a
512-token cap to provide a longer prose sample. These are workload probes,
not a broad prose corpus. Old-engine long-prose output varies across greedy
runs; cross-engine prose text also differs. Code output hashes permit a stronger
same-output comparison. Raw `.jsonl` files include warmups marked explicitly.

The ngram configurations use match length 4 and draft length 8, separately for
`ngram-simple` and `ngram-map-k`, each stacked with DFlash d4. These short lookup
lengths intentionally give ordinary prose opportunities to match. This does not
exhaust all ngram algorithms or parameter settings. `campaign.sh` records each
configuration and restores b11118 at 64K on exit, including failure.

## Measured comparison (two measured runs per cell, tok/s)

| Engine / speculation | Code | Short prose | 512-token prose |
|---|---:|---:|---:|
| b11118 / d4 | 158.06–159.12 | 75.80–76.29 | 78.15–79.68 |
| b11804 / d4 | 189.72–190.70 | 87.93–88.06 | 85.79–85.92 |
| b11804 / ngram-simple + d4 | 161.33–162.14 | 87.14–87.70 | 85.46–85.72 |
| b11804 / ngram-map-k + d4 | 171.74–181.34 | 87.81–87.93 | 85.74–85.80 |

The engine upgrade improves mean code decode by **19.9%**, short prose by
**15.7%**, and longer prose by **8.8%** in these samples. Code prefill remains
around 2.4K tok/s. b11804 d4 uses 5,044 MiB at 8K after measurement.

**Neither tested ngram stack earns a default.** Prose outputs, accepted-token
counts, and draft-token counts match the b11804 d4 baseline, with no speed gain.
Code output also matches, but ngram-simple slows it by about 15%, and ngram-map-k
by 5–10%. The map implementation retains lookup state across requests (see its
server log), so run-to-run variation is not purely timing noise. These findings
close the tested wildcard configurations, not every possible repetitive-prose
workload or ngram tuning choice.

## Depth-7 follow-up

b11804 d7 at 8K: code **209.11–210.70 tok/s**, short prose **63.11–63.22**,
longer prose **66.43–66.52**. All output hashes match b11804 d4 on these prompts.
The previous 173 tok/s result was a limit of the tested b11118 setup, not a
hardware or model throughput ceiling. Depth 7 still trades prose speed for code
speed, so depth 4 remains the mixed-workload choice.

Execution note: after all nine d7 responses were saved, editing the validation
shell script while it was running caused a shell read-offset error (`92: command
not found`). Its rollback restored b11118/64K successfully. The d7 raw timing
records remain complete, but its boot log was overwritten by the shell error
and its final server log was not captured. `validate-64k.sh` resumes the remaining
validation separately; this was an orchestration error, not a server/model crash.

## Final 64K validation and decision

b11804, 65536 context, DFlash d4, fp16 KV: code **187.98–188.39 tok/s**, short
prose **86.73–87.13**, longer prose **84.86–84.87**. Same output hashes as the
8K b11804 d4 samples. GPU process memory after capability probes: **5,996 MiB**;
the old serve's recorded idle figure was 5,824 MiB. These are different post-load
states, not a controlled allocator-only memory comparison. This validates a
64K-configured serve, not generation with 64K tokens already in the prompt.

River puzzle passes thinking-on with 1500 tokens and thinking-off. The 300-token
thinking probe still exhausts its budget. Tool call plus continuation passes.
Median repair at 1000 tokens thinking-on returns no final content and ends with
`finish_reason=length`; a repeated run confirms this. At a 2000-token budget it
finishes in 1114 tokens and passes execution checks. Thinking-off passes in 102
tokens. Raw responses are in `median-retests.jsonl`; all initial probe outcomes,
including failures, remain in `new-64k-d4-probes.jsonl`. The original probe now
accepts bare code as well as fenced code and supports `BOLT_PROBE_OUT` to keep
engine-specific evidence separate.

**Promoted b11804 as the runner's default engine, with live 64K / d4 and no ngram.**
Main and draft model files were not changed. Full AG-Bench was not rerun: the
historical 10/11 n=2 result remains attached to b11118. This upgrade is supported
by speed measurements, output comparisons, and the capability probes above.

Launch the current serving configuration:

```bash
BOLT_CTX=65536 bash experiments/nemotron-bolt-e4b-20261023/run-bolt.sh dflash-d4
```

Rollback to the original engine, same weights/context/depth:

```bash
BOLT_IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
BOLT_CTX=65536 bash experiments/nemotron-bolt-e4b-20261023/run-bolt.sh dflash-d4
```

For an old-engine measurement rerun, use the same explicit rollback image with
`BOLT_CTX=8192`, then `measure.py` with a fresh label. Do not append reruns under
an existing label when reporting an n=2 range.
