#!/usr/bin/env python3
"""Plot measured time against input context, for equal 192-token outputs."""
import csv
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
results = root / 'results'
samples = []
for filename, case in [
    ('strata-0142-release-probe-20261010.jsonl', 'short-0'),
    ('strata-0142-streamed-probe-20261010.jsonl', 'streamed-needle-code'),
]:
    for line in (results / filename).read_text().splitlines():
        row = json.loads(line)
        if row.get('case') == case and row['arm'] in ('0141', '0142'):
            assert row['timings']['generated'] == 192
            samples.append(row)

points = []
for arm in ('0141', '0142'):
    for context in sorted({r['input_tokens'] for r in samples}):
        group = [r for r in samples if r['arm'] == arm and r['input_tokens'] == context]
        points.append({
            'version': '0.1.41' if arm == '0141' else '0.1.42',
            'input_tokens': context,
            'output_tokens': 192,
            'runs': len(group),
            'decode_s': statistics.median(r['timings']['decode_ms'] / 1000 for r in group),
            'prefill_s': statistics.median(r['timings']['prompt_ms'] / 1000 for r in group),
            'total_s': statistics.median((r['timings']['prompt_ms'] + r['timings']['decode_ms']) / 1000 for r in group),
        })

with (results / 'strata-0141-vs-0142-context-time.csv').open('w') as file:
    writer = csv.DictWriter(file, fieldnames=list(points[0]))
    writer.writeheader()
    writer.writerows(points)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12})
fig, axes = plt.subplots(1, 2, figsize=(13, 6.3), sharey=True)
colors = {'0.1.41': '#3d65b8', '0.1.42': '#cf6417'}
markers = {'0.1.41': 'o', '0.1.42': '^'}
for ax, metric, title, xmax in zip(axes, ['decode_s', 'total_s'],
                                 ['Generation only', 'Prompt reading + generation'], [7, 86]):
    for version in colors:
        group = [p for p in points if p['version'] == version]
        ax.scatter([p[metric] for p in group], [p['input_tokens'] / 1000 for p in group],
                   color=colors[version], marker=markers[version], s=110,
                   label=f'Strata {version}', zorder=3)
        for p in group:
            offset = (0, 17) if version == '0.1.41' else (0, -24)
            if p['input_tokens'] < 1000 and version == '0.1.42':
                offset = (0, -16)
            # The short-context total-time marks are close: spread their labels.
            if metric == 'total_s' and p['input_tokens'] < 1000:
                offset = (32, 17) if version == '0.1.41' else (32, -16)
            ax.annotate(f"{p[metric]:.2f} s", (p[metric], p['input_tokens'] / 1000),
                        xytext=offset, textcoords='offset points', ha='center',
                        fontsize=12, color=colors[version])
    ax.set_xlim(0, xmax)
    ax.set_ylim(-5, 50)
    ax.set_yticks([0.034, 16.384, 32.768, 43.244])
    ax.set_yticklabels(['34 tokens', '16K', '32K', '43,244 tokens'])
    ax.set_xlabel('Time (seconds) — lower is faster', labelpad=12)
    ax.set_title(title, fontsize=15, pad=16)
    ax.grid(axis='x', alpha=0.2)
    ax.axhline(32.768, color='#909090', lw=1, ls='--', alpha=0.5)
    ax.spines[['top', 'right']].set_visible(False)
axes[0].set_ylabel('Input context length', labelpad=12)
axes[1].annotate('32K GPU-resident window', (84, 32.768), xytext=(0, 5),
                 textcoords='offset points', ha='right', fontsize=10, color='#686868')
axes[1].legend(loc='center right', frameon=False, fontsize=12)
fig.suptitle('RTX 2080 · Strata 0.1.41 vs 0.1.42 · 192 output tokens', fontsize=17, y=0.98)
fig.text(0.5, 0.06, '34-token context: median of 2 runs per version. 43,244-token context: 1 run per version.',
         ha='center', fontsize=11)
fig.text(0.5, 0.02, 'Calibrated 128K chat config. Different prompt at each context size. No interpolation or unmeasured points.',
         ha='center', fontsize=10, color='#555555')
fig.tight_layout(rect=(0, 0.12, 1, 0.93))
for suffix in ('png', 'svg'):
    fig.savefig(results / f'strata-0141-vs-0142-context-time.{suffix}', dpi=180, facecolor='white')
print(json.dumps(points, indent=2))
