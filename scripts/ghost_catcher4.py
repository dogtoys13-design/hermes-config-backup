#!/usr/bin/env python
"""🔍 高频连接抓取器 v4 — 盯SiliconFlow真实IP（不需要hosts劫持）

原理：直接扫 netstat 里到 SiliconFlow 5个真实IP的 ESTABLISHED 连接，
0.1秒间隔（超高频率），抓到就记录PID+命令行。QQ触发的调用即使短连接也能抓。
"""
import subprocess, time, datetime, os, re

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghost_catcher4.log")
SILICONFLOW_IPS = ["139.196.152.242", "47.102.215.139", "47.102.37.23", "47.103.87.49", "101.132.62.140"]
seen = set()

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_cmdline(pid):
    try:
        out = subprocess.run(["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:list"],
                            capture_output=True, text=True, timeout=6, errors="ignore", creationflags=0x08000000)
        m = re.search(r"CommandLine=(.+)", out.stdout, re.DOTALL)
        return m.group(1).strip()[:250] if m else "?"
    except:
        return "?"

log("👻 v4高频抓取器启动（0.1秒间隔，盯SiliconFlow真实IP）")
while True:
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                           timeout=4, errors="ignore", creationflags=0x08000000)
        for line in out.stdout.split("\n"):
            if "ESTABLISHED" not in line:
                continue
            parts = line.split()
            if len(parts) >= 5:
                remote = parts[2]
                pid = parts[-1]
                for ip in SILICONFLOW_IPS:
                    if remote.startswith(ip + ":"):
                        if pid not in seen:
                            seen.add(pid)
                            cmd = get_cmdline(pid)
                            log(f"🚨🚨 抓到SiliconFlow连接! PID={pid} | {remote} | CMD: {cmd}")
                        break
    except Exception as e:
        log(f"异常: {str(e)[:50]}")
    time.sleep(0.1)
