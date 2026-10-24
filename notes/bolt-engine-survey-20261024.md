# Bolt E4B engine and application latency survey — 2026-10-24

Research and source inspection, not a new engine performance benchmark. Live
serving configuration was not changed. Preserve UD-Q4_K_XL, 165 W, and the no-AD-Q4
constraint. Existing measured results: ../experiments/bolt-four-tricks-20261024/README.md.

## Architecture gate

The NVIDIA config declares Gemma4ForConditionalGeneration, hidden_size_per_layer_input
256, 42 layers, 18 shared-KV layers, sliding/full attention with head dimensions
256/512, and enable_moe_block=false. It is not NemotronH or a Mamba model. Thus
support for another Nemotron/Bolt model or Gemma 4 31B/26B does not establish E4B support.
The earlier NEXT-IDEAS entry's Mamba characterization is incorrect for this target.
Source: https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-BF16/blob/main/config.json

## Engine triage

- ik_llama.cpp: strongest next direct comparison. Its Gemma4 PR explicitly supports
  E4B on a single GPU, and the project targets Turing CUDA, has Gemma assistant MTP
  and DFlash infrastructure. Exact Bolt/DFlash pairing and tool templates remain
  untested here. Its XL warning specifically calls out F16 tensors; our actual
  file contains F32:339, Q5_K:168, Q6_K:90, Q4_K:43, Q8_0:42, Q2_K:36,
  BF16:1, IQ4_NL:1, F16:0 (read with GGUFReader, no weight changes). This passes
  that narrow warning check, not whole-engine compatibility.
  https://github.com/ikawrakow/ik_llama.cpp
  https://github.com/ikawrakow/ik_llama.cpp/pull/1581
- ExLlamaV3 / TabbyAPI: Turing work is relevant, but current README excludes E2B/E4B;
  Gemma4Config raises NotImplementedError for nonzero hidden_size_per_layer_input.
  Its recent NemotronH Bolt support is not this Gemma-derived Bolt E4B. Porting
  PLE and validating shared KV is a development project before any speed claim.
  https://github.com/turboderp-org/exllamav3/blob/master/README.md
  https://github.com/turboderp-org/exllamav3/blob/master/exllamav3/architecture/gemma4.py
  https://github.com/turboderp-org/exllamav3/issues/417
- TensorFold: published native Gemma recipes are 31B/12B on M5 Metal; the CUDA
  runbook qualifies Lightning on GB10, SM86 and Blackwell. No verified Bolt E4B
  SM75 serving recipe found. Native CUDA support in general is insufficient.
  https://github.com/ashhart/TensorFold/blob/main/README.md
  https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md
- Strata (Niko1221, our engine): installed 0.2.4 importer scope still omits gemma4,
  and no Gemma implementation was found in its src/include scan. Not a drop-in
  Bolt engine. Other unrelated projects also use the Strata name. PolyStrata
  advertises Gemma 4 26B-A4B, which is not evidence of E4B/PLE support.
  https://github.com/Niko1221/Strata
  https://github.com/Niko1221/Strata/blob/main/apps/host/docs/plans/17-local-model-import.md
  https://github.com/AmesianX/polystrata
- oMLX: requires Apple Silicon/macOS. Cannot accelerate this Linux RTX 2080.
  https://github.com/jundot/omlx
- Maya: launcher for llama-server, not independent compute kernels. Its highlighted
  tensor-sharding gain comes from multi-GPU llama.cpp configuration; our single GPU
  cannot use that mechanism. Configuration ideas may still be useful.
  https://github.com/Git-er-done-son/Maya_llama_server_launcher/blob/main/README.txt
- vLLM: upstream issue reports Gemma4 256/512-head attention failures on SM75,
  including shared-memory exhaustion. This is a reported version-specific issue,
  not proof all future releases fail. Require a small E4B/SM75 attention smoke
  before a full environment or checkpoint conversion.
  https://github.com/vllm-project/vllm/issues/38918
- SGLang: no verified exact Bolt E4B + SM75 + suitable 8GB quant + speculative
  path established in this survey. Treat as feasibility research, not a predicted
  speed win. Multi-request throughput claims cannot establish single-agent latency.
  https://docs.sglang.io/docs/get-started/install
- TensorRT-LLM: published reference matrix does not list Turing as a tested target.
  TensorRT-RTX is distinct: NVIDIA says its LLM execution-provider path on Turing
  is still planned. Generic TensorRT SM75 support does not solve Bolt deployment.
  https://nvidia.github.io/TensorRT-LLM/reference/support-matrix.html
  https://docs.nvidia.com/deeplearning/tensorrt-rtx/latest/architecture/architecture-overview.html
- LM Studio / Ollama: LM Studio's GGUF runtime is llama.cpp; Ollama maintains a
  pinned llama.cpp runner as well. Evaluate an identified backend change, not
  assume a product switch supplies faster kernels.
  https://lmstudio.ai/docs/app
  https://github.com/ollama/ollama/blob/main/llama/README.md

## Prioritized new experiments

1. ik_llama exact-target admission and probes, then serial/MTP/DFlash if supported.
   Pin source and record identical model SHA, prompt tokens, context, and power.
   Compare completed-task time and pass rate, not only decode rate.
2. Matched native cuBLAS + MTP d2/d3, versus cuBLAS + DFlash d4/d7. These combined
   profiles have not been tested. Existing individual gains do not multiply by assumption.
3. Separate session profiles for code versus chat; then investigate adaptive DFlash
   depth driven by accepted tokens per verification millisecond. Avoid restarting
   models or rebuilding a long cache every tool turn. Switching drafter families
   mid-session is not established as an existing seamless feature.
4. Real thinking-budget experiment: thinking off for simple chat/formatting;
   sufficient reasoning for debugging/planning. b11804 has --reasoning-budget,
   distinct from total max_tokens. A 300-token total cap previously produced no
   final answer. Verify actual template behavior and task pass rates.
5. Agent turn tracing: separate prompt, reasoning, visible output, tool execution,
   harness overhead, retries and compaction. Group independent reads/searches,
   use bounded relevant tool output and patches, and preserve stable cached prefix.
   Existing cache replay already saved 74% prompt time; do not count it as a new gain.
6. Profile GPU kernels before surgery: output projection over 262144 vocabulary,
   sampler/synchronization, PLE access, shared-KV attention, and draft verification.
   Investigate fusion or selective backend dispatch only where measured time lands.
   CUDA graphs are already reused in baseline logs; enabling them is not a new idea.
7. Long-history ladder (8K/32K/60K actual occupied context) for shortlisted profiles,
   with task quality checks. Allocated 64K context is not a 64K-history decode test.

Already tested: larger ubatch 1024 gave no gain; 2048 OOM; target Q8 KV mixed;
Q8 draft KV and requantized Q4 drafter slower; ngram modes negative. Revisit only
with a specific changed mechanism. No AD-Q4 swap or arbitrary context extension.

Acceptance: two or more repeats, code and chat and real agent traces, same budgets,
first useful answer/tool latency plus successful task wall time, memory and 165W cap,
retain failure evidence. No predicted percentage for unmeasured alternatives.
