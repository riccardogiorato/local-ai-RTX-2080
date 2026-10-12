#!/usr/bin/env python3
"""1 Hz CPU monitor with safety abort. Run as root.
Usage: oc-monitor.py OUT_CSV SECONDS [ABORT_C] [ABORT_V] [PID_TO_KILL]
Aborts on core >= ABORT_C, vcore >= ABORT_V for 3 s in a row, or vcore >= ABORT_V + 0.07 once.
Columns: t, MHz min/avg/max, hottest core C, package C, package W, core voltage (IA32_PERF_STATUS 0x198)."""
import os, re, struct, subprocess, sys, time, signal
out, dur = sys.argv[1], int(sys.argv[2])
abort_c = float(sys.argv[3]) if len(sys.argv) > 3 else 999
abort_v = float(sys.argv[4]) if len(sys.argv) > 4 else 99
victim = int(sys.argv[5]) if len(sys.argv) > 5 else 0
E = "/sys/class/powercap/intel-rapl:0/energy_uj"
def msr(reg, cpu=0):
    fd = os.open(f"/dev/cpu/{cpu}/msr", os.O_RDONLY)
    try: return struct.unpack("<Q", os.pread(fd, 8, reg))[0]
    finally: os.close(fd)
def vcore():
    return max(((msr(0x198, c) >> 32) & 0xFFFF) / 8192.0 for c in range(os.cpu_count()))
def temps():
    t = subprocess.run(["sensors"], capture_output=True, text=True).stdout
    cores = [float(x) for x in re.findall(r"^Core \d+:\s+\+([\d.]+)", t, re.M)]
    pkg = re.search(r"Package id 0:\s+\+([\d.]+)", t)
    return max(cores) if cores else 0, float(pkg.group(1)) if pkg else 0
f = open(out, "w"); f.write("t,mhz_min,mhz_avg,mhz_max,core_max_c,pkg_c,pkg_w,vcore\n")
prev = int(open(E).read()); t0 = time.time(); aborted = ""; hiv = 0
for i in range(dur):
    time.sleep(1)
    now = int(open(E).read()); w = (now - prev) / 1e6; prev = now
    mhz = [float(x) for x in re.findall(r"cpu MHz\s*:\s*([\d.]+)", open("/proc/cpuinfo").read())]
    cm, pk = temps(); v = vcore()
    f.write(f"{int(time.time()-t0)},{min(mhz):.0f},{sum(mhz)/len(mhz):.0f},{max(mhz):.0f},{cm},{pk},{w:.0f},{v:.4f}\n"); f.flush()
    hiv = hiv + 1 if v >= abort_v else 0
    if cm >= abort_c or hiv >= 3 or v >= abort_v + 0.07:
        aborted = f"ABORT at t={int(time.time()-t0)}s: core {cm} C, vcore {v:.3f} V"
        if victim:
            try: os.kill(victim, signal.SIGTERM)
            except ProcessLookupError: pass
        break
print(aborted or "monitor finished without abort", flush=True)
