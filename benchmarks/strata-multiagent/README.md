# Concurrent coding agents on the RTX 2080: 1 slot beats multi-slot

Measured 2026-10-15, Strata 0.1.44 chat config (Flash-Next 125B GSQ-RCO Q2_0, KV int8) on one 2080 (8 GB) /
i5-9600K / DDR4-3200. Question: do multiple coding agents sharing one server go faster with server-side
slots (`"parallel": N`, engine `--batch N`) or queued one request at a time?

## Work

Four scripted coding-agent sessions from the engine's own `tools/agent_turns_bench.py` (tool calls whose
results are real engine-repo files), cut where the largest prompt is 46.5K tokens: 15 turns total, four
sessions. Agents replay turns with a 1 s simulated tool time between requests; thinking off, temperature 0,
up to 256 new tokens. 2 rounds per arm, reverse order in round 2. A CPU-heavy process on the machine
(the ps2-web-recomp build loop of another session) discards and reruns the arm: the `wait_quiet` +
contend guard in `run.py` is part of the harness; the discarded contended attempt is kept in
`results/discarded/` (its one data point: a concurrent ninja build cuts decode from ~45 to ~11 tok/s).

## Arms and their engine overrides

More slot sessions take VRAM from the expert cache; on 8 GB the phases need per-arm overrides
(probes in `results/probe/`):

| Arm | Slots | Agents at once | Override | Why |
|---|---|---|---|---|
| seq | 1 | 1 (sessions back-to-back) | none | baseline, the standing chat config |
| p1x2 | 1 | 2 (interleaved turns) | none | the queue an agent client actually makes |
| p2 | 2 | 2 | `--kv-resident 16384` | 2 slot sessions at 128K leave room for only the minimum expert cache otherwise |
| p4 | 4 | 4 | + `--max-context 49152` `--prefill auto:49152` | 4 slot sessions do not fit VRAM at 128K; 48K is the largest that starts |

## Results (both rounds)

| Setup | Wall, 4 sessions (s) | Turn median s (max) | First-token median s | Decode tok/s median | Conversation-cache hit |
|---|---|---|---|---|---|
| **seq: 1 slot, back-to-back** | **365 / 299** | **10.1 (78.5)** | 8.8 | 36.5 | 64% |
| p1x2: 1 slot, 2 interleaved | 579 / 578 | 70.9 (135) | 70.0 | **46.5** | **0%** |
| p2: 2 slots, 2 agents | 846 / 849 | 70.1 (362) | 62.6 | 8.4 | 64% |
| p4: 4 slots @ 48K | 1955 / 1637 | 283 (1112) | 279.8 | 9.3 | 46% |

`python3 summarize.py results/multiagent-20261015-113002.jsonl` prints this table from the evidence.

## Verdict

- **Never multi-slot on this card.** Slot sessions evict the expert cache and batch mode drops
  speculative decoding (`drafts accepted 0 of 0` in the engine log): decode collapses from ~36 to 8-9
  tok/s, and prompt reads fall from ~650 to ~200 tok/s. Total wall: 2 slots 2.3x slower than the queue,
  4 slots 4.5-5.4x slower (and 4 slots cost 128K context on top; the fit probes set 48K).
- **A 1-slot queue is the right setup for N agents** when you cannot serialize sessions. Decode stays
  at full speed (46.5 tok/s, even faster than solo: the interleaved sessions warm the shared adaptive
  expert cache over more experts). The cost is the conversation cache: with another agent's turn between
  yours the prefix is not reused (hit 64% -> 0%), every turn re-reads its whole history, so the median
  turn goes 10 -> 71 s. Keep the queue shallow; each extra interleaving agent multiplies that wait.
- **Serialize sessions back-to-back when you control dispatch order** (`seq`): every agent keeps its
  cache (64% hit) and the whole fleet finishes 365/299 s vs 846+ for anything concurrent.

Evidence: `results/multiagent-20261015-113002.jsonl` (30 requests + 8 arm summaries, per-request
engine timings), `results/*.engine.log` (per-arm engine logs), `results/probe/` (slot-fit probes),
`results/discarded/` (the contended attempt). Harness: `run.py` (phases, guard, client), `summarize.py`
(table from evidence), `probe.py` (VRAM fitting).