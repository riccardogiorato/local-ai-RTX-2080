import collections,csv,json,pathlib,statistics
root=pathlib.Path(__file__).resolve().parent
out={}
for p in sorted(root.glob('*.jsonl')):
 groups=collections.defaultdict(list)
 for l in p.read_text().splitlines():
  r=json.loads(l)
  if r.get('warmup') is False:groups[(r['phase'],r['name'])].append(r)
 if not groups:continue
 data={}
 for (phase,name),rows in groups.items():
  ts=[r['response']['timings'] for r in rows]
  def stats(key):
   vals=[t[key] for t in ts];return {'min':min(vals),'max':max(vals),'mean':statistics.mean(vals)}
  data[phase+'/'+name]={'n':len(rows),'decode_tps':stats('predicted_per_second'),'prefill_tps':stats('prompt_per_second'),'prompt_ms':stats('prompt_ms'),'cache_tokens':[t['cache_n'] for t in ts],'fresh_tokens':[t['prompt_n'] for t in ts],'hashes':[r['content_sha256'] for r in rows],'accepted_fraction':[t.get('draft_n_accepted',0)/max(t.get('draft_n',0),1) for t in ts],'needle_pass':all('724193' in r['response'].get('content','') for r in rows) if phase=='prefill' else None}
 tele=root/(p.stem+'-telemetry.csv')
 if tele.exists():
  rows=list(csv.DictReader(tele.open()))
  data['telemetry']={'sampled_peak_gpu_mib':max(float(r[' memory.used [MiB]'].split()[0]) for r in rows),'max_power_w':max(float(r[' power.draw [W]'].split()[0]) for r in rows)}
 cfg=root/(p.stem+'-config.json')
 if cfg.exists():data['health_after_s']=json.loads(cfg.read_text()).get('health_after_s')
 out[p.stem]=data
(root/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
