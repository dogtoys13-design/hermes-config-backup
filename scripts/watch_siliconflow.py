#!/usr/bin/env python
"""监控到 SiliconFlow 的 API 调用（抓GLM-5.2幽灵调用源）
用法: python watch_siliconflow.py [分钟数]
原理: 通过修改 hosts 或代理不现实，改用轮询 netstat 抓 ESTABLISHED 连接到
api.siliconflow.cn 的进程PID，配合进程命令行定位调用方。
"""
import subprocess, time, sys, datetime, os

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 120  # 默认监控120分钟
LOG = os.path.join(os.path.dirname(__file__), "siliconflow_watch.log")

def find_siliconflow_connections():
    """找所有连接到SiliconFlow的本地进程"""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=30, errors="ignore")
        lines = out.stdout.split("\n")
        results = []
        for line in lines:
            if "api.siliconflow.cn" in line or ("ESTABLISHED" in line and ":443" in line):
                # 提取本地PID
                parts = line.split()
                if len(parts) >= 5 and parts[4].isdigit():
                    results.append((parts[4], line.strip()))
        return results
    except Exception as e:
        return [("ERR", str(e))]

def get_process_cmd(pid):
    """获取进程命令行"""
    try:
        out = subprocess.run(["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                           capture_output=True, text=True, timeout=15, errors="ignore")
        lines = [l.strip() for l in out.stdout.split("\n") if l.strip() and "CommandLine" not in l]
        return lines[0][:200] if lines else "?"
    except:
        return "?"

print(f"🔍 开始监控 SiliconFlow 连接（{DURATION}分钟），日志: {LOG}")
start = time.time()
with open(LOG, "a", encoding="utf-8") as log:
    log.write(f"\n=== 监控开始 {datetime.datetime.now()} ===\n")
    while time.time() - start < DURATION * 60:
        conns = find_siliconflow_connections()
        now = datetime.datetime.now().strftime("%H:%M:%S")
        for pid, line in conns:
            cmd = get_process_cmd(pid)
            msg = f"[{now}] PID={pid} | {line[:80]} | CMD: {cmd}"
            print(msg)
            log.write(msg + "\n")
            log.flush()
        time.sleep(30)  # 每30秒扫一次
print("监控结束")
