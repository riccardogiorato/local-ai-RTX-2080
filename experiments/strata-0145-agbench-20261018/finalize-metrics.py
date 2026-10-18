#!/usr/bin/env python3
"""Remove the harness warmup from suite engine counters; retain original totals."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=ROOT/'results.json';d=json.loads(p.read_text());assert d['complete'],'Wait for controller completion'
pattern=r'strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms .*?, (\d+) generated in (\d+) ms'
for arm,values in d['arms'].items():
 a=values['agbench']
 if a.get('excludes_warmup'):continue
 assert 'warm-up attempt 1: ok' in (ROOT/f'{arm}.runner.log').read_text()
 stats=[list(map(int,m.groups())) for m in re.finditer(pattern,(ROOT/f'{arm}-ag.engine.log').read_text())]
 assert len(stats)==a['engine_requests'] and sum(s[4] for s in stats)==a['generated_tokens']
 a['task8_baseline_already_passes']=True
 a['task_wall_seconds_excluding_task8']=sum(t['wall_s'] for t in a['tasks'] if not t['task'].startswith('task8-'))
 a['passed_excluding_task8']=sum(t['passed'] for t in a['tasks'] if not t['task'].startswith('task8-'))
 a['including_warmup']={k:a[k] for k in ('generated_tokens','decode_seconds','prompt_read_tokens','prompt_seconds','engine_requests')}
 a['excluded_warmup']={'prompt_tokens':stats[0][0],'generated_tokens':stats[0][4],'decode_seconds':stats[0][5]/1000}
 stats=stats[1:];a.update(generated_tokens=sum(s[4] for s in stats),decode_seconds=sum(s[5] for s in stats)/1000,prompt_read_tokens=sum(s[2] for s in stats),prompt_seconds=sum(s[3] for s in stats)/1000,engine_requests=len(stats),excludes_warmup=True)
 # The task8 inode check is supplemented by reviewable tool-command evidence.
 commands=[]
 for line in (ROOT/f'{arm}.task8-tb-broken-python.pi-session.jsonl').read_text().splitlines():
  e=json.loads(line)
  if e.get('type')=='tool_execution_start':commands.append({'tool':e['toolName'],'args':e.get('args',{})})
 (ROOT/f'{arm}.task8-repair-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
p.write_text(json.dumps(d,indent=2)+'\n');print('Removed one verified harness warmup per arm')
