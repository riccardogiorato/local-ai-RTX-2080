#!/usr/bin/env python3
"""Side-by-side answer battery: identical prompts to Q2_0 and IQ3_XXS chat configs, temp 0.

    python3 side-by-side.py          # boots each config once (A then B), sends BATTERY, saves JSON + markdown

Output: results/side-by-side-<ts>/{q20,iq3xxs}.json + side-by-side.md with paired answers.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402

HERE = Path(__file__).resolve().parent
Q20 = HERE.parents[1] / "recipes/strata-configs/strata-q20-gsq-0144-tailnet.json"
Q3 = HERE.parents[1] / "recipes/strata-configs/strata-q3xxs-gsq-0144-tailnet.json"

SYSTEM = "You are a precise assistant. Answer directly; no filler."

doc = """Meeting notes, ACME Corp, Q3 planning.
- Attendance: Ravi (infra), Giulia (payments), Marianne (security), Paul (data).
- Decision 1: payments API v2 ships Nov 12, after the PCI audit closes (audit window Oct 28 - Nov 4).
- Decision 2: Ravi's team owns the blue/green migration; freeze window Dec 1-10, no exceptions without Marianne's signoff.
- Decision 3: The legacy SOAP endpoint is deprecated on Jan 15; Giulia published the migration guide version 3.1, supersedes 2.8.
- Decision 4: Budget: EUR 40k for the observability overhaul, capped; anything above needs Paul's histogram of current telemetry costs.
- Decision 5: Paul presents data-retention findings on Nov 30, one week before the freeze begins.
- Open item: who runs the incident rotation during the freeze? Marianne proposed Ravi, Ravi countered that Giulia should hold it because payments will be in code-freeze.
"""

BATTERY = [
    ("logic", "A bat and a ball cost 1.10 EUR in total. The bat costs 1.00 EUR more than the ball. How much does the ball cost? Reply with the number and one line of justification."),
    ("logic2", "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies? Also state the inverse claim's truth: are all Lazzies definitely Bloops?"),
    ("codebug", "Find the bug and output ONLY the corrected function:\n```python\ndef counters(n):\n    fns = []\n    for i in range(n):\n        fns.append(lambda: i)\n    return fns\n```"),
    ("codebug2", "This JS rate limiter has a race; explain the race in one sentence and output the corrected code:\n```js\nlet tokens = 0;\nfunction allow() { if (tokens > 0) { tokens--; return true; } return false; }\nsetInterval(() => { tokens = 5; }, 1000);\n```"),
    ("codehard", "Implement a function is_bipartite(graph) in Python that detects whether an undirected graph is 2-colorable, handles disconnected components, and does not mutate the input."),
    ("math", "A factory's output doubles every 3 days. It starts at 8 units. After how many full days does it first exceed 1000 units? Show the calculation in one line."),
    ("italiano", "Spiega in italiano, in massimo 4 frasi, la differenza tra quantizzazione 2-bit e 3-bit per un modello linguistico, e quando conviene l'una o l'altra."),
    ("idiom", "Translate to Italian and briefly explain the trap: 'The data pipeline is a double-edged sword.'"),
    ("doc-reading", f"From these meeting notes, answer precisely: {doc}\nQuestion: Giulia's migration guide is at which version, which one does it replace, and which of Dec 1-10 or Nov 30 falls inside the PCI audit window? Three answers on one line."),
    ("doc-inference", f"Same meeting notes: {doc}\nQuestion: Who most plausibly runs the incident rotation during the freeze, and whose objection must be answered first? One line."),
    ("constraints", "Write exactly three sentences about a GPU's memory bandwidth. Constraints: sentence 2 must contain a number, sentence 3 must not contain the letter 'e' anywhere, and NO bullet points."),
    ("selfref", "In the exact sentence you are about to write, how many words will there be? Write that sentence so your claim is true."),
    ("algorithm", "For an LRU cache with capacity C that has just evicted its oldest key, what is the amortized cost of a single put() in terms of hash-table lookups? One sentence, complexity only."),
    ("emergent", "Give a rule that generalizes all of these: (2,4)->8, (3,5)->15, (4,7)->28, (5,9)->45. Then apply it to (10,13)."),
]


def one_model(name: str, cfg: Path, outdir: Path, log) -> dict:
    run.BASE_CONFIG = cfg
    log(f"boot {name}")
    proc, _load, _props = run.start_server(1, outdir, f"sbs-{name}", None)
    answers = {}
    try:
        for tag, prompt in BATTERY:
            t0 = time.time()
            r = run.chat("http://127.0.0.1:8080", "", [{"role": "system", "content": SYSTEM},
                                                       {"role": "user", "content": prompt}],
                         400, think=False)
            answers[tag] = {"prompt": prompt, "text": (r.get("text") or "").strip(),
                            "seconds": round(time.time() - t0, 1), "err": r.get("err")}
            log(f"  {name} {tag}: {len(answers[tag]['text'])} chars in {answers[tag]['seconds']} s"
                + (f" ERR {r.get('err')}" if r.get("err") else ""))
    finally:
        run.stop_server(proc)
    return answers


def main() -> int:
    outdir = HERE / "results" / f"side-by-side-{time.strftime('%Y%m%d-%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)
    logf = open(outdir / "sbs.log", "w")

    def log(s):
        print(s, flush=True)
        logf.write(f"{time.strftime('%H:%M:%S')} {s}\n")
        logf.flush()

    run.wait_quiet(log)
    runs = {"q2_0": one_model("q2_0", Q20, outdir, log),
            "iq3_xxs": one_model("iq3_xxs", Q3, outdir, log)}
    (outdir / "answers.json").write_text(json.dumps(runs, indent=1) + "\n")
    md = ["# Q2_0 vs IQ3_XXS side-by-side (temp 0)", ""]
    for tag, prompt in BATTERY:
        md.append(f"## {tag}")
        md.append(f"**prompt:** {prompt[:200]}")
        for m in ("q2_0", "iq3_xxs"):
            a = runs[m][tag]
            md.append(f"### {m} ({a['seconds']} s)")
            md.append("")
            md.append(a["text"] or f"(error: {a['err']})")
            md.append("")
    (outdir / "side-by-side.md").write_text("\n".join(md) + "\n")
    log("done -> " + str(outdir / "side-by-side.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())