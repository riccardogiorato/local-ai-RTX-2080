#!/usr/bin/env python3
"""Serial A/B on real coding-agent histories and an actual Pi bug-fix task."""
import copy,json,os,re,shutil,signal,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
SRC=REPO.parent/'strata-0145'
BASE=json.loads((SRC/'strata-q20-gsq-0145-p4096.json').read_text())
BODIES=['code-25k','code-100k']
ARMS=[('stock',str(ROOT/'strata-stock'),{}),('custom',str(SRC/'build-turing-0145/strata'),{'STRATA_SCORES_TURING':'2'}),('custom-suite',str(SRC/'build-turing-0145/strata'),{'STRATA_SCORES_TURING':'2','STRATA_SM75_PERF':'1'})]
results=[]
def save(): (ROOT/'full-results.json').write_text(json.dumps(results,indent=2)+'\n')
def logrows(arm):
 text=(ROOT/f'{arm}.engine.log').read_text(errors='replace')
 return [s for s in text.splitlines() if 'strata serve: prompt ' in s and 'tokens =' in s]
def run_pi(arm):
 master=REPO/'benchmarks/agentic-tasks/task1-js-bugfix';work=ROOT/f'pi-work-{arm}'
 shutil.copytree(master,work)
 env=os.environ.copy();env.update(PI_CODING_AGENT_DIR=str(ROOT/'pi-agent'),PI_OFFLINE='1')
 cmd=['/home/riccardogiorato/.local/share/mise/installs/pi/latest/pi/pi','--provider','kernel-bench','--model','local-model','--thinking','off','--mode','json','--no-session','--no-extensions','--no-mcp','--no-skills','--no-prompt-templates','--tools','read,bash,edit,write','-p',(work/'TASK.md').read_text()]
 start=len(logrows(arm));t=time.monotonic()
 with (ROOT/f'{arm}.pi-session.jsonl').open('w') as out,(ROOT/f'{arm}.pi-errors.log').open('w') as err:
  try:ret=subprocess.run(cmd,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=300).returncode
  except subprocess.TimeoutExpired:ret=124
 wall=time.monotonic()-t
 verify=subprocess.run(['bash','verify.sh'],cwd=work,capture_output=True,text=True,timeout=30)
 (ROOT/f'{arm}.verify.log').write_text(verify.stdout+verify.stderr)
 immutable=all((work/name).read_bytes()==(master/name).read_bytes() for name in ['TASK.md','verify.sh','test/cart.test.js'])
 row={'arm':arm,'class':'pi-cart-bugfix','wall_seconds':wall,'pi_exit':ret,'tests_pass':verify.returncode==0,'immutable_files_unchanged':immutable,'engine_summaries':logrows(arm)[start:]}
 return row
def main():
 for arm,exe,flags in ARMS:
  cfg=copy.deepcopy(BASE);cfg.update(exe=exe,host='127.0.0.1',port=8081,log=str(ROOT/f'{arm}.engine.log'))
  cfg['args'][cfg['args'].index('--prefill')+1]='auto:16384';cfg['env'].update(flags)
  config=ROOT/f'{arm}.json';config.write_text(json.dumps(cfg,indent=2)+'\n')
  slog=ROOT/f'{arm}.server.log';proc=None;log=None
  print(f'{time.ctime()} START {arm}',flush=True)
  if arm=='stock' and len(sys.argv)>1:
   pid=int(sys.argv[1]);print(f'Reusing existing benchmark server {pid}',flush=True)
  else:
   log=slog.open('w')
   proc=subprocess.Popen(['python3','-u','-m','serve.server','--engine','strata','--config',str(config),'--host','127.0.0.1','--port','8081'],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);pid=proc.pid
  try:
   deadline=time.monotonic()+1200
   while 'ready:' not in slog.read_text(errors='replace'):
    os.kill(pid,0)
    if proc is not None and proc.poll() is not None:raise RuntimeError(f'{arm} exited: {slog.read_text()[-1500:]}')
    if time.monotonic()>deadline:raise TimeoutError(f'{arm} boot')
    time.sleep(1)
   print(f'{time.ctime()} READY {arm}',flush=True)
   for label in BODIES:
    body=json.loads((ROOT/f'body-{label}.json').read_text());t=time.monotonic()
    req=urllib.request.Request('http://127.0.0.1:8081/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as r:answer=json.load(r)
    (ROOT/f'{arm}-{label}.response.json').write_text(json.dumps(answer,indent=2)+'\n')
    elog=(ROOT/f'{arm}.engine.log').read_text(errors='replace')
    timings=[s for s in elog.splitlines() if 'strata prefill timing:' in s and 'GPU timeline' in s]
    row={'arm':arm,'class':label,'wall_seconds':time.monotonic()-t,'engine_summary':logrows(arm)[-1],'timing':timings[-1] if timings else None,'message':answer['choices'][0]['message'],'usage':answer.get('usage'),'timings':answer.get('timings')}
    results.append(row);save();print(f'{time.ctime()} RESULT {json.dumps({k:v for k,v in row.items() if k not in ("message","timing")})}',flush=True)
   row=run_pi(arm);results.append(row);save();print(f'{time.ctime()} RESULT {json.dumps(row)}',flush=True)
  finally:
   try:os.killpg(pid,signal.SIGTERM)
   except ProcessLookupError:pass
   if proc is not None:
    try:proc.wait(timeout=15)
    except subprocess.TimeoutExpired:os.killpg(pid,signal.SIGKILL);proc.wait()
   if log is not None:log.close()
   time.sleep(3)
 print('DONE',flush=True)

if __name__ == "__main__":
 main()
