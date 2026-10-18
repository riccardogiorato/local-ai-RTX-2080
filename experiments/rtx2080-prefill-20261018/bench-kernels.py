#!/usr/bin/env python3
"""Run serial parity/performance comparisons; all logical scores and IDs must match."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXE=ROOT.parents[1].parent/'strata-0145/build-turing-0145/qsa_select_bench'
VARIANTS={'stock':{},'upstream-exact':{'STRATA_SCORES_THREAD':'1'},'custom1':{'STRATA_SCORES_TURING':'1'},'custom2':{'STRATA_SCORES_TURING':'2'},'custom3':{'STRATA_SCORES_TURING':'3'}}
CASES=[(32768,256,7),(99912,256,7),(131072,256,7),(99912,2048,7),(1024,1,1),(4096,17,2),(8193,65,3),(32769,129,19),(100003,257,42),(131071,33,123)]
rows=[]
try:
 for ctx,nq,seed in CASES:
  for name,flags in VARIANTS.items():
   env=os.environ.copy()
   for v in ('STRATA_SCORES_THREAD','STRATA_SCORES_TURING','STRATA_SM75_PERF','STRATA_SELECT_SIMT'):env.pop(v,None)
   env.update(flags);env.update(QSA_BENCH_SEED=str(seed),QSA_BENCH_DUMP=str(ROOT/'logical-output.bin'))
   p=subprocess.run([str(EXE),str(ctx),str(nq),'30','131072'],env=env,capture_output=True,text=True,check=True)
   digest=hashlib.sha256((ROOT/'logical-output.bin').read_bytes()).hexdigest()
   if name=='stock':reference=digest
   if digest!=reference:raise AssertionError((ctx,nq,seed,name,digest,reference))
   row={'context':ctx,'queries':nq,'seed':seed,'variant':name,'sha256':digest,'bitwise_equal':True,'stdout':p.stdout}
   rows.append(row);print(ctx,nq,seed,name,p.stdout.splitlines()[-1],flush=True)
 (ROOT/'kernel-validation.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:
 (ROOT/'logical-output.bin').unlink(missing_ok=True)
