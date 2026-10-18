import json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WATCH=661766
BAD={'wasm-opt','ninja','rustc','cc1','cc1plus','clang','clang++','gcc','g++','make','ps2run'}
with (ROOT/'resource-samples.jsonl').open('w') as f:
 while Path(f'/proc/{WATCH}').exists():
  raw=subprocess.check_output(['ps','-eo','pid,ppid,pcpu,comm','--no-headers'],text=True)
  ps=[]
  for line in raw.splitlines():
   pid,ppid,cpu,name=line.split(maxsplit=3);ps.append((int(pid),int(ppid),float(cpu),name))
  own={WATCH};changed=True
  while changed:
   old=len(own);own.update(pid for pid,ppid,cpu,name in ps if ppid in own);changed=len(own)>old
  external=[{'pid':pid,'cpu_percent_lifetime':cpu,'name':name} for pid,ppid,cpu,name in ps if pid not in own and name in BAD and cpu>50]
  gpu=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw,clocks.current.sm','--format=csv,noheader,nounits'],text=True).strip()
  row={'time':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'loadavg':Path('/proc/loadavg').read_text().strip(),'gpu':gpu,'external_builds':external};f.write(json.dumps(row)+'\n');f.flush()
  time.sleep(5)
