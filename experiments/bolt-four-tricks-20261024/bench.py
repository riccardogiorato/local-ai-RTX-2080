#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,time,urllib.request,sys
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
MODELS=pathlib.Path('/home/riccardogiorato/models')
IMAGE='ghcr.io/ggml-org/llama.cpp:server-cuda12-b11804@sha256:490d8cd8000203a3ab8fdfce14ef931e2aa85affd4dd4447bcc75f299f00fd9a'
TARGET='nemotron-bolt-e4b/NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf'
DFLASH='nemotron-bolt-e4b/dflash-NVIDIA-Nemotron-3.5-Bolt-E4B-Q8_0.gguf'
MTP='gemma-4-e4b-qat/gemma-4-E4B-it-qat-assistant-MTP-Q8_0.gguf'
SMALL='nemotron-bolt-e4b/experimental/dflash-Bolt-Q4_K_M-from-Q8.gguf'
proc=None
log_handle=None
monitor=None
monitor_log=None

def call(path,payload=None,timeout=600):
 req=urllib.request.Request('http://127.0.0.1:8080/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

def shell(args,**kw):return subprocess.run(args,check=True,**kw)
def stop():
 global proc,log_handle,monitor,monitor_log
 if proc is not None:
  proc.terminate()
  try:proc.wait(timeout=20)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
  proc=None
 if log_handle:log_handle.close();log_handle=None
 if monitor is not None:monitor.terminate();monitor.wait();monitor=None
 if monitor_log:monitor_log.close();monitor_log=None
 subprocess.run(['sudo','docker','rm','-f','bolt-serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def start(label,kind='draft-dflash',draft=DFLASH,depth=4,engine='docker',extra=()):
 global proc,log_handle,monitor,monitor_log
 power=float(subprocess.check_output(['nvidia-smi','--query-gpu=power.limit','--format=csv,noheader,nounits'],text=True).strip())
 if power!=165:raise RuntimeError('Power cap changed: '+str(power))
 stop()
 started=time.monotonic()
 monitor_log=(OUT/(label+'-telemetry.csv')).open('w')
 monitor=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,memory.used,power.draw,power.limit,utilization.gpu,temperature.gpu','--format=csv','-lms','500'],stdout=monitor_log,stderr=subprocess.DEVNULL)
 base='/models/' if engine=='docker' else str(MODELS)+'/'
 args=['--model',base+TARGET,'--alias','local-model','--host','127.0.0.1' if engine!='docker' else '0.0.0.0','--port','8080','--ctx-size','65536','--parallel','1','--n-gpu-layers','999','--flash-attn','on','--jinja','--no-warmup','--metrics']
 if kind!='none':args+=['--spec-type',kind,'--spec-draft-model',base+draft,'--spec-draft-n-max',str(depth)]
 args+=list(extra)
 if engine=='docker':
  cmd=['sudo','docker','run','--gpus','all','-p','8080:8080','-v',str(MODELS)+':/models:ro','-v',str((MODELS/'gemma-4-e4b-qat').resolve())+':/models/gemma-4-e4b-qat:ro','-d','--name','bolt-serve',IMAGE]+args
  shell(cmd,stdout=subprocess.DEVNULL)
 else:
  exe=f'/tmp/bolt-b11804-tricks/build-{engine}/bin/llama-server'
  cmd=[exe]+args
  log_handle=(OUT/(label+'-server.log')).open('w')
  proc=subprocess.Popen(cmd,stdout=log_handle,stderr=subprocess.STDOUT)
 (OUT/(label+'-config.json')).write_text(json.dumps({'command':cmd,'power_limit_w':165},indent=2)+'\n')
 for _ in range(120):
  try:
   if call('health',timeout=2).get('status')=='ok':
    config=json.loads((OUT/(label+'-config.json')).read_text())
    config['health_after_s']=time.monotonic()-started
    (OUT/(label+'-config.json')).write_text(json.dumps(config,indent=2)+'\n')
    print(label,'healthy',flush=True);return
  except Exception:pass
  if proc is not None and proc.poll() is not None:break
  if engine=='docker':
   state=subprocess.check_output(['sudo','docker','inspect','bolt-serve','--format','{{.State.Running}}'],text=True).strip()
   if state!='true':break
  time.sleep(2)
 raise RuntimeError(label+' failed startup')

def snapshot(label):
 if proc is None:
  with (OUT/(label+'-server.log')).open('w') as f:subprocess.run(['sudo','docker','logs','bolt-serve'],stdout=f,stderr=subprocess.STDOUT)
 (OUT/(label+'-gpu.txt')).write_text(subprocess.check_output(['nvidia-smi','--query-gpu=power.limit,memory.used,temperature.gpu','--format=csv'],text=True))

def record(label,phase,name,run,payload):
 t=time.monotonic();r=call('completion',payload);wall=time.monotonic()-t
 row={'label':label,'phase':phase,'name':name,'run':run,'warmup':run==0,'wall_s':wall,'response':r,'content_sha256':hashlib.sha256(r.get('content','').encode()).hexdigest()}
 with (OUT/(label+'.jsonl')).open('a') as f:f.write(json.dumps(row)+'\n')
 print(json.dumps({'label':label,'phase':phase,'name':name,'run':run,'timings':r.get('timings'),'wall_s':wall}),flush=True)
 return row

def decode(label):
 prompts={n:(ROOT/'benchmarks'/'prompts'/n).read_text() for n in ['code-continuation.txt','decode-isolation.txt']}
 prompts['prose-long']='Write a detailed essay of at least 900 words explaining how controlled experiments distinguish causation from correlation. Discuss confounding variables, random assignment, measurement error, replication, and a concrete gardening example. Use connected prose with no lists. Begin the essay now:\n'
 for name,p in prompts.items():
  for run in range(3):record(label,'decode',name,run,{'prompt':p,'n_predict':512 if name=='prose-long' else 256,'temperature':0,'seed':42,'cache_prompt':False,'samplers':['temperature']})

def prepare_prompts():
 # Fixed repository text, not a repeated-token workload. Retain exact token arrays.
 pieces=[]
 for p in sorted((ROOT/'recipes').glob('*.md')):
  pieces.append('\nDocument: '+p.name+'\n'+p.read_text())
 corpus=''.join(pieces)
 head='Reference documents follow. Remember the audit code 724193.\n'
 suffix='\nQuestion: What is the audit code stated at the start? Reply with only that six-digit code.\nAnswer:'
 tokens=call('tokenize',{'content':head+corpus,'add_special':True})['tokens'];tail=call('tokenize',{'content':suffix,'add_special':False})['tokens']
 assert len(tokens)>32768
 prompts={str(n):tokens[:n-len(tail)]+tail for n in [2048,8192,32768]}
 (OUT/'prefill-prompts.json').write_text(json.dumps(prompts))

def prefill(label):
 prompts=json.loads((OUT/'prefill-prompts.json').read_text())
 for n,p in prompts.items():
  for run in range(3):
   row=record(label,'prefill',n,run,{'prompt':p,'n_predict':32,'temperature':0,'seed':42,'cache_prompt':False,'samplers':['temperature']})
   print('needle',n,'724193' in row['response'].get('content',''),flush=True)

def restore():
 stop()
 with (OUT/'restore.log').open('a') as f:
  shell(['bash',str(ROOT/'experiments/nemotron-bolt-e4b-20261023/run-bolt.sh'),'dflash-d4'],env=dict(os.environ,BOLT_CTX='65536',BOLT_IMAGE=IMAGE),stdout=f,stderr=subprocess.STDOUT)

if __name__=='__main__':
 configs={
 'baseline':{},'mtp-d2':{'kind':'draft-mtp','draft':MTP,'depth':2},'mtp-d3':{'kind':'draft-mtp','draft':MTP,'depth':3},
 'draft-kvq8':{'extra':['--spec-draft-type-k','q8_0','--spec-draft-type-v','q8_0']},
 'draft-q4':{'draft':SMALL},'native-default':{'engine':'default'},'native-cublas':{'engine':'cublas'}}
 try:
  for label in sys.argv[1:]:
   try:
    start(label,**configs[label])
    decode(label)
    if label in ['baseline','native-default','native-cublas']:
     if not (OUT/'prefill-prompts.json').exists():prepare_prompts()
     prefill(label)
    snapshot(label)
   except Exception as e:
    snapshot(label)
    (OUT/(label+'-error.txt')).write_text(repr(e)+'\n')
    print('ERROR',label,repr(e),flush=True)
 finally:restore()
