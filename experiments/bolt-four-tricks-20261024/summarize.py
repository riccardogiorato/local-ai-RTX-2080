import json,pathlib,collections,statistics
root=pathlib.Path(__file__).resolve().parent
for p in sorted(root.glob('*.jsonl')):
 groups=collections.defaultdict(list)
 for l in p.read_text().splitlines():
  r=json.loads(l)
  if not r.get('warmup',True):groups[(r['phase'],r['name'])].append(r)
 for (phase,name),rows in groups.items():
  ts=[r['response']['timings'] for r in rows]
  print(p.stem,phase,name,'n',len(rows),'decode',','.join(f"{t['predicted_per_second']:.2f}" for t in ts),'prefill',','.join(f"{t['prompt_per_second']:.1f}" for t in ts),'cache',str([t['cache_n'] for t in ts]),'prompt',str([t['prompt_n'] for t in ts]),'sha',str([r['content_sha256'][:10] for r in rows]))
