#!/usr/bin/env python3
"""Report every tool command naming another retained AG-Bench work directory."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out=[]
for arm in ('stock','optimized'):
 label=f'strata-0145-{arm}-turing-v22-20261018'
 for p in ROOT.glob(f'{arm}.task*.pi-session.jsonl'):
  for line in p.read_text().splitlines():
   e=json.loads(line)
   if e.get('type')!='tool_execution_start':continue
   args=str(e.get('args',{}));foreign=sorted(set(x for x in re.findall(r'/tmp/agentic-run/([\w.-]+)',args) if x!=label))
   if foreign:out.append({'arm':arm,'task':p.name.split('.')[1],'foreign_runs':foreign,'tool':e['toolName'],'args':e.get('args')})
for item in out:
 if item['task']=='task5-js-to-ts' and item['foreign_runs']==['out']:
  item['review']='Own temporary TypeScript output directory, created and deleted by this task; not another run.'
 elif item['arm']=='stock' and item['task']=='task8-tb-broken-python':
  item['review']='String replacement of a stale launcher path; this command does not read that old run.'
 else:item['review']='Task 8 references/inspects retained run artifacts; task 8 excluded from headline timing.'
(ROOT/'cross-run-access-audit.json').write_text(json.dumps({'method':'Tool-argument references to another /tmp/agentic-run/<label>; not an OS sandbox or exhaustive information-flow proof.','findings':out},indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='args'} for r in out],indent=2))
