#!/usr/bin/env python
"""💰 SiliconFlow 余额+连接 双监控 — 抓幽灵调用

原理：
  1. 每2秒扫本机到 api.siliconflow.cn 的连接（抓本机调用方）
  2. 每5分钟查一次余额（抓外部调用——余额减少但本机无连接=外部在调）
  3. 余额变化立即记录（时间+余额值+推断）

用法：python watch_siliconflow2.py
日志：scripts/siliconflow_watch2.log
"""
import subprocess, time, sys, datetime, os, re, requests

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siliconflow_watch2.log")
API_KEY = "sk-oblkrvgfnogxovzpjhcrylgsfdoqjndunkoaqovxmwkruflz"
seen_pids = set()
last_balance = None

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def scan_connections():
    """扫本机到SiliconFlow的连接"""
    results = []
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                            timeout=10, errors="ignore", creationflags=0x08000000)
        for line in out.stdout.split("\n"):
            if "api.siliconflow.cn" in line:
                parts = line.split()
                if parts:
                    results.append((parts[-1], line.strip()[:100]))
    except Exception as e:
        results.append(("ERR", str(e)))
    return results

def get_cmdline(pid):
    try:
        out = subprocess.run(["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:list"],
                            capture_output=True, text=True, timeout=10, errors="ignore", creationflags=0x08000000)
        m = re.search(r"CommandLine=(.+)", out.stdout, re.DOTALL)
        return m.group(1).strip()[:300] if m else "?"
    except:
        return "?"

def get_balance():
    try:
        r = requests.get("https://api.siliconflow.cn/v1/user/info",
                        headers={"Authorization": f"Bearer {API_KEY}"}, timeout=10)
        d = r.json()
        if d.get("data"):
            return float(d["data"].get("balance", 0))
    except Exception as e:
        return None
    return None

log("💰 余额+连接双监控启动")
while True:
    # 1. 扫连接（每2秒）
    try:
        conns = scan_connections()
        for pid, line in conns:
            if pid not in seen_pids:
                seen_pids.add(pid)
                cmd = get_cmdline(pid)
                log(f"🆕 抓到本机连接! PID={pid} | {line[:80]} | CMD: {cmd}")
    except Exception as e:
        log(f"扫描异常: {e}")

    # 2. 查余额（每5分钟）
    now = time.time()
    if int(now) % 300 < 2:  # 每5分钟一次
        bal = get_balance()
        if bal is not None:
            if last_balance is None:
                log(f"💰 初始余额: {bal}")
            elif bal < last_balance - 0.001:
                log(f"🚨 余额减少! {last_balance} → {bal} (减少{last_balance-bal:.4f})")
                # 抓一下当前所有连接
                conns = scan_connections()
                if conns:
                    for pid, line in conns:
                        cmd = get_cmdline(pid)
                        log(f"   ⚠️ 此刻连接: PID={pid} | {line[:80]} | CMD: {cmd}")
                else:
                    log(f"   ⚠️ 本机此刻无连接 → 消耗来自【外部/平台侧】!")
            last_balance = bal

    time.sleep(2)
