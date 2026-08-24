#!/usr/bin/env python
"""🔍 SiliconFlow 幽灵调用监控器 — 抓"谁在用api.siliconflow.cn"

原理：
  1. 每2秒扫描 netstat -ano，找所有到 api.siliconflow.cn:443 的 ESTABLISHED 连接
  2. 一旦抓到，立刻用 wmic 查该 PID 的完整命令行
  3. 记录时间+PID+命令行到日志文件（含首次出现的标记）
  4. 常驻运行（Ctrl+C 或 kill 停止）

用法：
  python watch_siliconflow.py            # 前台运行
  python watch_siliconflow.py --bg      # 后台运行（自动写日志，不阻塞）

日志：scripts/siliconflow_watch.log（追加模式）
"""
import subprocess, time, sys, datetime, os, re

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siliconflow_watch.log")
INTERVAL = 2  # 每2秒扫一次
seen_pids = set()  # 已记录的PID（避免重复刷）

def scan_connections():
    """扫描所有到 SiliconFlow 的连接，返回 [(pid, remote_ip, state)]"""
    results = []
    try:
        # 用 -n 数字端口 + -b 含进程名（需要管理员），先试 -ano
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True,
            timeout=10, errors="ignore", creationflags=0x08000000  # 隐藏窗口
        )
        for line in out.stdout.split("\n"):
            if "api.siliconflow.cn" in line or ("ESTABLISHED" in line and ":443" in line and "127.0.0.1" not in line):
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    remote = parts[2] if len(parts) > 2 else "?"
                    results.append((pid, remote))
    except Exception as e:
        results.append(("ERR", str(e)))
    return results

def get_cmdline(pid):
    """获取进程完整命令行"""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:list"],
            capture_output=True, text=True, timeout=10, errors="ignore",
            creationflags=0x08000000
        )
        m = re.search(r"CommandLine=(.+)", out.stdout, re.DOTALL)
        return m.group(1).strip()[:300] if m else "(无命令行信息)"
    except Exception as e:
        return f"(查询失败: {e})"

def main():
    bg = "--bg" in sys.argv
    log_fh = open(LOG, "a", encoding="utf-8")
    log_fh.write(f"\n{'='*60}\n🔍 监控器启动 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n")
    log_fh.flush()

    print(f"🔍 监控中（每{INTERVAL}秒扫描），日志: {LOG}")
    print("  按 Ctrl+C 停止（后台运行则用 taskkill /PID 结束）")
    if bg:
        print("  后台模式：脚本已detach，日志持续记录")

    while True:
        try:
            conns = scan_connections()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for pid, remote in conns:
                if pid == "ERR":
                    log_fh.write(f"[{now}] ⚠️ 扫描异常: {remote}\n")
                    log_fh.flush()
                    continue
                # 过滤掉常见系统进程的443（Windows Update等）——只报SiliconFlow域名的
                if "api.siliconflow.cn" in remote:
                    cmdline = get_cmdline(pid)
                    marker = "🆕首次出现" if pid not in seen_pids else "重复"
                    seen_pids.add(pid)
                    msg = f"[{now}] {marker} PID={pid} | 连接: {remote} | 命令行: {cmdline}"
                    print(msg)
                    log_fh.write(msg + "\n")
                    log_fh.flush()
        except KeyboardInterrupt:
            log_fh.write(f"监控器停止 {datetime.datetime.now()}\n")
            log_fh.close()
            print("\n🛑 监控停止")
            sys.exit(0)
        except Exception as e:
            log_fh.write(f"[{datetime.datetime.now()}] 异常: {e}\n")
            log_fh.flush()
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
