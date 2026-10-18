#!/usr/bin/env python3
"""v2: one pinned Strata server, context ladder, live power walk, finally cleanup.
Usage: strata-power-sweep.py SERVE_LOG OUT_JSONL --config CHAT_CONFIG --server-root STRATA_CHECKOUT
The standing config is read-only; the run stores a local-only copy beside OUT_JSONL.
"""
import argparse,glob,hashlib,json,os,re,signal,subprocess,sys,threading,time,urllib.request
from pathlib import Path
LIMITS=[225,190,165,145,125,145,165,190,225]
LINE=re.compile(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\)")
SHORT=["Write a Python function that merges two sorted lists, with a docstring and three tests.","Explain in plain words how a hash map handles collisions, with a small example.","Write a bash script that finds the ten largest files under a directory and prints their sizes."]
REPO=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def command(args):return subprocess.check_output(args,text=True).strip()
def set_power(w):return command(['sudo','-n','nvidia-smi','-pl',str(w)])
def quiet():
 rows=command(['ps','-eo','pid,comm,args','--no-headers']);bad=[]
 for line in rows.splitlines():
  parts=line.split(None,2)
  if len(parts)<3:continue
  pid,name,args=parts
  if name in {'nvcc','ninja','cc1plus','cc1','rustc','wasm-opt','ps2run','cmake','make'} or (name.startswith('node') and re.search(r'\b(vite|next dev|webpack.*serve)\b',args)):bad.append({'pid':int(pid),'name':name})
 if bad:raise RuntimeError('Quiet-box guard: '+json.dumps(bad))
 return {'loadavg':Path('/proc/loadavg').read_text().strip(),'mem_available_kib':int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])}
def http(url,body=None,timeout=1800):
 req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

class Monitor:
 def __init__(self,root):self.root=root;self.samples=[];self.pcie=[];self.procs=[];self.threads=[];self.error=None;self.done=threading.Event()
 def start(self):
  def read(args,kind,cols):
   proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);self.procs.append(proc)
   with (self.root/(kind+'-samples.jsonl')).open('w') as f:
    for line in proc.stdout:
     if line.startswith('#') or not line.strip():continue
     try:
      vals=[float(x) for x in (line.split(',') if kind=='gpu' else line.split()[1:])]
      if len(vals)!=len(cols):continue
      row={'time':time.time(),**dict(zip(cols,vals))};getattr(self,'samples' if kind=='gpu' else 'pcie').append(row);f.write(json.dumps(row)+'\n');f.flush()
     except ValueError:continue
  for args,kind,cols in [(['nvidia-smi','--query-gpu=power.draw,clocks.sm,temperature.gpu,utilization.gpu','--format=csv,noheader,nounits','-lms','200'],'gpu',['watts','sm_mhz','temp_c','gpu_util']),(['nvidia-smi','dmon','-s','t','-d','1'],'pcie',['rx_mb_s','tx_mb_s'])]:
   t=threading.Thread(target=read,args=(args,kind,cols),daemon=True);t.start();self.threads.append(t)
  def guard():
   while not self.done.wait(2):
    try:quiet()
    except Exception as e:self.error=str(e)
  t=threading.Thread(target=guard,daemon=True);t.start();self.threads.append(t)
 def window(self,t0,t1):
  rows=[x for x in self.samples if t0<=x['time']<=t1];pci=[x for x in self.pcie if t0<=x['time']<=t1]
  if not rows:return None
  out={'samples':len(rows)}
  for k in ('watts','sm_mhz','temp_c','gpu_util'):
   v=[r[k] for r in rows];out[k]=round(sum(v)/len(v),2);out[k+'_range']=[min(v),max(v)]
  if pci:
   for k in ('rx_mb_s','tx_mb_s'):
    v=[r[k] for r in pci];out[k]=round(sum(v)/len(v),2);out[k+'_range']=[min(v),max(v)]
  return out
 def close(self):
  self.done.set()
  for p in self.procs:
   if p.poll() is None:p.terminate()
  for p in self.procs:
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:p.kill();p.wait()
  for t in self.threads:t.join(timeout=5)

class Workloads:
 def __init__(self,cfg,root,server_root):
  sys.path.insert(0,str(server_root/'tools'));import strata_tokenizer as ST
  p=Path(cfg['tokenizer']);vocab=json.loads((p/'vocab.json').read_text());tokens=[None]*len(vocab)
  for token,index in vocab.items():tokens[index]=token
  self.tok=ST.Tokenizer(tokens,(p/'merges.txt').read_text().split('\n'),json.loads((p/'token_type.json').read_text()))
  chunks=[];sources=[]
  for base in (REPO,server_root):
   files=command(['git','-C',str(base),'ls-files']).splitlines()
   for rel in files:
    p=base/rel
    if p.suffix not in ('.md','.py','.cpp','.cu','.h'):continue
    if any(part in p.parts for part in ('experiments','results','agentic-tasks','vendor','third_party')):continue
    if not p.is_file() or p.stat().st_size>200000:continue
    text=p.read_text(errors='replace');chunks.append('\n\nSource: '+rel+'\n'+text);sources.append({'repo':str(base),'path':rel,'sha256':sha(p)})
  corpus=''.join(chunks);ids=self.tok.encode(corpus);assert len(ids)>140000,len(ids)
  # Fixed real prose/code, never a repeated-word synthetic context.
  self.text=self.tok.decode(ids[:150000]);self.ids=self.tok.encode(self.text)
  (root/'corpus.txt').write_text(self.text);(root/'corpus-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
 def count(self,text):return len(self.tok.encode('<|im_start|>user\n'+text+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n',parse_special=True))
 def make(self,target,nonce):
  needle='cobalt-'+hashlib.sha256(nonce.encode()).hexdigest()[:12]
  prefix='Unique document '+nonce+'.\nRead this engineering archive and remember its archive key.\n'
  marker='\nARCHIVE KEY: '+needle+'\n'
  suffix='\nReturn the exact ARCHIVE KEY first. Then write a detailed annotated Python implementation of an LRU cache, including tests and explanation. Continue for at least 400 words.\n'
  # Calibrate by tokenizing the complete chat template, then verify against the engine prompt_n.
  n=target-150
  for _ in range(8):
   left=self.tok.decode(self.ids[:int(target*.10)])
   right=self.tok.decode(self.ids[int(target*.10):n])
   text=prefix+left+marker+right+suffix;actual=self.count(text)
   if abs(actual-target)<=3:break
   n+=target-actual
  depth=len(self.tok.encode(prefix+left))/actual
  assert abs(actual-target)<=8,(actual,target)
  return text,needle,actual,depth

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('serve_log',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--config',type=Path,required=True);ap.add_argument('--server-root',type=Path,required=True);ap.add_argument('--cooldown',type=int,default=60);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
 a.out=a.out.resolve();a.serve_log=a.serve_log.resolve();root=a.out.with_suffix('');root.mkdir(parents=True,exist_ok=True)
 if a.out.exists():raise FileExistsError('Refusing to append a second server session to '+str(a.out))
 cfg=json.loads(a.config.read_text());original_config_sha=sha(a.config);pin=dict(cfg);pin.update(host='127.0.0.1',port=8080,log=str(a.serve_log));pinned=root/'pinned-config.json';pinned.write_text(json.dumps(pin,indent=2)+'\n')
 exe=Path(cfg['exe']);build_root=exe.parent.parent
 weights={}
 for flag in ('--native','--ple-gguf','--pack','--mtp','--expert-profile'):
  if flag in cfg['args']:
   raw=cfg['args'][cfg['args'].index(flag)+1];p=Path(raw);p=p if p.is_absolute() else Path(cfg['cwd'])/p
   weights[flag]={'path':str(p),'resolved':str(p.resolve()),'bytes':p.stat().st_size if p.is_file() else None}
 initial=quiet();gpu=command(['nvidia-smi','--query-gpu=name,pstate,power.draw,power.limit,utilization.gpu,memory.used,pcie.link.gen.max,pcie.link.width.max','--format=csv,noheader,nounits'])
 assert ', P8,' in gpu and float(gpu.split(',')[4])==0,gpu
 workloads=Workloads(cfg,root,a.server_root)
 header={'event':'discovery','time':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'model':'Qwen3.8-Flash-Next GSQ-RCO Q2_0 125B','selection':'Fleet-record standing chat recipe, newest adopted chat engine suffix 0145; IQ3_XXS/0144 is a slower quality alternative; Qwen3.6 A3B/0145 is a different 16K lineage for a future pass.','recipe':'recipes/flashnext-gsqrc-q20-125b-strata.md','config':str(a.config.resolve()),'config_sha256':original_config_sha,'standing_config':cfg,'weights':weights,'engine_tag':command(['git','-C',str(build_root),'describe','--tags','--always','--dirty']),'engine_commit':command(['git','-C',str(build_root),'rev-parse','HEAD']),'engine_sha256':sha(exe),'engine_diff_sha256':hashlib.sha256(command(['git','-C',str(build_root),'diff']).encode()).hexdigest(),'python_server_root':str(a.server_root.resolve()),'preflight_gpu':gpu,'preflight':initial,'limits':LIMITS,'cooldown_seconds':a.cooldown,'runner_sha256':sha(__file__),'prediction_limit':192,'temperature':0,'thinking':False,'corpus_sha256':sha(root/'corpus.txt'),'pcie_dmon_units':'MB/s, as reported by nvidia-smi dmon header','ladder_targets':[32768,65536,81920,98304,130816],'128k_definition':'131072 context cells; target 130816 prompt tokens leaves 256 cells for 192 generated tokens and template margin.'}
 (root/'discovery.json').write_text(json.dumps(header,indent=2)+'\n');print(json.dumps(header),flush=True)
 if a.prepare_only:return
 out=a.out.open('x');server=None;server_output=None;monitor=Monitor(root);records=[]
 def record(row):out.write(json.dumps(row)+'\n');out.flush();records.append(row)
 def interrupt(signum,frame):raise KeyboardInterrupt('signal '+str(signum))
 signal.signal(signal.SIGTERM,interrupt);record(header)
 try:
  set_power(225)
  invocation=[sys.executable,'-u','-m','serve.server','--engine','strata','--config',str(pinned),'--host','127.0.0.1','--port','8080']
  # Refuse to touch a live user serve.
  import socket
  with socket.socket() as sock:
   assert sock.connect_ex(('127.0.0.1',8080))!=0,'Port 8080 already in use'
  server_output=(root/'server.log').open('w');server=subprocess.Popen(invocation,cwd=a.server_root,stdout=server_output,stderr=subprocess.STDOUT,start_new_session=True)
  deadline=time.time()+900
  while True:
   if server.poll() is not None:raise RuntimeError('Server exited while loading')
   try:
    health=http('http://127.0.0.1:8080/health',timeout=2)
    if health.get('loaded'):break
   except (OSError,ValueError):pass
   if time.time()>deadline:raise TimeoutError('Server readiness')
   time.sleep(1)
  record({'event':'health','server_pid':server.pid,'invocation':invocation,'health':health});print('PINNED HEALTH '+json.dumps(health),flush=True);monitor.start()
  def ask(text,phase,target,run,step,limit,needle=None,estimated=None,depth=None):
   before=quiet()
   if monitor.error:raise RuntimeError(monitor.error)
   b0=a.serve_log.stat().st_size;t0=time.time()
   body={'model':cfg.get('model_name','local-model'),'messages':[{'role':'user','content':text}],'max_tokens':192,'temperature':0,'seed':42,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
   response=http('http://127.0.0.1:8080/v1/chat/completions',body);t1=time.time()
   for _ in range(30):
    with a.serve_log.open('rb') as f:f.seek(b0);matches=LINE.findall(f.read().decode(errors='replace'))
    if matches:break
    time.sleep(.1)
   if not matches:raise RuntimeError('No engine timing summary')
   r=matches[-1];prompt_s=int(r[3])/1000;decode_s=int(r[6])/1000;end_prefill=t1-decode_s
   answer=response.get('choices',[{}])[0].get('message',{}).get('content') or ''
   rec={'event':'measurement','phase':phase,'step':step,'power_limit_w':limit,'target_tokens':target,'run_index':run,'prompt_n':int(r[0]),'reused_tokens':int(r[1]),'read_tokens':int(r[2]),'prefill_tps':float(r[4]),'prefill_seconds':prompt_s,'generated_tokens':int(r[5]),'decode_tps':float(r[7]),'decode_seconds':decode_s,'wall_seconds':round(t1-t0,4),'time_start':t0,'time_end':t1,'power_prefill':monitor.window(end_prefill-prompt_s,end_prefill),'power_decode':monitor.window(end_prefill,t1),'needle':needle,'needle_depth':depth,'needle_ok':needle in answer if needle else None,'local_prompt_estimate':estimated,'response':answer,'quiet_before':before,'contamination':monitor.error}
   if target and (abs(rec['prompt_n']-target)>64 or rec['reused_tokens']!=0):raise RuntimeError('Uncalibrated/reused long input: '+json.dumps(rec))
   record(rec);print(f"{phase} step={step} PL={limit} target={target} prompt_n={rec['prompt_n']} prefill={rec['prefill_tps']} decode={rec['decode_tps']} needle={rec['needle_ok']}",flush=True)
   if monitor.error:raise RuntimeError(monitor.error)
   return rec
  # Warmup is evidence, excluded from result tables.
  ask('Warmup: write a short Python merge-sort function.','warmup',None,0,None,225)
  for target in header['ladder_targets']:
   for run in range(2):
    text,needle,estimate,depth=workloads.make(target,f'ladder-{target}-{run}')
    ask(text,'ladder',target,run,None,225,needle,estimate,depth)
  for step,limit in enumerate(LIMITS):
   print(f'COOLDOWN checkpoint {step}, next limit {limit} W: {a.cooldown}s',flush=True)
   set_power(limit);record({'event':'checkpoint','step':step,'power_limit_w':limit,'cooldown_seconds':a.cooldown,'time':time.time()});time.sleep(a.cooldown);quiet()
   for run,q in enumerate(SHORT):ask(f'Unique checkpoint {step} prompt {run}.\n'+q,'short',None,run,step,limit)
   for target in (30720,102400):
    text,needle,estimate,depth=workloads.make(target,f'walk-{step}-{target}')
    ask(text,'walk',target,0,step,limit,needle,estimate,depth)
   if step==5:
    text,needle,estimate,depth=workloads.make(102400,'ascending-145-recheck')
    ask(text,'recheck',102400,1,step,limit,needle,estimate,depth)
  record({'event':'complete','measurements':sum(r.get('event')=='measurement' for r in records),'needle_failures':sum(r.get('needle_ok') is False for r in records),'server_pid':server.pid})
 except BaseException as e:
  record({'event':'error','type':type(e).__name__,'message':str(e)});raise
 finally:
  # Restore even after HTTP/parse/assertion failure or SIGTERM/Ctrl-C.
  try:
   restored=set_power(225);record({'event':'power_restored','response':restored,'time':time.time()})
  except Exception as cleanup_error:
   record({'event':'power_restore_error','message':str(cleanup_error)})
  if server is not None:
   try:os.killpg(server.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:server.wait(timeout=20)
   except subprocess.TimeoutExpired:os.killpg(server.pid,signal.SIGKILL);server.wait()
  monitor.close()
  if server_output:server_output.close()
  record({'event':'cleanup','server_exit':server.returncode if server else None,'config_unchanged':sha(a.config)==original_config_sha,'gpu':command(['nvidia-smi','--query-gpu=power.limit,memory.used,utilization.gpu','--format=csv,noheader,nounits'])});out.close()
  print('CLEANUP complete: 225 W restored, server and samplers stopped',flush=True)
if __name__=='__main__':main()
