#!/usr/bin/env python3
"""Range-only tables for the v2 JSONL; warmup never enters comparisons."""
import argparse,json,statistics
from pathlib import Path

def span(values,d=1):
 v=[x for x in values if x is not None]
 if not v:return '—'
 lo,hi=min(v),max(v)
 return f'{lo:,.{d}f}' if lo==hi else f'{lo:,.{d}f}–{hi:,.{d}f}'
def ratio_loss(rows,baseline,key):
 a=[r[key] for r in rows];b=[r[key] for r in baseline]
 return [100*(1-max(a)/min(b)),100*(1-min(a)/max(b))]
def main():
 p=argparse.ArgumentParser();p.add_argument('evidence',type=Path);a=p.parse_args();root=a.evidence.with_suffix('')
 records=[json.loads(x) for x in a.evidence.read_text().splitlines()];data=[r for r in records if r.get('event')=='measurement' and r['phase']!='warmup']
 complete=any(r.get('event')=='complete' for r in records)
 if not complete:raise SystemExit('Measurement session is not complete; no final tables generated')
 assert len(data)==56,len(data)
 assert all(r.get('contamination') is None for r in data)
 assert all(r['needle_ok'] is True and r['reused_tokens']==0 and r['generated_tokens']==192 for r in data if r['target_tokens'])
 assert records[-1]['event']=='cleanup' and records[-1]['config_unchanged']
 assert any(r.get('event')=='power_restored' for r in records)
 header=records[0];long=[r for r in data if r['target_tokens']]
 out=['## Strata v0.1.45 · Flash-Next Q2_0 125B · 2026-10-18','',
 'One pinned calibrated 128K/32K-resident serve, same executable and weights throughout. Two ladder runs per point; the power walk uses both directions and a 60-second cooldown at every checkpoint. All values below are ranges over this run, not best-of or comparisons with historical measurements.','',
 '### Controlled context ladder at 225 W','',
 '| Input class | Actual prompt tokens | Prefill tok/s | Decode after fill tok/s | Request wall s | Needle |',
 '|---|---:|---:|---:|---:|---|']
 for target,label in zip(header['ladder_targets'],('32K','64K','80K','96K','128K')):
  rows=[r for r in data if r['phase']=='ladder' and r['target_tokens']==target];assert len(rows)==2
  out.append('| '+label+' | '+span([r['prompt_n'] for r in rows],0)+' | '+span([r['prefill_tps'] for r in rows])+' | '+span([r['decode_tps'] for r in rows])+' | '+span([r['wall_seconds'] for r in rows])+' | 2/2 |')
 out+=['','128K is the assigned 131,072-token context; its prompt leaves space for the requested 192 output tokens. All long inputs use actual code/prose, zero prefix reuse and an exact key at about 10% depth.','',
 '### Power limit versus throughput','',
 '| Limit W | Short decode tok/s | 30K prefill tok/s | Decode at 30K tok/s | 100K prefill tok/s | Decode at 100K tok/s |',
 '|---:|---:|---:|---:|---:|---:|']
 summary={}
 for limit in (225,190,165,145,125):
  short=[r for r in data if r['phase']=='short' and r['power_limit_w']==limit]
  fill30=[r for r in data if r['phase']=='walk' and r['power_limit_w']==limit and r['target_tokens']==30720]
  fill100=[r for r in data if r['phase'] in ('walk','recheck') and r['power_limit_w']==limit and r['target_tokens']==102400]
  out.append('| '+str(limit)+' | '+' | '.join(span([r[key] for r in rows]) for rows,key in ((short,'decode_tps'),(fill30,'prefill_tps'),(fill30,'decode_tps'),(fill100,'prefill_tps'),(fill100,'decode_tps')))+' |')
  baseline=[r for r in data if r['phase']=='walk' and r['power_limit_w']==225 and r['target_tokens']==102400]
  directional=[100*(1-r['prefill_tps']/next(b['prefill_tps'] for b in baseline if b['step']==(0 if r['step']<4 else 8))) for r in fill100] if limit!=125 else [100*(1-fill100[0]['prefill_tps']/b['prefill_tps']) for b in baseline]
  summary[str(limit)]={'direction_matched_100k_prefill_loss_percent':directional,'100k_prefill_loss_percent_bounds':ratio_loss(fill100,baseline,'prefill_tps'),'100k_decode_loss_percent_bounds':ratio_loss(fill100,baseline,'decode_tps'),'samples_100k':len(fill100)}
 out+=['','The 145 W 100K range includes the extra recheck on the ascending footstep. The 125 W midpoint has one checkpoint; other limits have two. Short-decode ranges include the three fixed prompt classes.','',
 '### Board telemetry during the 100K arm','',
 '| Limit W | Prefill W | Decode W | Prefill SM MHz | Decode SM MHz | Prefill °C | Decode °C | Prefill PCIe RX MB/s |',
 '|---:|---:|---:|---:|---:|---:|---:|---:|']
 for limit in (225,190,165,145,125):
  rows=[r for r in data if r['phase'] in ('walk','recheck') and r['power_limit_w']==limit and r['target_tokens']==102400]
  pairs=[('power_prefill','watts'),('power_decode','watts'),('power_prefill','sm_mhz'),('power_decode','sm_mhz'),('power_prefill','temp_c'),('power_decode','temp_c'),('power_prefill','rx_mb_s')]
  out.append('| '+str(limit)+' | '+' | '.join(span([(r[phase] or {}).get(key) for r in rows],0 if key in ('sm_mhz','rx_mb_s') else 1) for phase,key in pairs)+' |')
 out+=['','Telemetry entries are ranges of per-request window means. Measurement records include window min/max from the raw 200 ms GPU samples; PCIe traffic is sampled at 1 Hz in nvidia-smi’s reported MB/s. GPU board power excludes CPU and RAM power.','',
 '### Ascending 145 W recheck','']
 for r in data:
  if r['power_limit_w']==145 and r['target_tokens']==102400:
   out.append(f"- Step {r['step']}, {r['phase']}, run {r['run_index']}: {r['prefill_tps']} tok/s prefill, {r['decode_tps']} tok/s decode, {r['wall_seconds']:.1f} s wall; needle passed.")
 out+=['',f"All {len(long)} long-context needle checks passed. There was one loaded server instance; cleanup restored 225 W, stopped the owned server and both sampler processes, and verified the standing config was unchanged.",'',
 '[Raw measurements](../'+a.evidence.name+') · [Run protocol and pinned discovery](README.md) · [Runner](../strata-power-sweep.py)']
 (root/'tables.md').write_text('\n'.join(out)+'\n');(root/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n');print('\n'.join(out));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
