#!/usr/bin/env python
"""小红书图文笔记抓取工具：短链解析 → 提取图片URL → 下载图片 → OCR识别正文
用法:
  python xhs2text.py <小红书链接或短链> [输出目录]
输出: 图片存 <输出目录>/, 正文打印到 stdout (自动调用 ocr_image.py 识别)
"""
import sys, os, re, json, ssl, subprocess, urllib.request, urllib.parse

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    return urllib.request.urlopen(req, timeout=timeout, context=CTX)

def resolve_short(url):
    """短链(xhslink.cn) → 真实作品页URL"""
    resp = fetch(url)
    return resp.geturl()

def extract_images(html):
    """从SSR HTML提取正文图片URL (h5_1080高清版)"""
    imgs = re.findall(r'https?://sns-webpic[^"\']*?xhscdn\.com[^"\']*?(?:jpg|jpeg|png|webp)', html)
    imgs = [i.replace("\\u002F", "/") for i in imgs]
    seen, out = set(), []
    for i in imgs:
        if i not in seen and "h5_1080" in i and "avatar" not in i:
            seen.add(i)
            out.append("https://" + i if i.startswith("sns") else i)
    return out

def download(url, path):
    resp = fetch(url, timeout=30)
    with open(path, "wb") as f:
        f.write(resp.read())

def ocr(path):
    """调用 ocr_image.py 识别单张图"""
    r = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "ocr_image.py"), path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.stdout

def main():
    if len(sys.argv) < 2:
        print("用法: python xhs2text.py <链接> [输出目录]")
        sys.exit(1)
    link = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SCRIPT_DIR, "xhs_tmp")
    os.makedirs(outdir, exist_ok=True)

    print("🔗 解析链接...", flush=True)
    if "xhslink" in link:
        page_url = resolve_short(link)
        print("真实地址:", page_url, flush=True)
    else:
        page_url = link

    print("📥 抓取页面...", flush=True)
    html = fetch(page_url).read().decode("utf-8", errors="replace")
    m = re.search(r"<title>(.*?)</title>", html)
    title_m = re.search(r'"title":"([^"]+)"', html)
    title = title_m.group(1).replace("\\u002F", "/") if title_m else (m.group(1) if m else "未知名")
    print("标题:", title, flush=True)

    imgs = extract_images(html)
    print(f"🖼️ 发现 {len(imgs)} 张图", flush=True)
    texts = []
    for i, u in enumerate(imgs):
        path = os.path.join(outdir, f"xhs_{i+1}.jpg")
        print(f"  下载图{i+1}...", flush=True)
        try:
            download(u, path)
        except Exception as e:
            print(f"  图{i+1}下载失败: {e}", flush=True)
            continue
        print(f"  OCR识别图{i+1}...", flush=True)
        t = ocr(path)
        texts.append(t)

    print("\n===== 全文内容 =====")
    for i, t in enumerate(texts):
        print(f"--- 图{i+1} ---")
        print(t.strip())
        print()

if __name__ == "__main__":
    main()
