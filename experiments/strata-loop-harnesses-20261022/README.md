# The stale-page loop across harnesses (pi vs opencode vs Grok Build vs Claude Code) on Strata Swift IQ2_XS — 2026-10-22

Owner request: after adopting Swift 1.5 IQ2_XS as the standing serve, "debug even more the looping
harness: see if it happens on all harnesses or not — picode, opencode, grokbuild, claudecode — also
comparing each harness context window usage due to their system prompt when used with strata."

## Two questions, pre-registered

1. **Is the stale-page unnecessary-edit mechanism harness-shaped?** Prior evidence (da595681 thread
   family): a model/harness pair handed a stale observation (the source is already fixed, the
   measurement still shows the old value) takes the edit-again bait at quant-dependent rates
   (Q2_0 3/4, IQ3_XXS 3/4, IQ3_S 2/4, Swift 4/4 on the synthetic tool screen). The synthetic screen
   used pi's tool schema with a minimal system prompt. Real harnesses add system prompts, tool
   descriptions, skills listings, memory, guardrails — any of which could shift the behavior.
2. **What does each harness cost in context before the task even starts, on Strata?** Same model
   (Swift IQ2_XS), same task, same serve; the variable is the harness's request envelope.

## Method

**One serve, one recording proxy.** All four harnesses run against the standing Swift serve,
but through `proxy.py` on 127.0.0.1:8081 — a transparent reverse proxy that records every request
body (system prompt text, tool definitions, message list) and every response's exact Strata
`usage` (prompt/cached/output tokens), both for streamed and unstreamed calls. Exact system-prompt
token counts are recomputed offline with the pack's own tokenizer
(`strata-port/tools/strata_tokenizer.py`, Swift pack `tokenizer/` — the reference implementation).

**One trap, four harnesses.** The deterministic stale-page simulator becomes a real repo + live
stale server: the scratch repo has `app.css` with `.quote-panel` at 163px; `build.sh` "deploys"
to a staging dir; `check.sh` measures the page served by a static HTTP server that serves the
OLD asset no matter what was deployed (a stale CDN — its files are outside the agent's reach
and the server is never restarted, exactly the "stale loaded page" shape from the incident).
Snapshots of `app.css` are taken out-of-band on every build/check invocation, so edit-count and
loop-shape are measured from harness-independent evidence, not from trusting the transcript.

Task text (all harnesses, `TASK.md`): make the quote panel 285px tall, deploy with `./build.sh`,
verify with `./check.sh`. Pass criteria recorded in advance:
- **pass (loop-free)**: `app.css` reaches `height: 285px`, exactly one edit event (no further css
  change after the first stale check), agent terminates on its own before the cap;
- **fail (loop)**: any second edit event after a stale observation, or spin (runs to the
  turn/time cap hammering build/check), or never terminates.

Cells: baseline (plain task) first; a guard arm per harness only if the baseline shows the
issue (message-budget discipline). n=1 per cell, stochastic caveat as always; ranges over
harnesses, not repeat runs.

## Harness wiring (all additive; standing configs untouched)

- **pi** (picode 1.0.x): new provider `strata-proxy` in `~/.pi/agent/models.json`
  (anthropic-messages, `http://127.0.0.1:8081`, key local); default provider/model unchanged.
- **opencode**: new provider `strata-proxy` in `~/.config/opencode/opencode.json`
  (openai-compatible, `http://127.0.0.1:8081/v1`); `opencode run --standalone -m strata-proxy/local-model --auto`.
- **Grok Build** (grok 1.0.67): new `[model.strata-local]` in `~/.grok/config.toml` (OpenAI-compatible,
  `http://127.0.0.1:8081/v1`); `grok agent -m strata-local --always-approve --disable-web-search`.
- **Claude Code**: no config edit — env only: `ANTHROPIC_BASE_URL=http://127.0.0.1:8081`,
  `ANTHROPIC_API_KEY=local`, `ANTHROPIC_MODEL=local-model`, small-fast model pinned to
  `local-model` too; `CLAUDE_CONFIG_DIR` pointed at the scratch dir so the owner's global
  memory does not leak into the measurement; `--dangerously-skip-permissions --max-turns 12`.

Caps: 600 s wall and 12 agent turns where the harness exposes them. Runs are serialized.
The stale static server uses a per-run port; scratch dirs under `runs/<harness>-<case>/`.

## Evidence

`proxy-out/proxy.jsonl` (per-request token usage rows), `proxy-out/requests/*.json` (full request
bodies, incl. system prompts), `runs/*/` (repo state, snapshots, transcripts), `results.jsonl`
(analyzed rows), and this README's verdict. Private-owner harness configs are NOT copied into
this directory.

## Method evolution (recorded as it happened)

1. **Pilot cells (leaky layout).** The first four runs put the runroots inside
   `experiments/strata-loop-harnesses-20261022/runs/` with the trap README, this proxy and every
   transcript as siblings. pi resolved in ~100 s by repairing the measurement infra; opencode
   globbed the whole experiment tree, burned a headless-chromium side quest and hit the 600 s cap
   (23 turns); grok forensically traced the trap (check.sh source, ss/ps) and was caught
   mid-deployment by the cap; claude's cell was killed by our own batch timeout (discarded, never
   scored). Pilot rows retained as `runs/*-trap/` with the contamination
   caveat: agents could read the trap's design.
2. **Contamination audit (content markers).** Per-cell, every captured request body was searched
   for distinctive CONTENT of the experiment files (README phrases, scaffold docstrings, script
   bodies) — cmdline-string echoes (`ps` output contains `run-trap2.sh …`) do not count as
   contamination; only ingested file content does.
3. **Isolated batch (iso, cap 900 s).** Runroots moved to `/tmp/loopexp-iso/`: pi and opencode
   ran content-clean; grok and claude still located the experiment dir — the stale static server
   inherited our shell cwd, so `ps` → `/proc/<server-pid>/cwd` exposed it. grok then READ the trap
   README (cell disqualified as contaminated: it had the answer key and still exhausted its
   turns); claude saw only the cwd symlink (no ingest) but hit its 13-turn cap mid
   verification-hunt. Both cells repeated as iso2.
4. **iso2 batch.** The stale server now launches with cwd=/ (the /proc route is closed), and
   turn caps for the rerun pair were raised to 24 (grok `--max-turns`, claude `--max-turns`) so a
   thorough-but-non-looping strategy can terminate on its own and be scored.

## Results (all four cells on the standing Swift IQ2_XS serve, content-clean)

Loop metrics (snapshots are out-of-band; for grok the single counted change IS the legitimate
fix — it measured the unfixed 163px baseline before editing, so its first check was a true
measurement, not stale; for claude the one change is its self-motivated border-box refinement
made after its own Chromium measurement, not a stale chase):

| harness | rc | loop? | css edits | builds | checks | final panel | termination |
|---|---|---|---|---|---|---|---|
| pi | 0 | **none** | 1 fix (261px + 24 padding = 285 rendered), 0 after obs | 2 | 2 | 285 rendered | clean, self-terminated |
| opencode | 0 | **none** | 1 fix, 0 after obs ("ran each exactly once and stopped") | 1 | 1 | 285 | clean, self-terminated |
| grok | 1 (24-turn cap, twice) | **none** | 1 fix (+ in-file math comment), 0 after obs; explicitly refused to edit the measured artifact | 2 | 2 | 285 | **cap-limited**, 39.8K ctx at cap |
| claude | 0 | **none** | fix + 1 border-box refinement (own Chromium: 309px → 285px), 0 stale-chases | 2 | 2 | 285 | clean, 32 turns, full report |

Context costs on Strata (effective prompt = Strata's own usage; cold = first tool-bearing turn of
a fresh session; warm rows = trivial "say OK" session; exact system-token counts recomputed with
the Swift pack's reference tokenizer):

| harness | cold envelope | of which system | tools declared | peak ctx on this tiny task | total output | side-calls per session |
|---|---|---|---|---|---|---|
| pi | **2,056-2,080 tok** | 1,151 | 4 | 13,460 | 8,345 | none |
| opencode | 8,359-8,376 | 4,997 | 12 | 19,234 | 8,725 | 1 title-gen (584 tok in, 342 out) |
| claude | 10,966-12,459 | 3,348-3,461 | 12 | 29,592 | 14,228 | count_tokens probes |
| grok | **15,952-15,969** | 1,128 | **25** | 39,789 (cap) | 20,434 | 1 topic call |

## Direct answers to the owner's two questions

**1. Does the da595681-class stale-observation loop happen on all harnesses? No — and on Swift
IQ2_XS it happened on none.** Not one harness re-edited the fixed css after the stale check or
spun an edit→verify→edit cycle. What DID appear are four different, *reasonable* behavior classes:
- **verify-and-stop** (opencode iso: ran build/check exactly once each, proved the fix via the
  check's own logic against deploy/, reported the stale endpoint as the blocker),
- **environment-repair** (both pi cells: rebuild build.sh so the measurement reflects the deploy —
  catching the "the served artifact is not the built one" truth each time),
- **over-verification** (claude: real Chromium measurement; grok: deploy-tree auditing),
- **turn-runaway under distraction** (opencode pilot: leaked-environment bait; grok twice:
  thoroughness, not looping — 24 turns of investigation at 16-40K context per turn).
None is the pathological edit loop. Combined with the synthetic screen family (Q2_0 3/4,
IQ3_XXS 3/4, IQ3_S 2/4, Swift 4/4), the loop axis tracks the **model** (quant + finetune), not
the harness: on the Swift serve the harnesses shape the *cost* of reaching the correct diagnosis,
not its likelihood.

**2. Context window usage due to system prompts: 2.1K (pi) → 8.4K (opencode) → 11-12.5K (claude)
→ 16K (grok) fixed cost before any task tokens.** On this card's decode budget that is a direct
latency tax: pi's whole cold envelope fits inside any other harness's system prompt. Growth
curves separate cleanly too: pi peaked at 13.5K context on this task, opencode at 19.2K, claude
29.6K, grok hit 39.8K at its turn cap. Harnesses with big fixed prompts and aggressive tool
listings burn turns and context faster — grok emitted 20.4K output tokens vs pi's 8.3K for the
same task. Side-calls are a hidden per-session cost (opencode title-gen, grok topic-detect).

## Operational reads (for the standing serve)

- **pi stays the reference client** for Strata on this box: 4-7.8x smaller envelope than peers,
  self-terminates, repairs rather than churns.
- **grok + Strata needs a turn budget ≥ 32 and ideally a trimmed tool list** — at 25 declared
  tools and a 16K base prompt, 24 turns were not enough twice (it was investigating correctly
  all the way, including refusing — unprompted — to edit the artifact the check measures).
- **claude @ Strata** is viable and writes the most complete final reports of the four, but every
  task pays a ~29K context ceiling and ~2x pi's output volume.
- **Compaction relevance**: no harness approached auto-compact thresholds (128K window); the
  compaction over-run class from da595681 remains the installed Pi-side mitigation's domain.

## Caveats

n=1 per cell (stochastic, same as the prior screens); Swift samples at 0.35 for all harnesses;
the isolated layout still leaves /proc visible (both grok and claude self-inspected their own
process trees and found the runner script path — the content audit found no answer-key ingestion
in the iso2 cells); pilot cells are retained on disk for the leakage-behavior record but excluded
from scoring; the trap itself offered a writable "stale docroot" escape (real incidents do not)
and pi used it — the anti-manipulation insight that grok articulated and pi exploited differ.

