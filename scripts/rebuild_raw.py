#!/usr/bin/env python
"""批量重抓14条断链抖音，转写纠错后存Raw（修复source断链）"""
import sys, os, time, subprocess, requests, uuid, re, json

sys.path.insert(0, os.path.expanduser(r"~/AppData/Local/hermes/AI-outbrain-2.0"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] = r"C:\Users\Administrator\AppData\Local\hermes\bin;" + os.environ.get("PATH", "")

from src.douyin_parser import DouyinParser
from transcribe_siliconflow import transcribe
from fix_transcript import load_corrections, correct_text

RAW_ROOT = r"C:\Vault\Raw（原始资料）"

# 14条：卡片 → 链接 → Raw目标路径
TASKS = [
    ("成瘾性行业与投资", "https://v.douyin.com/7udzx7Pb5hI/", "投资/2026-08-03-douyin-全哥价值投资-成瘾性.md"),
    ("人性的疯狂与认知边界", "https://v.douyin.com/xKJuPan1sSs/", "投资/2026-08-03-douyin-全哥-牛顿人性疯狂.md"),
    ("洞察力是练出来的", "https://v.douyin.com/TxsQF5dr6oA/", "投资/2026-08-03-douyin-全嫂在美国-洞察力.md"),
    ("人生阶段的决策与为自己而活", "https://v.douyin.com/QqONTPNBu-4/", "个人/2026-08-03-douyin-全嫂在美国-人生阶段感悟.md"),
    ("美股为什么难跌养老金托底", "https://v.douyin.com/wrZMenKZb5k/", "投资/2026-08-03-douyin-全哥-美股难跌401K.md"),
    ("情绪负债与AI参与门槛", "https://v.douyin.com/MJvItMYoZN4/", "投资/2026-08-04-douyin-全哥价值投资-情绪负债AI门槛.md"),
    ("时间的价值你的时间属于谁", "https://www.iesdouyin.com/share/video/7666998218072631887/", "投资/2026-08-06-douyin-全哥-时间的价值.md"),
    ("内耗时代的生存法则", "https://v.douyin.com/JpRiMz-BZ9k/", "投资/2026-08-08-douyin-全哥-内耗时代生存法则.md"),
    ("成为顶尖公司的股东不做牛马", "https://v.douyin.com/U6nENf5KLoY/", "个人/2026-08-08-douyin-全嫂在美国-股东思维.md"),
    ("科比坠机的教训敬畏心与风险分级", "https://v.douyin.com/tKTSI_d3SUs/", "个人/2026-08-08-douyin-北方的wolf-科比坠机教训.md"),
    ("财富三阶段活下来活得好活得久", "https://www.iesdouyin.com/share/video/7670232478062604169/", "个人/2026-08-08-douyin-全嫂在美国-财富三阶段.md"),
    ("驴拉磨的思维牢笼", "https://v.douyin.com/6Bf38yjqfHg/", "个人/2026-08-09-douyin-全嫂在美国-驴拉磨思维牢笼.md"),
    ("不懂不碰赚钱比赔钱更危险", "https://v.douyin.com/s7-OAbmmxFU/", "投资/2026-08-09-douyin-波咕日记-不懂不碰.md"),
    ("非对称机会与诺亚方舟", "https://v.douyin.com/gkYRNBSkR5o/", "投资/2026-08-09-douyin-诺夫财知道-非对称机会诺亚方舟.md"),
]

corrections = load_corrections()
parser = DouyinParser()
tmp_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "douyin_reback")
os.makedirs(tmp_dir, exist_ok=True)

results = []
for card, url, rel_path in TASKS:
    try:
        print(f"\n🔄 [{card}] 下载中...", flush=True)
        info = parser.parse(url)
        author = info["author_name"]
        r = requests.get(info["video_url"], headers=info["download_headers"], timeout=120)
        uid = uuid.uuid4().hex[:8]
        video_path = os.path.join(tmp_dir, f"v_{uid}.mp4")
        with open(video_path, "wb") as f:
            f.write(r.content)

        wav_path = os.path.join(tmp_dir, f"a_{uid}.wav")
        subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                        "-ar", "16000", "-ac", "1", wav_path, "-y"],
                       capture_output=True, check=True)
        os.remove(video_path)

        text = transcribe(wav_path)
        os.remove(wav_path)
        if corrections:
            text = correct_text(text, corrections)

        # 存Raw
        target = os.path.join(RAW_ROOT, rel_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        content = f"""---
status: recovered
source: 抖音
author: {author}
date: 2026-08-10（重新抓取补存）
url: {url}
domain: 投资
---

## 📇 知识卡片

**来源：** 抖音 @{author}（2026-08-10 重新抓取补存，修复source断链）
**日期：** 2026-08-10

**📝 全文（原始转写+纠错）：**
{text}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        results.append(f"✅ [{card}] 已存: {rel_path} ({len(text)}字)")
        print(results[-1], flush=True)
    except Exception as e:
        results.append(f"❌ [{card}] 失败: {e}")
        print(results[-1], flush=True)

print("\n" + "=" * 50)
print(f"完成: {sum(1 for r in results if r.startswith('✅'))}/14 成功")
for r in results:
    print(r)
