#!/bin/bash
# Paired Strata-only 4.7 GHz trial: fresh stock probe vs 47x6 MSR probe, no AVX2 burn.
# Usage: bash oc47-strata-only.sh   (aborts per-sample at 90 C core / 1.35 V via oc-monitor.py)
set -u
REPO=/home/riccardogiorato/Desktop/github/local-ai-rtx2080; D=$REPO/benchmarks/cpu
CFG=/home/riccardogiorato/Desktop/github/strata-port/strata-q20-gsq-01401-tailnet.json
STOCK_OUT=$REPO/benchmarks/results/strata-oc47f-stock-probe-20261012.json
OC_OUT=$REPO/benchmarks/results/strata-oc47f-47-probe-20261012.json
MON_CSV=$D/oc47f-strata-20261012.csv
rm -f $STOCK_OUT $OC_OUT $STOCK_OUT.boot0.log $OC_OUT.boot0.log $MON_CSV

# MSR 0x1AD helpers (multipliers reset on reboot too, but we always restore)
read_msr(){ sudo -n python3 -c "
import os,struct; print(struct.unpack('<Q',os.pread(os.open('/dev/cpu/0/msr',os.O_RDONLY),8,0x1AD))[0])"; }
ORIG=$(read_msr)
restore(){ sudo -n python3 -c "
import os,struct
for c in range(os.cpu_count()):
    fd=os.open(f'/dev/cpu/{c}/msr',os.O_WRONLY); os.pwrite(fd,struct.pack('<Q',$ORIG),0x1AD); os.close(fd)
print('MSR 0x1AD restored to stock')"; }
trap restore EXIT INT TERM
echo "== original MSR 0x1AD = $ORIG ($(printf '0x%x' $ORIG))"

# monitor for the whole run (root, 1 Hz, abort thresholds 90 C / 1.35 V)
sudo -n modprobe msr
sudo -n python3 $D/oc-monitor.py $MON_CSV 2400 90 1.35 0 > /tmp/oc47f-mon.out 2>&1 &
MON=$!

probe(){ # $1 = output.json  $2 = arm label
  ( cd $REPO && python3 benchmarks/strata-env-probe.py $CFG "$1" "[[\"$2\",{}]]" < /dev/null )
}

echo "== stock probe start $(date +%H:%M:%S)"; date +%s > $D/.t_stock
probe $STOCK_OUT stock47f || { echo "stock probe failed"; exit 1; }
echo "== stock probe done  $(date +%H:%M:%S)"

# engage 47x6
sudo -n python3 -c "
import os,struct
orig=$ORIG; new=(orig & ~((1<<48)-1)) | sum(47<<(8*i) for i in range(6))
for c in range(os.cpu_count()):
    fd=os.open(f'/dev/cpu/{c}/msr',os.O_WRONLY); os.pwrite(fd,struct.pack('<Q',new),0x1AD); os.close(fd)
fd=os.open('/dev/cpu/0/msr',os.O_RDONLY); rb=struct.unpack('<Q',os.pread(fd,8,0x1AD))[0]
print('MSR 0x1AD now', [(rb>>(8*i))&0xFF for i in range(6)])"

echo "== 4.7 probe start $(date +%H:%M:%S)"; date +%s > $D/.t_47
probe $OC_OUT oc47 || { echo "4.7 probe failed"; exit 1; }
echo "== 4.7 probe done  $(date +%H:%M:%S)"
restore; trap - EXIT INT TERM
sudo -n kill $MON 2>/dev/null
echo OC47F-DONE