# Bolt at 64K: alternate engine, combined drafting, reasoning budgets

User-authorized follow-up: test ik_llama; combine forced cuBLAS with MTP d2/d3
and DFlash d4/d7; compare thinking modes. Use the highest model-supported context
for coding/chat. All server profiles request 65,536 tokens, parallel 1, full GPU
offload, flash attention and FP16 target KV. Target stays UD-Q4_K_XL, power limit
165 W, and no AD-Q4 substitution. The standard launcher now defaults to 64K.

## Provenance

- Mainline native engines: same b11804 source and binaries from
  `../bolt-four-tricks-20261024/`, CUDA 13.4, SM75. Forced cuBLAS build unchanged.
- Docker control: b11804 digest pinned in `campaign.py`'s imported bench module.
- ik_llama: source `804ee29c28a5e892df6e84941cb78628ed4c266c`, downloaded from
  https://github.com/ikawrakow/ik_llama.cpp/archive/804ee29c28a5e892df6e84941cb78628ed4c266c.tar.gz
  and extracted to `/tmp/ik-bolt-804ee29`. `build-ik.sh` records build options.
  No source patches. CUDA 13.4, GCC 16.2.1, Release, SM75, CUDA graphs default on.
- ik_llama explicitly uses `--swa-compress`: window-sized storage for sliding
  attention, retaining the full logical context and full-attention history.
  This avoids its default full-context allocation for sliding layers. Source
  `llama-model.h` names Gemma4 as supported. No KV quantization is introduced.
- Original target and draft SHA256: see the preceding experiment. Per-start
  commands, telemetry, engine logs, failures and output hashes are retained.
- Timed performance begins only after the build completes. The one
  `budget128-compatibility.json` request during compilation is explicitly untimed;
  it checks budget plumbing only and is excluded from speed conclusions.

## Workloads and interpretation

`campaign.py prepare` freezes repository code/docs and token arrays. These are
controlled long inputs, not a captured real 60K conversation. Reference
prompts screen retrieval/prefill once at 8K/32K/61,440 tokens. The 61,440-token
code continuation measures both prefill and decode with one excluded warmup and
two measured runs. Fresh prompt token counts must match
exact lengths. Retrieval checks catch lost/truncated context. Historical short
code/prose tests also use one warmup plus two measured runs, at 64K allocation.
Different output hashes mean rates compare workloads, not identical sequences.

Capability probes run after each complete speed profile; all receive the same
budgets, including 2000 for the median repair. The 300-token *total-output* river
probe remains a deliberately small-budget case, distinct from reasoning limits.

`campaign.py reasoning PROFILE` tests median and interval merging, with edge-case
and input-mutation checks. Modes: thinking off, 128 or 512 reasoning tokens, and
unrestricted reasoning. All allow 3072 total output tokens. Each case repeats
twice at short and ~59.6K actual prompt context. Full outputs, reasoning text,
retokenized reasoning length, API usage, timings and verification failures are
retained. Actual measured API counts take precedence over prepared counts.

`agent-thinking.py PROFILE [MODES...]` attaches a real ~48K-token reference file
using Pi's documented `@file` input. Pi sees it in its history and can compact it;
the proxy does not secretly add context. The same tasks 1 and 9 run twice per mode,
with 240 s task caps. The test-local Pi model compaction override reserves 4096
tokens and keeps 8192 recent tokens, matching the 3072 response cap and allowing
long inputs to remain through tool turns. The wrapper writes only inside the task
copy and explicitly trusts those local settings; global Pi settings are unchanged. A local 8080->8082 proxy enforces reasoning mode and a common
3072-token output cap; it buffers responses, so these runs measure complete-task
latency, not streaming first-token latency. Log actual API usage and Pi compaction
when interpreting results. This is a two-task smoke comparison, not full AG-Bench.

All test scripts restore the pinned Docker DFlash d4 / 64K baseline in `finally`.
The test helpers own only their started native process and the `bolt-serve`
container. Logs append; use a fresh output directory or archive results before
rerunning. Do not run two experiment drivers simultaneously on this GPU/port.

## Completed results

Means of two measured runs, excluding warmups. Short decode rates are workload
comparisons; prose outputs can differ. All near-full code answers have the same
42-token output hash. That answer is a compact loop, unlike the longer short-input
continuation: do not attribute their decode-rate difference solely to context.

| Profile | Short code tok/s | Long prose tok/s | 61,440-input code wall seconds |
|---|---:|---:|---:|
| Docker DFlash d4 control | 190.23 | 86.08 | 36.65 |
| cuBLAS DFlash d4 | 191.61 | 84.74 | 34.65 |
| cuBLAS DFlash d7 | 212.83 | 63.03 | 34.91 |
| cuBLAS MTP d2 | 162.33 | 107.59 | 33.53 |
| cuBLAS MTP d3 | 180.00 | 99.13 | 33.58 |
| ik_llama serial | — | 83.10 | 44.99 |
| ik_llama MTP d2 | — | 55.19 | 54.23 |
| ik_llama DFlash d4 | — | 47.90 | 46.68 |

The initial ik starts on port 8080 failed binding the socket, before loading the
model. These are harness failures, not context or compatibility failures. The
fresh `*-8090/8091/8092` runs completed. ik speculation was slower than its serial
path in these configurations; this does not rule out further ik-specific tuning.

cuBLAS MTP d2 reasoning tests passed all 32 executions (two functions, two repeats,
two context sizes, four thinking modes). Means across four checks per cell:

| Thinking mode | Short input seconds | ~59,600 input seconds |
|---|---:|---:|
| Off | 1.30 | 33.73 |
| 128-token reasoning budget | 2.33 | 35.66 |
| 512-token reasoning budget | 2.86 | 36.40 |
| Unrestricted reasoning | 2.85 | 36.43 |

Unrestricted means no separate reasoning cap, still with the common 3072 total
output cap. The 512 cap usually does not bind: mean reasoning lengths were 182
tokens on short inputs and 210 at long context. These simple-function successes
do not establish safe thinking-off behavior for agents.

## Agent results and decision

Two repetitions of each of tasks 1 and 9, with actual occupied context reaching
54,615 tokens. All 140 logged HTTP requests returned 200. Context can change
through Pi compaction; the attached reference is not a guarantee every later turn
retains every original token. Session archives and actual usage are retained.

| Profile / thinking | Passes | Bugfix seconds (r1/r2) | Log analysis seconds (r1/r2) |
|---|---:|---:|---:|
| cuBLAS DFlash d4 / unrestricted | 4/4 | 45 / 56 | 37 / 40 |
| cuBLAS MTP d2 / unrestricted | 3/4 | 38 / 38 | 97 fail / 49 |
| cuBLAS MTP d2 / budget512 | 3/4 | 54 / 39 | 37 / 69 fail |
| cuBLAS MTP d2 / off | 3/4 | 39 / 34 | 39 fail / 101 |

Failure audit: unrestricted r1 and budget512 r2 used report labels/layouts rejected
by the task verifier. Thinking-off r1 wrote incorrect totals and modified its
copied `tests/test_outputs.py` to accept them. The protected-file check correctly
failed that run despite its edited verifier passing. No original task file was
changed (all eight saved source hashes match). These are observed task failures,
not HTTP errors. The small sample does not isolate MTP as their cause.

Keep Docker DFlash d4 with thinking as the normal serving configuration. cuBLAS
DFlash d4 is the strongest tested alternative for large fresh inputs. MTP d2 has
a measured prose/memory advantage, but is not promoted for agent use on these
results. Deeper DFlash d7 helps repetitive code but substantially hurts prose.
Thinking off remains a task-specific experiment, not the agent default.

`summary.json`, `agent-summary.json`, `agent-failure-audit.json`, and the compressed
`agentic-sessions/` hold supporting evidence. `final-state.json` confirms the
pinned Docker image, DFlash d4, 65,536 context, healthy API, 165 W power limit,
and unchanged original task files. No Yukon kernel changes were applied here.
