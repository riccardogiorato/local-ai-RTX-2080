import json,pathlib,statistics
root=pathlib.Path(__file__).resolve().parent
for p in sorted(root.glob('*.jsonl')):
 if p.stem.endswith('-probes'): continue
 rows=[json.loads(l) for l in p.read_text().splitlines()]; rows=[r for r in rows if r.get('warmup') is False]
 for name in dict.fromkeys(r['prompt'] for r in rows):
  rr=[r for r in rows if r['prompt']==name]; rates=[r['response']['timings']['predicted_per_second'] for r in rr]
  print(p.stem,name,'n='+str(len(rr)),f'{min(rates):.2f}-{max(rates):.2f}', 'tokens='+str([r['response']['timings']['predicted_n'] for r in rr]),'hashes='+str([r['content_sha256'][:12] for r in rr]))
