#!/usr/bin/env python
"""抖音链接 → 下载 → Whisper转写 → 生成知识卡片 → 待审核"""
import sys, os, json, requests, time, subprocess, whisper
from pathlib import Path

sys.path.insert(0, os.path.expanduser(r"~/AppData/Local/hermes/AI-outbrain-2.0"))
from src.douyin_parser import DouyinParser

os.environ["PATH"] = r"C:\Users\Administrator\AppData\Local\hermes\bin;" + os.environ.get("PATH", "")

REVIEW_DIR = r"C:\Vault\_待审核"
OUT_DIR = r"C:\Vault\00_Raw"
os.makedirs(REVIEW_DIR, exist_ok=True)

def process_douyin(url):
    # --- 1. 下载 ---
    print("🔍 解析抖音...")
    info = DouyinParser().parse(url)
    author = info["author_name"]
    duration = info["duration_str"]
    stats = info["statistics"]
    
    r = requests.get(info["video_url"], headers=info["download_headers"], timeout=120)
    video_path = os.path.join(REVIEW_DIR, "temp_video.mp4")
    with open(video_path, "wb") as f:
        f.write(r.content)
    
    wav_path = os.path.join(REVIEW_DIR, "temp_audio.wav")
    subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1", wav_path, "-y"],
                   capture_output=True, check=True)
    os.remove(video_path)
    
    # --- 2. 转写（云端SenseVoice，替代本地Whisper） ---
    t0 = time.time()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from transcribe_siliconflow import transcribe
    text = transcribe(wav_path)
    elapsed = time.time() - t0
    os.remove(wav_path)
    
    # --- 3. 生成知识卡片 ---
    ts = time.strftime("%Y-%m-%d %H:%M")
    date = time.strftime("%Y-%m-%d")
    
    # 简单自动分类（根据关键词）
    domain = "投资"
    subdomain = "投资理念"
    if any(k in text for k in ["期权", "put", "call", "卖铺", "卖靠", "行权"]):
        domain, subdomain = "投资", "实操复盘"
    elif any(k in text for k in ["代码", "铺货", "软件", "自动化"]):
        domain, subdomain = "电商", "AI应用"
    elif any(k in text for k in ["教育", "学习", "人生", "规划", "运动"]):
        domain, subdomain = "个人", "学习方法"
    
    card = f"""## 📇 知识卡片

**来源：** 抖音 @{author}
**时长：** {duration}（{stats.get('点赞','?')}赞 / {stats.get('收藏','?')}收藏）
**转写：** SenseVoice | {elapsed:.0f}秒 | {len(text)}字
**日期：** {date}

**📌 摘要：**
{text[:200]}...

**🏷️ 建议分类：** {domain} → {subdomain}
**📂 入库路径：** Raw（原始资料）/{domain}/{subdomain}/{date}-douyin-{author}.md

**📝 全文：**
{text}
"""
    
    # 保存待审核
    review_path = os.path.join(REVIEW_DIR, f"douyin_{author}_{date}.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(f"---\nstatus: pending\nsource: 抖音\nauthor: {author}\ndate: {date}\nurl: {url}\n---\n\n{card}\n")
    
    # 输出给AI发微信
    print("\n" + "=" * 50)
    print("📲 请发送以下内容给用户审核：")
    print("=" * 50)
    print(f"""
📥 有一条抖音内容待审核

🎬 @{author} | {duration}
👍 {stats.get('点赞','?')}  💬 {stats.get('评论','?')}  ⭐ {stats.get('收藏','?')}

📝 内容摘要：
{text[:300]}...

🏷️ 建议归类：{domain} → {subdomain}

✅ 同意入库 → 我回"确认"
❌ 放弃 → 我回"丢弃"
✏️ 改分类 → 我回"改到XX"
""")
    
    print(f"📂 待审核文件: {review_path}")
    print(f"📊 全文 {len(text)} 字")
    return card, review_path, domain, subdomain, text

if __name__ == "__main__":
    process_douyin(sys.argv[1])
