# -*- coding: utf-8 -*-
"""
Azrok Network Monitor - runs game normally and watches netstat
Run: python monitor_net.py
"""
import subprocess
import time
import os
import re

exe_dir = os.path.dirname(os.path.abspath(__file__))
exe_path = os.path.join(exe_dir, "Azrok.exe")

print("=" * 60)
print("  Azrok Network Monitor")
print("=" * 60)

# Start game normally
proc = subprocess.Popen([exe_path], cwd=exe_dir)
pid = proc.pid
print(f"[OK] Azrok.exe started, PID: {pid}")
print(f"[*] Monitoring network connections for 20 seconds...")
print()

connections = set()
start = time.time()

while time.time() - start < 20:
    # Check if process still alive
    if proc.poll() is not None:
        print(f"[!] Game exited with code: {proc.returncode}")
        break

    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if str(pid) in line:
                line = line.strip()
                if line and line not in connections:
                    connections.add(line)
                    print(f"  [NET] {line}")
    except:
        pass

    time.sleep(0.3)

print()
print("=" * 60)
print("  SUMMARY")
print("=" * 60)
if connections:
    for c in sorted(connections):
        print(f"  {c}")
else:
    print("  No network connections detected from Azrok.exe")
    print("  (Game may connect and disconnect too fast to catch)")

# Save log
log_path = os.path.join(exe_dir, "net_log.txt")
with open(log_path, 'w') as f:
    f.write(f"Azrok Network Monitor\nPID: {pid}\n\n")
    for c in sorted(connections):
        f.write(c + "\n")
print(f"\n[SAVED] {log_path}")
input("\nPress Enter to exit...")
