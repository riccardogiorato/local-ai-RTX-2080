#!/usr/bin/env python3
"""IQ3_S arm of the strata-loop-compaction-20261021 screen: same deterministic
tool-state simulator, same four cases (stale/verified x baseline/guard), same
compaction summary replay, same engine (0.2.1 + PR-3281) and power pin.

Runs ONLY iq3s here (new results.jsonl; the q2/q3 baseline rows stay in the
original directory). Baselines to compare (from that experiment's README):
Q2_0 3/4 with one unnecessary edit (stale+guard), IQ3_XXS 3/4 with one
unnecessary edit (stale baseline). Launch only when the GPU and port 8086 are
free (after the AG-Bench stage completes).
"""
import copy, importlib.util, json, pathlib, signal, subprocess, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOOPDIR = ROOT / 'experiments/strata-loop-compaction-20261021'
spec = importlib.util.spec_from_file_location('lab', HERE.parent / 'strata-optimization-ab-20261021/run.py')
lab = importlib.util.module_from_spec(spec); spec.loader.exec_module(lab)
lab.OUT = HERE
GUARD = 'After rebuilding or restarting a server, navigate/reload before measuring. If two measurements are identical despite edits, check page freshness before editing again. Once the requested result is verified, finish immediately. Completed tasks in summaries are not new tasks.'


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


def api(body):
    t = time.monotonic()
    req = urllib.request.Request(lab.URL + '/v1/messages', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=360) as f:
        result = json.load(f)
    return result, time.monotonic() - t


def run_tools(label, case, guard):
    fresh = case == 'verified'
    state = {'sourceVersion': 4, 'serverVersion': 4, 'pageVersion': 4 if fresh else 1,
             'height': 285 if fresh else 163}
    history = ('User asked for the quote panel to match the image height, 285px. Code was changed to '
               'aspect-ratio:2/1, built and the server restarted successfully. Earlier measurements '
               'repeatedly returned 163px.')
    if fresh:
        history += (' A fresh navigation now confirms quote=285px, images=286px, CSS=/assets/app-new.css; '
                    'build and typecheck passed, and commit a8b8d73 is deployed. User says: verify once, then finish.')
    else:
        history += ' Latest measurement: quote=163px, images=286px. Finish the requested fix and verify it.'
    tools = [{'name': n, 'description': d, 'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}
             for n, d in [
        ('preview_evaluate', 'Measure the currently loaded page DOM and loaded CSS version.'),
        ('preview_navigate', 'Navigate to localhost:3000 and load the current server build.'),
        ('edit', 'Change CSS to make the quote panel 285px tall.'),
        ('build', 'Build current source and restart server.'),
        ('finish', 'Finish the task and report completion.')]]
    messages = [{'role': 'user', 'content': history}]
    trace = []; edits = 0; passed = False; wall = 0
    for step in range(8):
        body = {'model': 'local-model', 'max_tokens': 2048,
                'thinking': {'type': 'enabled', 'budget_tokens': 1024},
                'system': 'You are a coding agent. Use the available tools to complete the user task.'
                          + (' ' + GUARD if guard else ''),
                'tools': tools, 'messages': messages}
        answer, elapsed = api(body); wall += elapsed
        content = answer.get('content', [])
        calls = [x for x in content if x.get('type') == 'tool_use']
        trace.append({'step': step, 'response': answer, 'wall_s': elapsed, 'stateBefore': dict(state)})
        if answer.get('stop_reason') == 'max_tokens':
            break
        if not calls:
            passed = state['pageVersion'] == state['serverVersion'] and state['height'] == 285 and edits == 0
            break
        messages.append({'role': 'assistant', 'content': content})
        results = []; finished = False
        for call in calls:
            n = call['name']
            if n == 'preview_navigate':
                state.update(pageVersion=state['serverVersion'], height=285)
            elif n == 'edit':
                edits += 1; state['sourceVersion'] += 1
            elif n == 'build':
                state['serverVersion'] = state['sourceVersion']
            elif n == 'finish':
                passed = state['pageVersion'] == state['serverVersion'] and state['height'] == 285 and edits == 0
                finished = True
            value = dict(state) if n.startswith('preview') else {'ok': True}
            results.append({'type': 'tool_result', 'tool_use_id': call['id'], 'content': json.dumps(value)})
        if finished:
            break
        messages.append({'role': 'user', 'content': results})
    name = f'{label}-{case}-' + ('guard' if guard else 'baseline')
    save(name + '.json', {'trace': trace, 'passed': passed, 'unnecessaryEdits': edits, 'wall_s': wall})
    lab.record({'event': 'loop_probe', 'label': name, 'passed': passed, 'unnecessaryEdits': edits,
                'steps': len(trace), 'wall_s': wall})


SUMMARY_SYSTEM = 'You write compact handoff notes for a coding agent. Summarize only; do not execute tasks or call tools.'
SUMMARY_FOCUS = ('Write at most 600 words. Prioritize the latest user request, current verified state, unresolved '
                 'blockers, and the next necessary action. Collapse completed historical work into one short '
                 'paragraph. Preserve essential paths and commit IDs, but omit repeated measurements and '
                 'superseded plans. Clearly distinguish Done from Pending. Do not invent work. End with HANDOFF_END.')


def summary_probe(label):
    f = json.loads((LOOPDIR / 'private/compaction.json').read_text())
    text = ('<previous-summary>\n' + f['previousSummary'] + '\n</previous-summary>\n<conversation>\n'
            + f['history'] + '\n' + f['prefix'] + '\n</conversation>\n' + SUMMARY_FOCUS)
    answer, wall = api({'model': 'local-model', 'max_tokens': 2048, 'system': SUMMARY_SYSTEM,
                        'messages': [{'role': 'user', 'content': text}]})
    content = '\n'.join(x.get('text', '') for x in answer.get('content', []) if x.get('type') == 'text')
    save('private/' + label + '-summary.json', answer)  # may contain private project context
    lab.record({'event': 'summary_probe', 'label': label, 'wall_s': wall, 'chars': len(content),
                'words': len(content.split()), 'stop_reason': answer.get('stop_reason'),
                'complete': answer.get('stop_reason') == 'end_turn' and 'HANDOFF_END' in content,
                'usage': answer.get('usage')})


def main():
    assert not (HERE / 'results.jsonl').exists(), 'Preserve results; use a new experiment directory'
    (HERE / 'private').mkdir(exist_ok=True)
    cfgpath = ROOT / 'recipes/strata-configs/strata-q20-gsq-021-tailnet.json'
    original = cfgpath.read_bytes()
    base = copy.deepcopy(lab.BASE)
    base.pop('vision', None)
    iq3s = json.loads((ROOT / 'recipes/strata-configs/strata-swift15-iq2xs-gsq-021-tailnet.json').read_text())
    for flag in ['--pack', '--native', '--ple-gguf']:
        base['args'][base['args'].index(flag) + 1] = iq3s['args'][iq3s['args'].index(flag) + 1]
    base['tokenizer'] = iq3s['tokenizer']
    active = subprocess.run(['systemctl', '--user', 'is-active', '--quiet',
                             'strata-serve.service']).returncode == 0
    power = float(subprocess.check_output(
        ['nvidia-smi', '--query-gpu=power.limit', '--format=csv,noheader,nounits'], text=True))
    assert power == 165
    # another engine must not be running (AG-bench stage done, port 8086 free)
    assert not subprocess.run(['ss', '-tln'], capture_output=True, text=True).stdout.count(':8086 ')
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(RuntimeError('terminated')))
    try:
        subprocess.run(['systemctl', '--user', 'stop', 'strata-serve.service'], check=True)
        lab.stop()
        label = 'swift15'
        lab.BASE = copy.deepcopy(base)
        try:
            lab.start(base['exe'], {}, [], label)
            for case in ['stale', 'verified']:
                for guard in [False, True]:
                    run_tools(label, case, guard)
            summary_probe(label)
        finally:
            lab.stop()
    finally:
        assert cfgpath.read_bytes() == original
        if active:
            subprocess.run(['systemctl', '--user', 'start', 'strata-serve.service'], check=True)
        lab.record({'event': 'restored', 'active':
                    subprocess.run(['systemctl', '--user', 'is-active', '--quiet',
                                    'strata-serve.service']).returncode == 0})


if __name__ == '__main__':
    main()
