#!/usr/bin/env python3
"""Final analysis for the harness-comparison experiment.

Valid cells (post-audit, see README 'Method evolution'):
  pi-trap-iso        runs/pi-trap-iso        rc=0
  opencode-trap-iso  runs/opencode-trap-iso  rc=0
  claude-trap-iso2   runs/claude-trap-iso2   rc=0
  grok-trap-iso2     runs/grok-trap-iso2     rc=1 (24-turn cap; content-clean)

Superseded/invalid (kept on disk but not scored):
  *-trap       pilot cells inside the leaky experiment dir (contamination possible)
  grok-trap-iso   read the trap README (answer key) before exhausting turns
  claude-trap-iso  pre-cwd-leak-patch run, superseded by iso2

Context metrics come from proxy-out/proxy.jsonl (Strata's own usage numbers,
effective prompt = input + cache_creation + cache_read on the anthropic route;
prompt_tokens already includes cached on the OpenAI route). Edit-event metrics
come from the snapshot filenames' embedded epoch-ns (out-of-band, order-proof)
plus css digests.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
PROXY = HERE / 'proxy-out' / 'proxy.jsonl'
VALID = {
    'pi-trap-iso': ('pi', 'runs/pi-trap-iso'),
    'opencode-trap-iso': ('opencode', 'runs/opencode-trap-iso'),
    'grok-trap-iso2': ('grok', 'runs/grok-trap-iso2'),
    'claude-trap-iso2': ('claude', 'runs/claude-trap-iso2'),
}


def rows_for(label):
    return [json.loads(l) for l in PROXY.read_text().splitlines()
            if json.loads(l)['label'] == label]


def context(rows):
    def is_chat(r):
        last = r['route'].split('?', 1)[0].rstrip('/').split('/')[-1]
        return last in ('messages', 'completions')

    chat = [r for r in rows if is_chat(r)]
    main = [r for r in chat if (r.get('n_tools') or 0) > 0] or chat
    if not main:
        return {}
    cold = min(main, key=lambda r: r['seq'])
    return {
        'requests_total': len(rows),
        'chat_requests': len(chat),
        'cold_prompt_tokens': cold.get('effective_prompt_tokens'),
        'system_tokens': cold.get('system_tokens'),
        'n_tools': cold.get('n_tools'),
        'peak_prompt_tokens': max((r.get('effective_prompt_tokens') or 0) for r in chat),
        'total_output_tokens': sum((r.get('output_tokens') or 0) for r in rows),
        'served_wall_s': round(sum((r.get('wall_s') or 0) for r in rows), 1),
    }


def snap_epoch_ns(p):
    m = re.search(r'-([0-9]{19})\.css', p.name)
    return int(m.group(1)) if m else 0


def trap(run_dir: pathlib.Path):
    snaps = run_dir / 'snaps'
    files = sorted(snaps.glob('css-*.css'), key=snap_epoch_ns)

    def h(p):
        return hashlib.sha1(p.read_text().encode()).hexdigest()[:8]

    def state(p):
        m = re.search(r'\.quote-panel\s*\{[^}]*?height:\s*(\d+)px', p.read_text(), re.S)
        return (snap_epoch_ns(p), p.name.split('-')[1], h(p), int(m.group(1)) if m else None)

    states = [state(p) for p in files]
    invocations = [l.split()[-1] for l in (snaps / 'invocations.log').read_text().splitlines()]
    first_check_state = next((s for s in states if s[1] == 'check'), None)
    changes_after_first_check = 0
    seen_post = []
    if first_check_state:
        seen_post.append(first_check_state[2])  # baseline: css as it was when first measured
        for s in states:
            if s[0] > first_check_state[0]:
                seen_post.append(s[2])
        for i in range(1, len(seen_post)):
            if seen_post[i] != seen_post[i - 1]:
                changes_after_first_check += 1
    final = run_dir / 'work' / 'app.css'
    m = re.search(r'\.quote-panel\s*\{[^}]*?height:\s*(\d+)px', final.read_text(), re.S)
    return {
        'builds': invocations.count('build'),
        'checks': invocations.count('check'),
        'snapshots': len(states),
        'state_track': [(s[1], s[2], s[3]) for s in states],
        'css_changes_after_first_stale_check': changes_after_first_check,
        'final_panel_height': int(m.group(1)) if m else None,
    }


def main():
    out = []
    for label, (harness, rdir) in VALID.items():
        run_dir = HERE / rdir
        out.append({'harness': harness, 'label': label, 'rc': None,
                    **context(rows_for(label)), **trap(run_dir)})
    with (HERE / 'results.jsonl').open('w') as f:
        for r in out:
            f.write(json.dumps(r) + '\n')
    hdr = f"{'harness':10s} {'cold':>6s} {'system':>7s} {'tools':>5s} {'peak':>6s} {'out_t':>6s} {'edits>stale':>11s} builds checks final"
    print(hdr)
    for r in out:
        print(f"{r['harness']:10s} {r.get('cold_prompt_tokens') or 0:>6} {r.get('system_tokens') or 0:>7} "
              f"{r.get('n_tools') or 0:>5} {r.get('peak_prompt_tokens') or 0:>6} {r.get('total_output_tokens') or 0:>6} "
              f"{r['css_changes_after_first_stale_check']:>11} {r['builds']:>6} {r['checks']:>6} {r['final_panel_height']}")


if __name__ == '__main__':
    main()
