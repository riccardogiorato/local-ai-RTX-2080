#!/bin/bash
# Sample per-core MHz, package temperature and package power once a second.
# Usage: cpu-monitor.sh OUT_CSV SECONDS
out=$1; dur=${2:-600}; E=/sys/class/powercap/intel-rapl:0/energy_uj
echo "t,mhz_min,mhz_avg,mhz_max,pkg_c,core_max_c,pkg_w" > "$out"
prev=$(sudo -n cat $E); t0=$(date +%s)
for ((i=0; i<dur; i++)); do
  sleep 1
  now=$(sudo -n cat $E); w=$(( (now-prev)/1000000 )); prev=$now
  mhz=$(awk '/cpu MHz/{print $4}' /proc/cpuinfo | sort -n | awk '{a[NR]=$1; s+=$1} END{printf "%d,%d,%d", a[1], s/NR, a[NR]}')
  temps=$(sensors 2>/dev/null | awk '/Package id 0/{gsub(/[+°C]/,"",$4); p=$4} /^Core [0-9]/{gsub(/[+°C]/,"",$3); if ($3>m) m=$3} END{print p "," m}')
  echo "$(( $(date +%s)-t0 )),$mhz,$temps,$w" >> "$out"
done
