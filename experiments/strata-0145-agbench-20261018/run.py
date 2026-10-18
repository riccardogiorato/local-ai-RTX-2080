#!/usr/bin/env python3
"""Matched Strata v0.1.45 stock/optimized full AG-Bench v2.2 and standard speed probes."""
import hashlib,json,os,re,shutil,signal,socket,subprocess,sys,threading,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
SRC=REPO.parent/'strata-0145'
PI=Path('/home/riccardogiorato/.local/share/mise/installs/pi/latest/pi/pi').resolve()
PORT=8083
SOURCE=REPO/'benchmarks/agentic-tasks'
MASTER=ROOT/'pristine-tasks'
BASE=json.loads((REPO/'recipes/strata-configs/strata-q20-gsq-0145-tailnet.json').read_text())
ARMS=[('stock',REPO/'experiments/rtx2080-prefill-20261018/strata-stock',{}),('optimized',SRC/'build-turing-0145/strata',{'STRATA_SCORES_TURING':'2','STRATA_SM75_PERF':'1'})]
CAP=900
TASKS=sorted(p.name for p in SOURCE.glob('task*') if p.is_dir())
assert len(TASKS)==11,TASKS

def manifest(base):
 out={}
 for p in base.rglob('*'):
  if 'node_modules' in p.parts or '__pycache__' in p.parts or '.git' in p.parts:continue
  if p.is_symlink():out[str(p.relative_to(base))]='link:'+os.readlink(p)
  elif p.is_file():out[str(p.relative_to(base))]=hashlib.sha256(p.read_bytes()).hexdigest()
 return out

GOLD=manifest(SOURCE)
(ROOT/'original-task-manifest.json').write_text(json.dumps(GOLD,indent=2)+'\n')
shutil.copytree(SOURCE,MASTER,symlinks=True,ignore=shutil.ignore_patterns('node_modules','__pycache__','.git'))
agentdir=ROOT/'pi-agent';agentdir.mkdir()
model={'id':'local-model','name':'Strata matched AG-Bench','reasoning':False,'input':['text'],'contextWindow':131072,'maxTokens':32768,'cost':{'input':0,'output':0,'cacheRead':0,'cacheWrite':0},'samplingParams':{'temperature':0,'seed':42},'compat':{'supportsStore':False,'supportsDeveloperRole':False,'supportsReasoningEffort':False,'maxTokensField':'max_tokens'}}
(agentdir/'models.json').write_text(json.dumps({'providers':{'llamacpp-local':{'api':'openai-completions','baseUrl':f'http://127.0.0.1:{PORT}/v1','apiKey':'local-benchmark','models':[model]}}},indent=2)+'\n')
(agentdir/'settings.json').write_text(json.dumps({'compaction':{'enabled':False},'retry':{'enabled':False}})+'\n')
wrapper=ROOT/'pi-wrapper';wrapper.write_text('#!/bin/bash\nexec '+str(PI)+' --no-extensions --no-mcp --no-skills --no-prompt-templates --thinking off "$@"\n');wrapper.chmod(0o755)
env=os.environ.copy();env.update(PI_BIN=str(wrapper),PI_CODING_AGENT_DIR=str(agentdir),PI_OFFLINE='1',WARM_TIMEOUT='90')
for k in ('TASK_RE','WARM_BYPASS','STRATA_SCORES_TURING','STRATA_SM75_PERF','STRATA_SCORES_TURING_CHECK'):env.pop(k,None)
script=(REPO/'benchmarks/agentic-bench.sh').read_text()
script=re.sub(r'^BENCH_DIR=.*$',f'BENCH_DIR="{REPO / "benchmarks"}"',script,flags=re.M)
script=re.sub(r'^TASKS_DIR=.*$',f'TASKS_DIR="{MASTER}"',script,flags=re.M)
# Freeze the established harness while avoiding its destructive git restore. The
# immutable source manifest is checked by this controller before and after each arm.
script=re.sub(r'restore_master_if_dirty\(\) \{.*?^\}', 'restore_master_if_dirty() { :; }',script,flags=re.S|re.M)
a=script.index('for i in $(seq 1 90); do');b=script.index('\ndone',a)+len('\ndone')
script=script[:a]+'# Loaded readiness was verified by the controller for this Strata API.\n'+script[b:]
script=script.replace('localhost:8080',f'localhost:{PORT}').replace('127.0.0.1:8080',f'127.0.0.1:{PORT}')
# Keep a verifier log instead of throwing it away.
script=script.replace('bash verify.sh >/dev/null 2>&1','bash verify.sh > "$work/verify.log" 2>&1')
# Capture task8 directory identity before Pi is allowed to repair its environment.
needle='  local t0=$SECONDS'
script=script.replace(needle,'  if [ "$task_name" = "task8-tb-broken-python" ]; then stat -c %i "$work/protected/venv" > "'+str(ROOT)+'/${LABEL}.task8-inode.txt"; fi\n'+needle)
frozen=ROOT/'agentic.frozen.sh';frozen.write_text(script)
metadata={'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'pi_executable':str(PI),'pi_version':subprocess.check_output([str(PI),'--version'],env=env,text=True).strip(),'tasks':TASKS,'cap_seconds':CAP,'model_metadata':model,'original_harness_sha256':hashlib.sha256((REPO/'benchmarks/agentic-bench.sh').read_bytes()).hexdigest(),'frozen_harness_sha256':hashlib.sha256(script.encode()).hexdigest(),'stock_executable':str(ARMS[0][1]),'optimized_executable':str(ARMS[1][1]),'storage':'same verified NVMe GGUF files, canonical model alias','historical_comparison_limit':'Pi version changed; same-day matched arms are the primary comparison.'}
(ROOT/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
state={'phase':'starting','arms':{},'complete':False}
def save(): (ROOT/'results.json').write_text(json.dumps(state,indent=2)+'\n')
def log(message):print(time.strftime('%H:%M:%S')+' '+message,flush=True)
def protect_snapshot():
 assert manifest(SOURCE)==GOLD,'Original task sources changed during run; no automatic restore performed.'

def start(arm,exe,flags,phase):
 cfg=json.loads(json.dumps(BASE));cfg.update(exe=str(exe),host='127.0.0.1',port=PORT,log=str(ROOT/f'{arm}-{phase}.engine.log'))
 cfg['env']={k:v for k,v in cfg.get('env',{}).items() if k not in ('STRATA_SCORES_TURING','STRATA_SM75_PERF','STRATA_SCORES_TURING_CHECK','STRATA_TRACE','STRATA_PREFILL_TIMING')};cfg['env'].update(flags)
 path=ROOT/f'{arm}-{phase}.config.json';path.write_text(json.dumps(cfg,indent=2)+'\n')
 output=(ROOT/f'{arm}-{phase}.server.log').open('w')
 proc=subprocess.Popen([sys.executable,'-u','-m','serve.server','--engine','strata','--config',str(path),'--host','127.0.0.1','--port',str(PORT)],cwd=SRC,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
 t=time.monotonic();deadline=t+900
 while True:
  if proc.poll() is not None:raise RuntimeError(f'{arm} server exited')
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=2) as r:health=json.load(r)
   if health.get('loaded'):break
  except (OSError,ValueError):pass
  if time.monotonic()>deadline:raise TimeoutError('server boot')
  time.sleep(1)
 log(f'READY {arm} {phase}, load {time.monotonic()-t:.1f}s');return proc,output

def stop(proc,output):
 try:os.killpg(proc.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:proc.wait(timeout=15)
 except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 output.close();time.sleep(2)

def audit(arm,label):
 files=sorted((REPO/'benchmarks/results').glob(label+'-*.jsonl'));assert files,label
 raw=[json.loads(l) for l in files[-1].read_text().splitlines()]
 assert len(raw)==11 and {r['task'] for r in raw}==set(TASKS),(len(raw),raw)
 out=[]
 for row in raw:
  name=row['task'];work=Path('/tmp/agentic-run')/label/name;master=MASTER/name
  protected=['TASK.md','verify.sh','tests','test','docs','wheels']
  if name!='task8-tb-broken-python':protected.append('protected')
  protected += {'task2-react-fix':['render-check.mjs','package.json'],'task4-python-bugfix':['test_metrics.py'],'task5-js-to-ts':['tsconfig.json'],'task9-tb-analyze-access-logs':['access_log'],'task10-tb-bank-trans-filter':['data/bank_transactions.csv']}.get(name,[])
  bad=[]
  for rel in protected:
   p=master/rel
   if p.is_dir():
    a,b=manifest(p),manifest(work/rel)
    if a!=b:bad.append(rel)
   elif p.exists() and (not (work/rel).exists() or p.read_bytes()!=(work/rel).read_bytes()):bad.append(rel)
  if name=='task8-tb-broken-python':
   inode=int((ROOT/f'{label}.task8-inode.txt').read_text())
   if (work/'protected/venv').stat().st_ino!=inode:bad.append('venv directory recreated')
  events=[]
  for line in (work/'pi-session.jsonl').read_text().splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  tools=sum(e.get('type')=='tool_execution_start' for e in events)
  errors=[e['message'].get('errorMessage') for e in events if e.get('type')=='message_end' and e.get('message',{}).get('role')=='assistant' and e['message'].get('stopReason')=='error']
  passed=bool(row['passed'] and not bad and tools>0 and not errors)
  rec={**row,'passed':passed,'raw_passed':row['passed'],'actual_tool_calls':tools,'immutable_violations':bad,'agent_errors':errors,'workdir':str(work)};out.append(rec)
  for f in ('pi-session.jsonl','pi-errors.log','verify.log'):
   src=work/f
   if src.exists():shutil.copy2(src,ROOT/f'{arm}.{name}.{f}')
 stats=[]
 pattern=r'strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms .*?, (\d+) generated in (\d+) ms'
 for m in re.finditer(pattern,(ROOT/f'{arm}-ag.engine.log').read_text()):stats.append(list(map(int,m.groups())))
 return {'tasks':out,'passed':sum(r['passed'] for r in out),'total':11,'task_wall_seconds':sum(r['wall_s'] for r in out),'generated_tokens':sum(s[4] for s in stats),'decode_seconds':sum(s[5] for s in stats)/1000,'prompt_read_tokens':sum(s[2] for s in stats),'prompt_seconds':sum(s[3] for s in stats)/1000,'raw_result':str(files[-1]),'engine_requests':len(stats)}

try:
 for arm,exe,flags in ARMS:
  protect_snapshot();state['phase']='AG-Bench '+arm;save();log(f'START full AG-Bench {arm}, 11 tasks x {CAP}s cap')
  label=f'strata-0145-{arm}-turing-v22-20261018'
  proc,output=start(arm,exe,flags,'ag')
  try:
   with (ROOT/f'{arm}.runner.log').open('w') as runlog:
    subprocess.run(['bash',str(frozen),label,str(CAP)],cwd=REPO,env=env,stdout=runlog,stderr=subprocess.STDOUT,check=True)
   state['arms'][arm]={'agbench':audit(arm,label)};save();log(f"DONE {arm}: {state['arms'][arm]['agbench']['passed']}/11 in {state['arms'][arm]['agbench']['task_wall_seconds']}s")
  finally:stop(proc,output)
  protect_snapshot()
 # Fresh server for each speed arm, avoiding dependence on preceding task trajectories.
 for arm,exe,flags in ARMS:
  state['phase']='standard speed probes '+arm;save();proc,output=start(arm,exe,flags,'speed')
  try:
   with (ROOT/f'{arm}.speed-runner.log').open('w') as logf:
    subprocess.run([sys.executable,str(SRC/'tools/strata_bench.py'),'--url',f'http://127.0.0.1:{PORT}','--runs','3','--long','--out',str(ROOT/f'{arm}-speed'),'--quiet'],stdout=logf,stderr=subprocess.STDOUT,check=True,timeout=1800)
   results=next((ROOT/f'{arm}-speed').rglob('results.json'));state['arms'][arm]['standard_speed_result']=str(results);save()
  finally:stop(proc,output)
 state['phase']='complete';state['complete']=True;save();log('ALL BENCHMARKS COMPLETE')
finally:protect_snapshot()
