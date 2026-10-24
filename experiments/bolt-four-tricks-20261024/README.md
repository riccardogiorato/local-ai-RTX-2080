# Bolt: four acceleration experiments, 2026-10-24

Scope authorized: Gemma MTP assistant versus DFlash; default CUDA versus forced
cuBLAS prefill; prefix-cache reuse across agent tool calls; smaller DFlash draft
weights and Q8 draft KV. Target weights remain the original UD-Q4_K_XL file.
The GPU power cap stays at 165 W. No AD-Q4 target substitution.

## Controls and artifacts

- Engine source: b11804, `c7fc5094179bf8a9c73c18593db714f8da41a402`.
- Docker baseline: `server-cuda12-b11804@sha256:490d8cd8000203a3ab8fdfce14ef931e2aa85affd4dd4447bcc75f299f00fd9a` (CUDA 12.8 runtime).
- Both native builds use the same source, CUDA 13.4, GCC 16.2.1, architecture 75,
  Release mode, and otherwise identical options. Only `GGML_CUDA_FORCE_CUBLAS`
  differs. Compare native-default versus native-cublas to isolate the kernel
  choice; comparison against Docker also changes compiler/toolkit/build options.
- All servers use 65536 context, parallel 1, full GPU layers, flash attention,
  fp16 target KV, Jinja, metrics. DFlash baseline depth is 4. Exact commands are
  saved in each `*-config.json`. Failed starts and requests remain recorded.
- Speed tests run after compilation finishes. `mtp-compat` is an untimed
  compatibility check during compilation, excluded from performance conclusions.
- Decode: historical code continuation, short prose, and 512-token essay. One
  excluded warmup and two measured runs per prompt, greedy temperature sampler,
  seed 42, cache disabled. Full responses and output hashes retained.
- Prefill: fixed repository documents tokenized into exactly 2048/8192/32768
  tokens, with an audit-code retrieval check, 32 output tokens. One warmup and
  two measured runs per size. Exact input token arrays are retained.
- Cache replay: saved real task1 agent messages/tool results, converted to
  OpenAI messages with reconstructed tool schemas and the live chat template.
  No tool is executed. One-token completions isolate processing cost. Cache
  on/off sequences each have a warmup and two measured passes, with reversed
  order on the second pass. Reset prompt before every sequence. This is a
  reconstructed replay, not a byte-identical capture of the original HTTP wire.
- The Q4_K_M drafter is an explicit `--allow-requantize` conversion from the
  existing Q8_0 drafter. It is a screening candidate, not a fresh BF16 quant.
  Source weights remain untouched. The Q8 draft-KV test changes only draft K/V.

`bench.py` serializes server ownership, records failures, and restores the pinned
Docker 64K/d4 baseline in `finally`. `build.sh` builds both native candidates;
`cache-replay.py` runs against the current baseline. Model SHA256 records,
quantizer logs, build caches, server logs and raw measurements accompany this file.

## Preparation findings

The Gemma QAT assistant loads successfully against Bolt on b11804 and generated
the correct answer to a simple arithmetic continuation. This is compatibility
evidence only, not a performance or broad-quality result. Its archive-backed
symlink requires an explicit read-only Docker mount. The first load attempt
failed on that missing mount; both the failure and corrected load are retained.

The saved eight-turn task1 session reports 3,775 fresh prompt tokens and 29,487
cache-read tokens (88.65% cached). These are historical b11118 harness counters,
not new b11804 performance measurements. They establish that cache reuse was
already active in real agent turns.

## Measured results

Means of two measured runs after one warmup; token rates are server timings.
All configurations retain the same Bolt target, 64K context and 165 W limit.

| Profile | Code decode tok/s | Long prose tok/s | Peak sampled GPU MiB |
|---|---:|---:|---:|
| Docker DFlash d4 baseline | 190.66 | 85.87 | 6000 |
| Gemma MTP d2 | 162.19 | 103.54 | 4714 |
| Gemma MTP d3 | 178.60 | 92.76 | 4714 |
| DFlash with Q8 draft KV | 184.70 | 84.67 | 5986 |
| DFlash Q4_K_M draft weights | 187.77 | 84.73 | 5834 |
| Native default CUDA | 192.42 | 85.74 | 6000 |
| Native forced cuBLAS | 189.91 | 84.75 | 6080 |

MTP d2 is a prose/memory candidate: about 21% faster on the long prose prompt,
with 1286 MiB lower total sampled GPU usage, but 15% slower on code. MTP d3
trades some prose speed for code speed. MTP and cuBLAS change prose output
hashes, so these compare the same workloads, not identical generated tokens.
Code output hashes match across all seven profiles. Q8 draft KV saves only
14 MiB here and slows decoding; the smaller Q4 drafter saves 166 MiB but also
slows decoding slightly. Neither is a speed upgrade.

| Fresh prompt tokens | Native default tok/s | Native cuBLAS tok/s | Change |
|---|---:|---:|---:|
| 2048 | 2410.53 | 2637.82 | +9.4% |
| 8192 | 2388.96 | 2598.45 | +8.8% |
| 32768 | 2020.08 | 2159.72 | +6.9% |

All measured audit-code retrieval checks pass, with zero cached tokens and
exact requested prompt lengths. cuBLAS helps substantial prefills, but tiny
15/53-token prompts take longer. It does not improve long-prose decode.
Native server health readiness was about 4 s versus 55–59 s for these Docker
starts; that is a build/startup observation, not steady decode throughput or
time to first answer. Warmups exclude cold first-request costs.

The seven-turn cache replay processes 27,757 tokens without reuse, versus
6,316 fresh and 21,441 cached tokens with reuse (77.2% cached). Across the two
measured passes, aggregate prompt processing drops from 11.643/11.646 s to
2.996/3.000 s: 74.3% less time, or 3.88× faster prompt processing. Request wall
time drops from 11.714/11.717 s to 3.067/3.080 s. This is an isolated replay,
not an end-to-end agent speedup; real tool execution and generation still cost
time. Existing agent sessions already reuse the prefix cache.

## Reproduction

Source archive: https://github.com/ggml-org/llama.cpp/archive/c7fc5094179bf8a9c73c18593db714f8da41a402.tar.gz
Extract it to `/tmp/bolt-b11804-tricks`, then run `bash build.sh` from this
folder. The source/build directories are deliberately outside the repository.
`bench.py` contains the exact profile mapping and saves every startup command.
Run `bash run-campaign.sh` only when this machine's GPU and port 8080 are free
for the experiment; it replaces `bolt-serve` during measurements and restores
our pinned Docker baseline afterward. Raw JSONL files append: archive existing
results before a repeat so separate campaigns do not mix.

`verify-profiles.py` compares baseline, MTP d2 and native cuBLAS with capability
probes and one run each of AG-Bench tasks 1 and 9. Median-fix gets 2000 tokens
for every profile; the historical probe default remains 1000. This is a
paired two-task regression smoke check, not a full 11-task leaderboard run.

## Validation and serving decision

All three profiles pass river reasoning at 1500 tokens, reasoning with thinking
off, the executed median fix at 2000 tokens, and the tool-call/continuation
probe. All three exhaust the 300-token thinking budget with no final answer.
Both AG-Bench smoke tasks pass for all three profiles:

| Profile | Task 1 bugfix | Task 9 access-log analysis |
|---|---:|---:|
| Baseline | pass, 17 s | pass, 39 s |
| MTP d2 | pass, 13 s | pass, 17 s |
| Native cuBLAS | pass, 15 s | pass, 14 s |

These agent timings are single runs with different tool trajectories. They do
not establish repeatable end-to-end speedups. Raw sessions are retained under
`agentic-sessions/`; machine-readable outcomes are in `verification-summary.json`.
The earlier full 10/11 ×2 agent record belongs to b11118, not these profiles.

Keep the pinned Docker b11804 DFlash d4 baseline as the live default. cuBLAS is
a validated experimental option for large fresh prefills; MTP d2 is an option
for prose or lower GPU memory use. Neither wins every workload. A combined
cuBLAS+MTP profile was not tested, so do not add their gains together.

`original-sha256-after.txt` confirms the target and original DFlash are unchanged.
Every recorded power-limit sample is 165 W (`power-limit-audit.json`); occasional
instantaneous power-draw samples exceed that configured limit. Final server
identity, arguments and GPU state are recorded in `final-state.json`.
