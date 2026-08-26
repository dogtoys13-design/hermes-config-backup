#!/usr/bin/env python
"""🔍 幽灵客户端抓取器 — 抓"谁连到127.0.0.1:443代理"

原理：代理记录"有请求"，但转发连接的PID是代理自己。
本脚本高频（0.2秒）扫 netstat，抓 ESTABLISHED 到 127.0.0.1:443 的【客户端】PID。
配合 siliconflow_proxy.py 使用——代理日志+本脚本=完整证据链。

用法：python ghost_catcher.py
"""
import subprocess, time, datetime, os, re

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghost_catcher.log")
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
                            capture_output=True, text=True, timeout=8, errors="ignore", creationflags=0x08000000)
        m = re.search(r"CommandLine=(.+)", out.stdout, re.DOTALL)
        return m.group(1).strip()[:200] if m else "?"
    except:
        return "?"

log("👻 幽灵客户端抓取器启动（0.2秒间隔）")
while True:
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                           timeout=5, errors="ignore", creationflags=0x08000000)
        for line in out.stdout.split("\n"):
            if "127.0.0.1:443" in line and "ESTABLISHED" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    local_port = parts[1]
                    if pid not in seen:
                        seen.add(pid)
                        cmd = get_cmdline(pid)
                        log(f"🚨🚨 抓到幽灵客户端! PID={pid} 本地端口={local_port}")
                        log(f"    命令行: {cmd}")
    except Exception as e:
        log(f"异常: {str(e)[:60]}")
    time.sleep(0.2)
