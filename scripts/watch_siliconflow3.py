#!/usr/bin/env python
"""🔍 SiliconFlow 幽灵调用监控器 v3 — 按真实IP匹配（修复v2的bug）

v2的bug：netstat只显示IP不显示域名，匹配"api.siliconflow.cn"永远匹配不到。
v3修复：先解析 api.siliconflow.cn 的真实IP，再匹配netstat输出中的IP。

原理：
  1. 启动时解析 api.siliconflow.cn → IP列表
  2. 每2秒扫描 netstat -ano，找 ESTABLISHED 到这些IP:443 的连接
  3. 抓到后立刻用 wmic 查PID命令行
  4. 每5分钟查余额（外部调用检测）
"""
import subprocess, time, sys, datetime, os, re, socket, requests

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siliconflow_watch3.log")
API_KEY = "sk-oblkrvgfnogxovzpjhcrylgsfdoqjndunkoaqovxmwkruflz"
seen_pids = set()
last_balance = None

def resolve_ips():
    """解析SiliconFlow的真实IP"""
    ips = set()
    try:
        for res in socket.getaddrinfo("api.siliconflow.cn", 443, proto=socket.IPPROTO_TCP):
            ips.add(res[4][0])
    except Exception as e:
        pass
    return ips

SILICONFLOW_IPS = resolve_ips()

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def scan_connections():
    """扫本机到SiliconFlow IP的连接"""
    results = []
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                            timeout=10, errors="ignore", creationflags=0x08000000)
        for line in out.stdout.split("\n"):
            if "ESTABLISHED" not in line:
                continue
            parts = line.split()
            if len(parts) >= 5:
                remote = parts[2]  # 远程IP:端口
                pid = parts[-1]
                for ip in SILICONFLOW_IPS:
                    if remote.startswith(ip + ":"):
                        results.append((pid, remote))
                        break
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

log(f"💰 v3监控启动 | SiliconFlow IP: {sorted(SILICONFLOW_IPS)}")
last_check = 0
while True:
    # 1. 扫连接（每2秒）
    try:
        conns = scan_connections()
        for pid, remote in conns:
            if pid not in seen_pids:
                seen_pids.add(pid)
                cmd = get_cmdline(pid)
                log(f"🆕 抓到本机连接! PID={pid} | {remote} | CMD: {cmd}")
    except Exception as e:
        log(f"扫描异常: {e}")

    # 2. 查余额（每5分钟）
    now = time.time()
    if now - last_check > 300:
        last_check = now
        bal = get_balance()
        if bal is not None:
            if last_balance is None:
                log(f"💰 初始余额: {bal}")
            elif bal < last_balance - 0.001:
                log(f"🚨 余额减少! {last_balance} → {bal} (减少{last_balance-bal:.4f})")
                conns = scan_connections()
                if conns:
                    for pid, remote in conns:
                        cmd = get_cmdline(pid)
                        log(f"   ⚠️ 此刻连接: PID={pid} | {remote} | CMD: {cmd}")
                else:
                    log(f"   ⚠️ 本机此刻无连接 → 消耗来自【外部/平台侧】!")
            last_balance = bal

    time.sleep(2)
