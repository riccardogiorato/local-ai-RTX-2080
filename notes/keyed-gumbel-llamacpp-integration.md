# Keyed-Gumbel exact sampling — llama.cpp integration (2026-09-27/28) — BUILT & VALIDATED

Grounded against the LOCAL tree `~/Desktop/github/llama.cpp-upstream` @
`e6ab7c1a4` (`common/sampling.{h,cpp}`, `tools/server/server-schema.cpp`), built
at `/tmp/llama-upstream-keyed` (clean clone + patch; the donor tree has pruned
build files, see `hardware.md` ops traps). Module `notes/keyed_gumbel_sampler.h`
validated 17/17 test classes (incl. min_p filter); served and measured on the
card tonight.

## Validation results (Qwen3.5-4B Q4_K_M, upstream kernels = KNOWN logits-drifter, temp 0.8, seed 42, 2 prompts)

| comparison | stock sampler | keyed sampler |
|---|---|---|
| drafted self-repeat (same server) | 2/2 identical | 2/2 identical |
| serial self-repeat | (serial is deterministic without drafts) | 2/2 identical |
| **cross-RESTART replay** (fresh server, same prompt+seed) | n/a (RNG state is per-request) | **2/2 byte-identical** |
| **drafted vs serial** | **2/2 DIFFER** | **1/2 differs — logits-bits only** |

Read: keyed sampling removes every drift term except kernel logits-bits. The
stock 2/2 vs keyed 1/2 difference IS the sampler-order term measured directly;
the residual 1/2 is the batch-dependent-kernels term that
`GGML_CUDA_BATCH_INVARIANT`-style invariance removes (already proven live on
the B bonsai fork at greedy). Cross-restart replay works — the property stock
cannot offer when a chain RNG's position depends on draw count.

## Integration deltas from the original plan (found during validation)

- Upstream's **default sampler list** carries `top_n_sigma` (disabled) and
  `min_p` (enabled at 0.05) — policy refined to llama.cpp stage semantics:
  replicate top_k / top_p / **min_p** / temperature in the module; skip disabled
  stages silently; throw only on enabled-and-unreplicatable ones (xtc>0,
  typ_p≠1, top_n_sigma≥0, infill, mirostat, adaptive_p), and refuse
  `backend_sampling`.
- `min_p` implemented in the module as an order-independent probability
  threshold after top_p (llama.cpp semantics, ties pass/fail together).
- JSON field is `"keyed_exact": true|false` (bool — the schema rejects numbers).
- **Position bookkeeping ended up zero-server-wiring**: `init_sampler`
  re-accepts the full prompt per request, so a total-accepted-tokens counter in
  `common_sampler` (advanced in `accept`, cleared in `reset`) IS the absolute
  position. No server changes beyond the schema field.

## Remaining open

- Upstream the patch (or carry it in the fork lineage): the residual logits-bits
  drift on upstream kernels is already solved for PTQ1_0/Bonsai by the fork's
  invariant routing; combining keyed sampling + invariant kernels on the fork
  gives the full TensorFold guarantee at temp>0. That pairing is untested.

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