#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parent
rows=json.loads((root/'full-results.json').read_text())
by={(r['arm'],r['class']):r for r in rows}
summary={'prefill':[],'pi':[]}
def normalized(message):
 m=json.loads(json.dumps(message))
 for call in m.get('tool_calls',[]) or []:call.pop('id',None)
 return m
for r in rows:
 if r['class']=='pi-cart-bugfix':
  work=root/f"pi-work-{r['arm']}"
  row=dict(r);events=[]
  for line in (root/f"{r['arm']}.pi-session.jsonl").read_text().splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  row['tool_execution_starts']=sum(e.get('type')=='tool_execution_start' for e in events)
  summary['pi'].append(row);continue
 t=r['timings'];assert t['cache_n']==0,r
 baseline=by[('stock',r['class'])]
 row={'arm':r['arm'],'case':r['class'],'prompt_tokens':r['usage']['prompt_tokens'],'prefill_seconds':t['prompt_ms']/1000,'prefill_tokens_per_second':t['prompt_per_second'],'wall_seconds':r['wall_seconds'],'completion_tokens':r['usage']['completion_tokens'],'throughput_gain_percent':100*(t['prompt_per_second']/baseline['timings']['prompt_per_second']-1),'greedy_message_matches_stock':normalized(r['message'])==normalized(baseline['message'])}
 summary['prefill'].append(row)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
