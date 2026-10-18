#!/usr/bin/env python3
"""Export the dashboard's measured data as an SVG and PNG, without a browser."""
import json,subprocess
from html import escape
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
d=json.loads((REPO/'benchmarks/strata-0145-results.json').read_text())
W,H=1440,1120
s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="1440" height="1120" fill="#080c12"/>']
fg='#edf4fb';muted='#9caec3';green='#75e6b2';gray='#778ba5';red='#ff938f'
def text(x,y,t,size=15,color=fg,weight='400',anchor='start'):
 s.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans, sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(t))}</text>')
def rect(x,y,w,h,color,r=5):s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}"/>')
def num(n,d=1):return f'{n:,.{d}f}' if isinstance(n,(int,float)) else 'Pending'
def arm(k):return d['arms'].get(k,{})
a=arm('stock').get('agbench');b=arm('optimized').get('agbench')
text(48,48,'RTX 2080 / BENCH LAB',15,muted,'700');text(1392,48,'2026-10-18 · '+d['phase'],13,muted,anchor='end')
text(48,112,'Strata, measured end to end.',40,weight='700')
text(48,148,'v0.1.45 stock vs Turing opt-ins · Flash-Next 125B Q2_0 · RTX 2080 8 GiB · Pi 1.3.0',16,muted)
text(48,176,'128K context / int8 KV / 32K resident · identical NVMe files · AG-Bench v2.2 · 900 s/task',14,muted)
cards=[('Stock verifier passes',f"{a['passed']} / 11" if a else 'Pending',f"{a['task_wall_seconds']:,} s task wall" if a else 'Awaiting audited suite'),('Optimized verifier passes',f"{b['passed']} / 11" if b else 'Pending',f"{b['task_wall_seconds']:,} s task wall" if b else 'Awaiting audited suite')]
if a and b and a['passed_excluding_task8']==b['passed_excluding_task8']==10 and not d['contended']:
 change=100*(b['task_wall_seconds_excluding_task8']/a['task_wall_seconds_excluding_task8']-1);cards.append(('10-task wall change',f'{change:+.1f}%','Excludes task 8; one suite per arm'))
else:cards.append(('10-task wall change','See outcomes' if a and b else 'Pending','Success and time shown together'))
sp=arm('optimized').get('speed',{}).get('prefill_32k');cards.append(('32K prompt throughput',num(sp,0)+' tok/s' if sp else 'Pending','Median of three fixed probes'))
for i,(label,value,note) in enumerate(cards):
 x=48+i*342;rect(x,210,326,140,'#101720',10);text(x+20,241,label,13,muted);text(x+20,292,value,29,green if i==1 else fg,'700');text(x+20,325,note,12,muted)
rect(48,374,816,600,'#101720',10);rect(884,374,508,600,'#101720',10)
text(70,411,'Time per task',21,weight='700');text(70,436,'Seconds · lower is better · failed tasks shown in red',12,muted)
rect(594,402,10,10,gray);text(612,412,'Stock',12,muted);rect(693,402,10,10,green);text(711,412,'Optimized',12,muted)
names=['Cart bugfix','React contract','Dependency upgrade','Python metrics','TypeScript migration','Pagination','ADR gateway','Python environment*','Access-log analysis','Bank filtering','Seating constraints']
def task(ag,n):return next((r for r in ag['tasks'] if int(r['task'][4:].split('-')[0])==n),None) if ag else None
maxwall=max([r['wall_s'] for ag in (a,b) if ag for r in ag['tasks']]+[1])
for n,name in enumerate(names,1):
 y=475+(n-1)*42;text(70,y+9,f'{n:02}  {name}',12,muted)
 for j,ag in enumerate((a,b)):
  r=task(ag,n);yy=y-4+j*13;rect(267,yy,500,7,'#192330',3)
  if r:rect(267,yy,max(1,500*r['wall_s']/maxwall),7,(gray if j==0 else green) if r['passed'] else red,3)
  text(835,yy+8,str(r['wall_s'])+' s' if r else '—',11,muted,anchor='end')
text(906,411,'Standard speed probes',21,weight='700');text(906,436,'Fresh server per arm · 3 repetitions · medians',12,muted)
text(1185,473,'Stock',12,muted,anchor='end');text(1370,473,'Optimized',12,muted,anchor='end')
for i,(label,key,unit) in enumerate([('Short decode','short_decode','tok/s'),('4K prefill','prefill_4k','tok/s'),('16K prefill','prefill_16k','tok/s'),('32K prefill','prefill_32k','tok/s'),('Agent first token','agent_ttft','s'),('Agent decode','agent_decode','tok/s')]):
 y=509+i*39;text(906,y,label,13,muted)
 for x,k in ((1185,'stock'),(1370,'optimized')):
  v=arm(k).get('speed',{}).get(key);text(x,y,num(v)+(' '+unit if v is not None else ''),13,fg,anchor='end')
text(906,778,'Agent work performed',16,weight='700')
for i,(label,key) in enumerate([('Wall excluding task 8 (s)','task_wall_seconds_excluding_task8'),('Generated tokens','generated_tokens'),('Tool executions','actual_tool_calls'),('Aggregate decode (tok/s)','decode_tps')]):
 y=815+i*36;text(906,y,label,12,muted);text(1370,y,num(a.get(key) if a else None,1 if key=='decode_tps' else 0)+' → '+num(b.get(key) if b else None,1 if key=='decode_tps' else 0),13,anchor='end')
text(48,1009,'One paired suite measures observed task time. Different agent trajectories can change token and tool work.',13,muted)
text(48,1034,'*Task 8 was already green and its optimized agent read stock logs; excluded from the time-change headline.',13,muted)
text(48,1068,'Interactive details: benchmarks/index.html · Data: benchmarks/strata-0145-results.json',12,green)
text(48,1092,'Method and raw evidence: experiments/strata-0145-agbench-20261018/README.md',12,muted)
s.append('</svg>');target=REPO/'benchmarks/dashboard.svg';target.write_text('\n'.join(s)+'\n')
subprocess.run(['rsvg-convert',str(target),'-o',str(REPO/'benchmarks/dashboard.png')],check=True)
print('Exported measured SVG and PNG')
