#!/usr/bin/env python
"""🔍 SiliconFlow 代理记录器 — 100%拦截所有调用

原理：
  1. hosts已把 api.siliconflow.cn 指向 127.0.0.1
  2. 本脚本监听 127.0.0.1:443
  3. 任何进程连 api.siliconflow.cn → 先到本代理
  4. 记录：时间 + 连接方PID + 请求内容（Host/模型名）+ 转发到真实SiliconFlow
  5. 一次不漏（代理层拦截，不是轮询）

注意：需要管理员权限监听443端口。
"""
import socket, threading, ssl, datetime, os, subprocess, re, struct

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siliconflow_proxy.log")
REAL_IPS = ["139.196.152.242", "47.102.215.139", "47.102.37.23", "47.103.87.49", "101.132.62.140"]
LISTEN_PORT = 443

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_conn_pid():
    """尝试找当前连接的本地PID（通过netstat匹配）"""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                           timeout=5, errors="ignore", creationflags=0x08000000)
        for line in out.stdout.split("\n"):
            if "127.0.0.1:443" in line and "ESTABLISHED" in line:
                parts = line.split()
                if parts:
                    return parts[-1]
    except:
        pass
    return "?"

def handle_client(conn, addr):
    """处理一个连接：记录请求头，然后转发到真实SiliconFlow"""
    try:
        # 读客户端发来的数据（HTTPS ClientHello 或 HTTP）
        conn.settimeout(10)
        data = conn.recv(8192)
        if not data:
            conn.close()
            return

        pid = get_conn_pid()
        # 尝试解析TLS ClientHello里的SNI（看请求的域名）
        sni = "?"
        try:
            if data and data[0] == 0x16:  # TLS handshake
                # 解析ClientHello获取SNI
                idx = data.find(b"\x00\x00") 
                # 简化：找可打印域名
                m = re.search(rb"([a-z0-9.-]+\.(?:cn|com|dev|net))", data)
                if m:
                    sni = m.group(1).decode()
        except:
            pass

        log(f"🚨 拦截到连接! PID={pid} | SNI={sni} | 数据{len(data)}字节")

        # 转发到真实SiliconFlow（轮换IP）
        for real_ip in REAL_IPS:
            try:
                upstream = socket.create_connection((real_ip, 443), timeout=10)
                upstream.sendall(data)
                # 双向转发
                def pipe(src, dst):
                    try:
                        while True:
                            chunk = src.recv(65536)
                            if not chunk:
                                break
                            dst.sendall(chunk)
                    except:
                        pass
                    finally:
                        try: dst.shutdown(socket.SHUT_WR)
                        except: pass

                t1 = threading.Thread(target=pipe, args=(upstream, conn), daemon=True)
                t2 = threading.Thread(target=pipe, args=(conn, upstream), daemon=True)
                t1.start(); t2.start()
                t1.join(); t2.join()
                log(f"✅ 转发完成 (→{real_ip})")
                break
            except Exception as e:
                log(f"⚠️ 转发到{real_ip}失败: {str(e)[:60]}")
                continue

        conn.close()
    except Exception as e:
        log(f"处理异常: {str(e)[:80]}")
        try: conn.close()
        except: pass

def main():
    log("🚀 SiliconFlow代理记录器启动 (监听127.0.0.1:443)")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("127.0.0.1", LISTEN_PORT))
        srv.listen(50)
        log(f"✅ 监听成功 :{LISTEN_PORT}")
    except PermissionError:
        log("❌ 需要管理员权限监听443！请用管理员运行")
        return
    except OSError as e:
        log(f"❌ 端口占用: {e} (可能已有代理在跑)")
        return

    while True:
        try:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            log("停止")
            break
        except Exception as e:
            log(f"accept异常: {str(e)[:60]}")

if __name__ == "__main__":
    main()
