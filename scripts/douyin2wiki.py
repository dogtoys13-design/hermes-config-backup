#!/usr/bin/env python
"""抖音链接 → 下载 → 云端转写 → 纠错 → 直接存Raw（带"待审-"前缀）
新流程（2026-08-10 规范）：
  转写完成 → 直接存Raw（文件名"待审-日期-作者-主题.md"）→ 内容永不丢失
  晚上审核 → 做卡片 → 去掉"待审-"前缀 = 已入库
  9点推送/待办 → 扫描"待审-"前缀 = 待审核清单
"""
import sys, os, json, requests, time, subprocess, uuid, re

sys.path.insert(0, os.path.expanduser(r"~/AppData/Local/hermes/AI-outbrain-2.0"))
from src.douyin_parser import DouyinParser

os.environ["PATH"] = r"C:\Users\Administrator\AppData\Local\hermes\bin;" + os.environ.get("PATH", "")

RAW_ROOT = r"C:\Vault\Raw（原始资料）"
os.makedirs(RAW_ROOT, exist_ok=True)

def detect_domain(text):
    """根据关键词自动分类：投资/电商/个人"""
    if any(k in text for k in ["期权", "put", "call", "卖铺", "卖靠", "行权", "仓位"]):
        return "投资", "实操复盘"
    if any(k in text for k in ["代码", "铺货", "软件", "自动化", "AI应用", "电商"]):
        return "电商", "AI应用"
    if any(k in text for k in ["教育", "学习", "人生", "规划", "运动", "育儿", "孩子"]):
        return "个人", "学习方法"
    return "投资", "投资理念"

def process_douyin(url):
    # --- 1. 下载 ---
    print("🔍 解析抖音...")
    info = DouyinParser().parse(url)
    author = info["author_name"]
    duration = info["duration_str"]
    stats = info["statistics"]

    r = requests.get(info["video_url"], headers=info["download_headers"], timeout=120)
    uid = uuid.uuid4().hex[:8]
    tmp_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "douyin_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    video_path = os.path.join(tmp_dir, f"video_{uid}.mp4")
    with open(video_path, "wb") as f:
        f.write(r.content)
    print(f"✅ 视频已下载: {len(r.content)/1024:.0f}KB")

    wav_path = os.path.join(tmp_dir, f"audio_{uid}.wav")
    subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1", wav_path, "-y"],
                   capture_output=True, check=True)
    os.remove(video_path)
    print(f"✅ 音频就绪: {os.path.getsize(wav_path)/1024:.0f}KB")

    # --- 2. 转写（云端SenseVoice） ---
    t0 = time.time()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from transcribe_siliconflow import transcribe
    from fix_transcript import load_corrections, correct_text
    text = transcribe(wav_path)
    elapsed = time.time() - t0
    os.remove(wav_path)
    print(f"📊 转写完成: {elapsed:.0f}秒, {len(text)}字")

    # --- 2.5 自动纠错（专有名词纠错表） ---
    corrections = load_corrections()
    if corrections:
        text = correct_text(text, corrections)
        print(f"🔧 已按纠错表替换 {len(corrections)} 类专有名词")

    # --- 3. 直接存Raw（带"待审-"前缀，内容永不丢失） ---
    date = time.strftime("%Y-%m-%d")
    domain, subdomain = detect_domain(text)

    # 从文本提取简短主题（前12个字）
    clean = re.sub(r'[🎼😊😡\s]', '', text[:80])
    topic = clean[:12] or "未命名"

    target_dir = os.path.join(RAW_ROOT, domain, subdomain)
    os.makedirs(target_dir, exist_ok=True)

    # 文件名：待审-日期-作者-主题.md（加序号防同作者同日覆盖）
    base = os.path.join(target_dir, f"待审-{date}-{author}-{topic}")
    raw_path = base + ".md"
    seq = 2
    while os.path.exists(raw_path):
        raw_path = f"{base}_{seq}.md"
        seq += 1

    content = f"""---
status: pending
source: 抖音
author: {author}
date: {date}
url: {url}
domain: {domain}
---

## 📇 知识卡片

**来源：** 抖音 @{author}
**时长：** {duration}（{stats.get('点赞','?')}赞 / {stats.get('收藏','?')}收藏）
**转写：** SenseVoice | {elapsed:.0f}秒 | {len(text)}字
**日期：** {date}
**状态：** ⏳ 待审核（文件名带"待审-"前缀，审核入库后去掉前缀）

**📌 摘要：**
{text[:200]}...

**🏷️ 建议分类：** {domain} → {subdomain}

**📝 全文（原始转写，未精修）：**
{text}
"""
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📂 已存Raw（待审）: {raw_path}")

    # --- 4. 输出给AI发微信 ---
    print("\n" + "=" * 50)
    print("📲 请发送以下内容给用户审核：")
    print("=" * 50)
    print(f"""
📥 有一条抖音内容已转写并存Raw待审核

🎬 @{author} | {duration}
👍 {stats.get('点赞','?')}  💬 {stats.get('评论','?')}  ⭐ {stats.get('收藏','?')}

📝 内容摘要：
{text[:300]}...

🏷️ 建议归类：{domain} → {subdomain}
📂 已存: Raw（原始资料）/{domain}/{subdomain}/{os.path.basename(raw_path)}

✅ 同意入库 → 我回"确认"
❌ 放弃 → 我回"丢弃"
✏️ 改分类 → 我回"改到XX"
""")

    print(f"📊 全文 {len(text)} 字")
    return content, raw_path, domain, subdomain, text

if __name__ == "__main__":
    process_douyin(sys.argv[1])
