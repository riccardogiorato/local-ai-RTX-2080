#!/usr/bin/env python3
"""Check the custom scorer against the original on every real 121K-prompt call."""
import copy,json,os,re,signal,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parents[1].parent/'strata-0145'
deadline=time.monotonic()+1800
while not (ROOT/'stock-pi-rerun.log').exists() or 'REFERENCE PI RERUN DONE' not in (ROOT/'stock-pi-rerun.log').read_text():
 if time.monotonic()>deadline:raise TimeoutError('waiting for serial benchmark/Pi completion')
 time.sleep(2)
cfg=json.loads((ROOT/'custom.json').read_text());cfg['env']['STRATA_SCORES_TURING_CHECK']='1';cfg['log']=str(ROOT/'real-check.engine.log')
p=ROOT/'real-check.json';p.write_text(json.dumps(cfg,indent=2)+'\n')
with (ROOT/'real-check.server.log').open('w') as log:
 proc=subprocess.Popen(['python3','-u','-m','serve.server','--engine','strata','--config',str(p),'--host','127.0.0.1','--port','8081'],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  deadline=time.monotonic()+600
  while 'ready:' not in (ROOT/'real-check.server.log').read_text(errors='replace'):
   if proc.poll() is not None:raise RuntimeError('score-check server exited')
   if time.monotonic()>deadline:raise TimeoutError('score-check boot')
   time.sleep(1)
  print(time.ctime(),'READY: checking real scores',flush=True)
  body=json.loads((ROOT/'body-code-100k.json').read_text())
  req=urllib.request.Request('http://127.0.0.1:8081/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=1000) as r:answer=json.load(r)
  (ROOT/'real-check.response.json').write_text(json.dumps(answer,indent=2)+'\n')
  text=(ROOT/'real-check.engine.log').read_text()
  checks=[tuple(map(int,m)) for m in re.findall(r'Turing score check: (\d+) queries, (\d+) active blocks, (\d+) mismatches',text)]
  assert checks and all(n==0 for q,b,n in checks),checks
  row={'prompt_tokens':answer['usage']['prompt_tokens'],'checked_calls':len(checks),'active_blocks_range':[min(b for q,b,n in checks),max(b for q,b,n in checks)],'mismatches':sum(n for q,b,n in checks),'validation_timing_not_a_performance_sample':True}
  (ROOT/'real-score-validation.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
 finally:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=15)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
print('REAL SCORE VALIDATION DONE',flush=True)
