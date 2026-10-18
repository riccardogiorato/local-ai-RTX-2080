#!/usr/bin/env python3
"""Rerun the reference Pi smoke test after correcting its isolated API base URL."""
import importlib.util,json,os,shutil,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
while not (ROOT/'full-runner.log').exists() or not (ROOT/'full-runner.log').read_text().rstrip().endswith('DONE'):time.sleep(2)
archive=ROOT/'discarded-transport';archive.mkdir(exist_ok=True)
for name in ('stock.pi-session.jsonl','stock.pi-errors.log','stock.verify.log','pi-work-stock'):
 p=ROOT/name
 if p.exists():shutil.move(p,archive/name)
rows=json.loads((ROOT/'full-results.json').read_text());discarded=[r for r in rows if r['arm']=='stock' and r['class']=='pi-cart-bugfix'];(archive/'results.json').write_text(json.dumps(discarded,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('fullbench',ROOT/'run-full.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with (ROOT/'stock-pi.server.log').open('w') as log:
 proc=subprocess.Popen(['python3','-u','-m','serve.server','--engine','strata','--config',str(ROOT/'stock.json'),'--host','127.0.0.1','--port','8081'],cwd=module.SRC,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  deadline=time.monotonic()+600
  while 'ready:' not in (ROOT/'stock-pi.server.log').read_text(errors='replace'):
   if proc.poll() is not None:raise RuntimeError('stock Pi server exited')
   if time.monotonic()>deadline:raise TimeoutError('stock Pi server boot')
   time.sleep(1)
  row=module.run_pi('stock');print(json.dumps(row),flush=True)
  assert row['engine_summaries'],'Pi failed before inference'
  rows=[r for r in rows if not(r['arm']=='stock' and r['class']=='pi-cart-bugfix')];rows.append(row);(ROOT/'full-results.json').write_text(json.dumps(rows,indent=2)+'\n')
 finally:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=15)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
print('REFERENCE PI RERUN DONE',flush=True)
