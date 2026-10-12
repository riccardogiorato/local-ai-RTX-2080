#!/bin/bash
# After the fair-context chain: re-run the disturbed Qwen-4B 128K suite at stock, then a 4.7 GHz all-core trial
# via MSR_TURBO_RATIO_LIMIT (resets on reboot), with auto-abort, then a Strata decode probe, then restore stock.
set -u
REPO=/home/riccardogiorato/Desktop/github/local-ai-rtx2080; D=$REPO/benchmarks/cpu; BENCH=$REPO/benchmarks
RUNLOG=$BENCH/results/fairctx-ram3200-20261012.runner.log
until grep -q 'FAIRCTX-DONE' $RUNLOG 2>/dev/null; do sleep 30; done
echo "== chain finished $(date +%H:%M:%S)"
# 1) re-run Qwen-4B @128K at stock
B=/home/riccardogiorato/Desktop/github/llamacpp-b2f036c0f/build-sm75/bin/llama-server; M=/home/riccardogiorato/models
pkill -x llama-server 2>/dev/null; sleep 4
setsid $B --alias local-model --host 127.0.0.1 --port 8080 --parallel 1 --n-gpu-layers 999 --flash-attn on --jinja \
  -m $M/qwen35-4b-mtp/Qwen3.5-4B-Q4_K_M.gguf --ctx-size 131072 --batch-size 512 --ubatch-size 512 -ctk q8_0 -ctv q8_0 \
  --spec-type draft-mtp --spec-draft-n-max 4 > /tmp/q4b-rerun.server.log 2>&1 < /dev/null &
i=0; until curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; do sleep 5; i=$((i+5)); [ $i -gt 600 ] && break; done
( cd $BENCH && WARM_TIMEOUT=240 PI_OFFLINE=0 bash agentic-bench.sh qwen35-4b-128k-b11562-v22 900 < /dev/null > /tmp/q4b-rerun.stdout 2>&1 )
f=$(ls -t $BENCH/results/qwen35-4b-128k-b11562-v22-2*.jsonl | head -1)
python3 -c "
import json; rows=[json.loads(l) for l in open('$f')]
print('== qwen35-4b-128k rerun (stock)', f'{sum(r[\"passed\"] for r in rows)}/{len(rows)} wall {sum(r[\"wall_s\"] for r in rows)}s', 'misses:', [r['task'].split('-tb-')[0] for r in rows if not r['passed']])"
pkill -x llama-server; sleep 5
# 2) 4.7 GHz all-core via MSR 0x1AD
sudo -n modprobe msr
ORIG=$(sudo -n python3 -c "
import os,struct; fd=os.open('/dev/cpu/0/msr',os.O_RDONLY); print(struct.unpack('<Q',os.pread(fd,8,0x1AD))[0])")
echo "original MSR 0x1AD = $ORIG ($(printf '0x%x' $ORIG))"
restore(){ sudo -n python3 -c "
import os,struct
for c in range(os.cpu_count()):
    fd=os.open(f'/dev/cpu/{c}/msr',os.O_WRONLY); os.pwrite(fd,struct.pack('<Q',$ORIG),0x1AD); os.close(fd)
print('MSR 0x1AD restored to stock')"; }
trap restore EXIT
sudo -n python3 -c "
import os,struct
orig=$ORIG; new=(orig & ~((1<<48)-1)) | sum(47<<(8*i) for i in range(6))
for c in range(os.cpu_count()):
    fd=os.open(f'/dev/cpu/{c}/msr',os.O_WRONLY); os.pwrite(fd,struct.pack('<Q',new),0x1AD); os.close(fd)
fd=os.open('/dev/cpu/0/msr',os.O_RDONLY); rb=struct.unpack('<Q',os.pread(fd,8,0x1AD))[0]
print('MSR 0x1AD now', [(rb>>(8*i))&0xFF for i in range(6)])"
sleep 2
$D/avx2-burn 6 300 > /tmp/oc47-burn.out 2>&1 &
BURN=$!
sudo -n python3 $D/oc-monitor.py $D/oc47-burn-20261012.csv 300 88 1.35 $BURN
wait $BURN 2>/dev/null; cat /tmp/oc47-burn.out
python3 - <<'PY'
import csv
rows=list(csv.DictReader(open("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/cpu/oc47-burn-20261012.csv")))
load=[r for r in rows if int(r["t"])>=5]
f=lambda k: [float(r[k]) for r in load]
print(f"4.7 GHz burn: {len(load)} s | clock avg {sum(f('mhz_avg'))/len(load):.0f} MHz (lowest {min(f('mhz_min')):.0f}) | hottest core avg {sum(f('core_max_c'))/len(load):.0f} C peak {max(f('core_max_c')):.0f} C | package {sum(f('pkg_w'))/len(load):.0f} W avg {max(f('pkg_w')):.0f} peak | vcore avg {sum(f('vcore'))/len(load):.3f} V peak {max(f('vcore')):.3f} V")
PY
if grep -q ABORT /tmp/oc47-burn.out 2>/dev/null || [ "$(tail -1 $D/oc47-burn-20261012.csv | cut -d, -f1)" -lt 290 ]; then echo "burn aborted or short: skipping Strata probe"; exit 0; fi
# 3) Strata decode probe at 4.7 GHz (2 boots), monitor running alongside
sudo -n python3 $D/oc-monitor.py $D/oc47-strata-20261012.csv 2400 88 1.35 0 > /tmp/oc47-strata-mon.out 2>&1 &
MON=$!
( cd $REPO && python3 benchmarks/strata-env-probe.py /home/riccardogiorato/Desktop/github/strata-port/strata-q20-gsq-01401-tailnet.json benchmarks/results/strata-0143-oc47-probe-20261012.json '[["oc47",{}],["oc47",{}]]' < /dev/null > /tmp/oc47-probe.out 2>&1 )
sudo -n kill $MON 2>/dev/null; sleep 1
python3 - <<'PY'
import json, statistics, csv
rows=[json.loads(l) for l in open("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/results/strata-0143-oc47-probe-20261012.json")]
S=[r["decode_tps"] for r in rows if r["event"]=="sample" and not r["case"].startswith("long")]
L=[round(r["timings"]["prompt_tokens"]/(r["timings"]["prompt_ms"]/1000)) for r in rows if r["event"]=="sample" and r["case"].startswith("long")]
D=[round(r["decode_tps"],1) for r in rows if r["event"]=="sample" and r["case"].startswith("long")]
print(f"Strata at 4.7 GHz: short decode {sorted(round(x,1) for x in S)} median {statistics.median(S):.1f} | 32K prefill {L} | decode after 32K {D}")
print("Strata at 4.3 GHz (same config, same RAM, earlier today): current-arm median 53.7, 32K prefill 655-656, decode after 32K 33.1-33.5")
m=list(csv.DictReader(open("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/cpu/oc47-strata-20261012.csv")))
busy=[r for r in m if float(r["pkg_w"])>=50]
if busy: print(f"during Strata: clock avg {sum(float(r['mhz_avg']) for r in busy)/len(busy):.0f} MHz, hottest core peak {max(float(r['core_max_c']) for r in busy):.0f} C, package peak {max(float(r['pkg_w']) for r in busy):.0f} W, vcore peak {max(float(r['vcore']) for r in busy):.3f} V")
PY
echo OC47-DONE
