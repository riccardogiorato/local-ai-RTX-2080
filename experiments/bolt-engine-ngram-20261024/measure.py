#!/usr/bin/env python3
"""Warm each fixed prompt once, then retain two raw, uncached greedy completions."""
import json, sys, time, urllib.request, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
label=sys.argv[1]
def get(path, payload=None):
    req=urllib.request.Request('http://127.0.0.1:8080/'+path, data=None if payload is None else json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=600) as r: return r.read().decode()
def metrics():
    return {a[0]:float(a[1]) for l in get('metrics').splitlines() if not l.startswith('#') and len(a:=l.split())==2}
prompts={n:(ROOT/'benchmarks'/'prompts'/n).read_text() for n in ['code-continuation.txt','decode-isolation.txt']}
prompts['prose-long']='Write a detailed essay of at least 900 words explaining how controlled experiments distinguish causation from correlation. Discuss confounding variables, random assignment, measurement error, replication, and a concrete gardening example. Use connected prose with no lists. Begin the essay now:\n'
for name,prompt in prompts.items():
    for run in range(3):
        before=metrics(); start=time.monotonic()
        result=json.loads(get('completion', {'prompt':prompt,'n_predict':256 if name!='prose-long' else 512,'temperature':0,'seed':42,'cache_prompt':False,'stream':False,'samplers':['temperature']}))
        wall=time.monotonic()-start; after=metrics()
        delta={k:after[k]-before.get(k,0) for k in after if k.endswith('_total')}
        row={'label':label,'prompt':name,'prompt_text':prompt,'run':run,'warmup':run==0,'wall_s':wall,'metrics_delta':delta,'response':result,'content_sha256':hashlib.sha256(result.get('content','').encode()).hexdigest()}
        with (OUT/(label+'.jsonl')).open('a') as f: f.write(json.dumps(row)+'\n')
        print(json.dumps({'label':label,'prompt':name,'run':run,'timings':result['timings'],'sha':row['content_sha256']}),flush=True)
