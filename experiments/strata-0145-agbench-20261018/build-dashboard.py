#!/usr/bin/env python3
import json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
b=json.loads((ROOT/'results.json').read_text());data={'phase':b['phase'],'complete':b['complete'],'arms':{},'contended':False,'fixture_limitations':['Task 8 already passes its verifier before agent work; optimized agent also read stock logs; excluded from the time-change headline.']}
monitor=ROOT/'resource-samples.jsonl'
if monitor.exists():
 for line in monitor.read_text().splitlines():
  try:data['contended'] |= bool(json.loads(line)['external_builds'])
  except (ValueError,KeyError):pass
for arm,values in b['arms'].items():
 out={};a=values.get('agbench')
 if a:
  a=json.loads(json.dumps(a));a['passed_excluding_task8']=sum(t['passed'] for t in a['tasks'] if not t['task'].startswith('task8-'));a['task_wall_seconds_excluding_task8']=sum(t['wall_s'] for t in a['tasks'] if not t['task'].startswith('task8-'));a['actual_tool_calls']=sum(t['actual_tool_calls'] for t in a['tasks']);a['decode_tps']=a['generated_tokens']/a['decode_seconds'] if a['decode_seconds'] else None;out['agbench']=a
 if values.get('standard_speed_result'):
  r=json.loads(Path(values['standard_speed_result']).read_text())['results'];out['speed']={'short_decode':r['chat']['decode_tps']['median'],'prefill_4k':r['prompts']['4K']['prompt_tps']['median'],'prefill_16k':r['prompts']['16K']['prompt_tps']['median'],'prefill_32k':r['prompts']['32K']['prompt_tps']['median'],'agent_ttft':r['agent']['turn_ttft_s']['median'],'agent_decode':r['agent']['turn_decode_tps']['median']}
 data['arms'][arm]=out
raw=json.dumps(data,indent=2)
(REPO/'benchmarks/strata-0145-results.json').write_text(raw+'\n')
html=(ROOT/'dashboard.template.html').read_text().replace('__BENCH_DATA__',raw.replace('<','\\u003c'))
(REPO/'benchmarks/index.html').write_text(html)
print('Dashboard updated:',data['phase'])
