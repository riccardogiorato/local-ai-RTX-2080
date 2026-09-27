# Design: recurrent-state snapshots for DeltaNet-class hybrids (b11118 lineage)

Draft of sibling-handoff item #2 (from the David19p research note §adoption-worthy).
This is the design document; the patch draft follows in §5. No GPU needed to draft;
validation plan in §6.

## 1. The problem

Qwen3.5/3.8-hybrid models carry ~48 "DeltaNet-like" gated-DeltaNet blocks whose
state is a *recurrent* (fixed-size per layer) tensor, plus a few classical
KV-attention layers. On multi-turn chat, llama.cpp already reuses the KV part of
a slot across turns (prefix cache match). The recurrent part, however, rides the
same machinery as KV sequence bookkeeping: `snn`/`wfn`/`target_feat` tensors are
part of `llama_state_seq_get_data`/`..._set_data` (the state save/restore path),
but the **hot path — processing a new turn when the previous turn's context is
still resident in the slot — pays a full state serialization round-trip whenever
the runtime manipulates sequence ids** (shift/truncate), because recurrent
state has no cheap "just continue from here" representation in the batch graph.

Concretely, the cradle of the tax is these patterns in the hybrid graph builder
(`llm_graph_context::build_kv` variants + the hybrid models' `build_ssm` /
DeltaNet paths in e.g. `src/models/qwen35.cpp` / `qwen38.cpp`):

- state tensors computed fresh per ubatch pass, with
  `ggml_view/imul/acc` over `inp_state`/`state_pred` views,
- the runtime's sequence-shifting machinery (`llama_memory_context` /
  `llm_graph_input` classes) choosing between "recompute-from-KV" vs
  "carry-state-forward" paths as a function of `seq_ids` bookkeeping.

With `--cache-ram`(prompt cache) flows, EVERY multi-turn move on hybrid models
pays: seq-rm → state-get → state-set → recompute contours. Measured symptom on
this card: multi-turn chat on ThinkingCap/Qwen-hybrids shows a per-turn
"rebind" latency (we observed the grooming in the AG-Bench turns and the
restore-rebind of the UBBoost shuttle: `restore into slot → n_prompt_tokens_cache: 0`,
state present but the metadata matcher refusing to credit it).

## 2. The idea (David19p distilled)

Instead of feeding sequence-id manipulation, give the hybrid blocks **explicit
snapshot views**: `ctx_snapshot = ggml_view(ctx0, g->lcp, n_seq, ...)` with
`reused = N` marked per-block. The graph then either (a) recomputes only the
delta rows (state continues from the snapshot view directly), or (b) skips
entirely if the ubatch lies within the snapshot's coverage. The analogous
mechanism already exists for the ATTENTION part ("prompt cache"); the recurrent
half needs its own bins.

The payoff is **per-turn latency**, not raw tok/s: skip the recurrent-state
recompute walk that every turn pays today. Multi-turn chat wall-time and agent
loop turns shrink by the fraction of state-recompute the snapshot avoids.

## 3. Where it plugs in (b11118-era codebase map)

1. `llm_graph_input` family (`src/llama-graph.cpp`): add an
   `llm_graph_input_recurrent_snap` input type carrying
   `{layer_range, n_tokens_covered, seq_id, snapshot_age}`.
2. The hybrid builders (`build_ssm`-class functions in
   `src/models/qwen35.cpp`, `qwen38.cpp`, `qwen3.8-flash-next`-era builders):
   accept an optional snapshot input; when present and the ubatch is a strict
   continuation (`lcp == snapshot.n_covered`), emit
   `state_prev = view(snapshot.snn[layer])` instead of running the
   `inp_state`→`state_pred` chain from scratch.
3. `llama_memory_context`/seq bookkeeping (`src/llama-arch.cpp` +
   `llama-memory.*`): on prefix-cache HIT for hybrid models, keep a per-seq
   recurrent snapshot registry (small: `n_layer_hybrid × state_bytes`,
   ~[48 layers × state` ≈ low hundreds of MB at most]); invalidate on shift.
4. Server surface: nothing new. The effect appears in the existing `cache_prompt`
   fast path.

## 4. Risk profile

- GGML graph correctness only; no CUDA changes (pure C++ host-side) — Turing-
  safe by construction.
- The snapshot views are read-only into existing graphs; risk concentrated on
  invalidation-on-shift correctness (a stale snapshot = silently wrong
  continuations — mitigated by hooking the same invalidation sites the KV
  metadata uses).
- Measured acceptance test exists already: our slot-shuttle failure
  (`n_prompt_tokens_cache: 0`) is precisely the class of bug this design removes
  for the recurrent halves — it doubles as the regression canary.

## 5. Patch draft (v0 — sketch-grade, against b11118 naming)

```cpp
// llm-graph.h — near llm_graph_input_embd
struct llm_graph_input_recurrent_snap {
    struct snapshot_meta {
        llama_seq_id seq;      // which sequence the snapshot belongs to
        size_t        n_cov;   // tokens covered (the 'lcp' anchor)
        int           age;     // ubatches since last refresh
    } meta;
    ggml_tensor * snn;        // [n_hybrid_layers, seq, ...] view bundle
};

// qwen35.cpp build_ssm-equivalent — head
if (snap && ubatch.pos_first == snap->meta.n_cov) {
    state_prev = ggml_view_3d(ctx0, snap->snn_layer[il],
                              state_ne0, n_seq, 1,
                              /*offs*/ 0);
    g->mark_reused(il, "snap_hit");
} else { /* existing inp_state path */ }
```

v0 is deliberately incomplete: it exists to anchor code review around the
two true questions — (a) the invalidation hook placement, and (b) whether
snapshot views survive `ggml_backend_sched` rescheduling (they should: the
same guarantees as the prompt-cache views).

## 6. Validation plan (when GPU frees)

1. Correctness canary: ThinkingCap, 5-turn chat at 8K — outputs bit-same with
   patch on/off (temp 0, same seeds).
2. Latency: measure per-turn rebind wall time (`prompt_ms` of turn N>1 with
   cache_prompt on) before/after; expect the rebind component to shrink.
3. Regression canary: the slot save/restore shuttle (thinkingcap + tc-prefill.bin
   state) — with the patch, restore should keep `n_prompt_tokens_cached > 0`
   for the recurrent layers; without it, the shuttle stays broken (today's truth).

## 7. What this is NOT

Not speculative-decoding-related (no GPU drafting); not a tok/s win per se; not
applicable to pure-attention models. It's a turn-latency optimization for the
hybrid family — portable to the bonsai fork (same lineage) and to the
qwen4exp/Flash-Next builder (its 48 DeltaNet blocks are the same class).