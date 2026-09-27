# Keyed-Gumbel exact sampling — llama.cpp integration plan (2026-09-27)

Grounded against the LOCAL tree `~/Desktop/github/llama.cpp-upstream` @
`e6ab7c1a4` (`common/sampling.{h,cpp}`, `tools/server/server.cpp`). The module
(`notes/keyed_gumbel_sampler.h`) is validated — 16/16 test classes green
(`notes/keyed_gumbel_sampler_test.cpp`), 300k-draw distribution matches softmax
to 4 decimals. This plan is written but **not yet built/served** — that + a drift
re-run is the follow-up item and needs a patched host or docker build.

## What it buys, honestly

- **Temp>0 runs become replayable**: every token is a pure function of
  (seed, absolute position, logits) — no RNG sequence, no order dependence.
  Re-runs of the same prompt+seed replay byte-identically even across restarts.
- **Spec-decode acceptance becomes TensorFold's "equality" semantics**: the verify
  row for position p and the serial step at p call the SAME pure function; if the
  logits agree bitwise, the tokens agree bitwise.
- What it does NOT fix alone: greedy drift (already measured, 1/6 on E4B MTP) and
  sampled drafted-vs-serial drift both *also* need batch-invariant verify logits
  (the kernel work). Sampling exactness + kernel invariance together give the full
  "drafts change speed only" guarantee; this patch is the first half.

## The splice (5 hunks, all in common/ + one server line)

1. **`common/keyed_gumbel_sampler.h`** — copy of `notes/keyed_gumbel_sampler.h` as-is.

2. **`common_params_sampling`** (`common/sampling.h`): add
   ```cpp
   bool     keyed_exact = false;      // opt-in: position-keyed Gumbel-max sampling
   uint64_t keyed_pos_base;           // absolute position of the first sampled token
   ```
   and a counter in `common_sampler`: `uint64_t n_gen = 0;` (guard: count only
   `is_generated` accepts).

3. **`common_sampler_init`** (`common/sampling.cpp:336-405`): when
   `params.keyed_exact`, build the chain WITHOUT the stochastic stage — keep
   logit-bias, penalties, rbudget, grammar; skip the `dist`/mirostat branch
   (the keyed pick replaces it entirely; xtc/typical/etc. warn-and-ignore).

4. **`common_sampler_sample`** (`common/sampling.cpp`, the body around the
   chain-apply, ~line 640): after `rbudget`/grammar handling (all deterministic
   processors still applied, so their effect stays), take the processed
   `cur_p.data[i].logit` array and call
   ```cpp
   const uint64_t pos = gsmpl->params.keyed_pos_base + gsmpl->n_gen;
   id = keyed_gumbel::choose(gsmpl->params.seed, pos, logits, cur_p.size,
                            gsmpl->params.temp, gsmpl->params.top_k, gsmpl->params.top_p);
   ```
   marking `cur_p.selected` to the returned id (for the grammar re-check path).

5. **Position bookkeeping — for free, with one ordering note**: the counter must
   advance per accepted generated token; `common_sampler_accept(gsmpl, token, /*is_generated=*/true)`
   is called after each row in `common_sampler_sample_and_accept_n`
   (`common/sampling.cpp:678-699`). Inside that loop, row i's sample sees
   `n_gen == n_gen_at_round_start + i` — exactly the absolute position TensorFold
   keys on, for both serial rounds (draft empty) and verify rounds. Accept-ordering
   does the bookkeeping; no other change needed there.

6. **Server wiring** (`tools/server/server.cpp`): in the request-handling path
   where `slot.params` is filled from JSON (search `params_search` / sampling
   json props), add `"keyed_exact"` (bool, default false) mapping to the flag, and
   right after prompt tokenization set
   `common_sampler_set_keyed_pos(smpl, /*first sampled pos =*/ slot.n_prompt_tokens)`
   (one-line setter; per-slot sampler makes this safe with `--parallel > 1`).
   The request keeps using the existing `seed` field; with `keyed_exact` the seed
   becomes the key base instead of an RNG init (document in the prop's help text:
   same prompt + same seed → same reply, serial, drafted, and across re-runs).

## Test protocol after build (the acceptance bar)

1. `keyed_gumbel_sampler_test.cpp` — green (done, pre-integration).
2. Repro at temp>0: same prompt+seed, 3 runs, serial — 3/3 byte-identical.
3. Cross-restart repro: restart server between runs — still identical (the RNG
   state no longer lives in the process).
4. Drift harness (`notes/spec-drift-test-llamacpp.sh`) with `keyed_exact` + greedy
   on E4B: expectation UNCHANGED vs tonight's result (sampling equality does not
   touch greedy logits) — this run isolates "sampler layer" from "kernel layer".
5. Kernel-invariance pairing (Bonsai e1/e0 runs, tonight) decides whether the
   combined drafted==serial test can pass on the ternary lane now or waits for the
   fork patch.

## Why this design and not a `llama_sampler` custom stage

The `llama_sampler_chain` stages do not receive the absolute position — only the
server/common layer knows it. Making the keyed pick a first-class op inside
`common_sampler_sample` keeps the position bookkeeping in one place and leaves the
`llama_sampler` backend API untouched (backend/LGPU runtimes using the chain
directly are unaffected).

## Effort

~150 lines total. The patched build: host `cmake -DGGML_CUDA=ON
-DCMAKE_CUDA_ARCHITECTURES=75` from the local upstream tree, or extend the
digest-pinned docker recipe with a bind-mount build once the patch is validated.