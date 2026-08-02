#!/usr/bin/env python
"""抖音链接 → 下载 → 智谱GLM-4-Voice转写 → 待审核"""
import sys, os, json, requests, time, subprocess, base64
from pathlib import Path

sys.path.insert(0, os.path.expanduser(r"~/AppData/Local/hermes/AI-outbrain-2.0"))
from src.douyin_parser import DouyinParser

os.environ["PATH"] = r"C:\Users\Administrator\AppData\Local\hermes\bin;" + os.environ.get("PATH", "")

API_KEY = "4a9380755377494c8a9da4c4f07c6ed4.ox8tb8xjBJRkcAX6"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
REVIEW_DIR = r"C:\Vault\_待审核"
os.makedirs(REVIEW_DIR, exist_ok=True)

def transcribe_with_zhipu(wav_path, max_duration=600):
    """调用智谱GLM-4-Voice转写，按需分段"""
    import wave
    # 检查音频时长，超长则分段
    with wave.open(wav_path, 'rb') as w:
        total_frames = w.getnframes()
        rate = w.getframerate()
        duration = total_frames / rate
    
    print(f"音频时长: {duration:.0f}秒")
    
    # 分段处理（每段120秒）
    segments = max(1, int(duration / 120) + 1)
    all_text = []
    
    ffmpeg = r"C:\Users\Administrator\AppData\Local\hermes\bin\ffmpeg.exe"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    for i in range(segments):
        start = i * 120
        seg_wav = os.path.join(REVIEW_DIR, f"temp_seg_{i}.wav")
        subprocess.run([ffmpeg, "-y", "-ss", str(start), "-t", "120", "-i", wav_path,
                        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", seg_wav],
                       capture_output=True, check=True)
        
        with open(seg_wav, "rb") as f:
            wav_b64 = base64.b64encode(f.read()).decode()
        os.remove(seg_wav)
        
        payload = {
            "model": "glm-4-voice",
            "messages": [
                {"role": "user", "content": [
                    {"type": "input_audio", "input_audio": {"data": wav_b64, "format": "wav"}},
                    {"type": "text", "text": "请把这段音频里的语音完整转写成文字，只输出转写内容，不要任何多余的话。"}
                ]}
            ]
        }
        
        # 重试机制
        for attempt in range(3):
            try:
                r = requests.post(API_URL, headers=headers, json=payload, timeout=180)
                if r.status_code == 200:
                    text = r.json()["choices"][0]["message"].get("content", "")
                    all_text.append(text.strip())
                    print(f"  第{i+1}/{segments}段: {len(text)}字")
                    break
                else:
                    print(f"  第{i+1}段失败({r.status_code}): {r.text[:100]}，重试...")
                    time.sleep(3)
            except Exception as e:
                print(f"  第{i+1}段异常: {e}，重试...")
                time.sleep(3)
    
    return "\n".join(all_text)

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
    subprocess.run([r"C:\Users\Administrator\AppData\Local\hermes\bin\ffmpeg.exe", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1", wav_path, "-y"],
                   capture_output=True, check=True)
    os.remove(video_path)
    
    # --- 2. 智谱转写 ---
    t0 = time.time()
    text = transcribe_with_zhipu(wav_path)
    elapsed = time.time() - t0
    os.remove(wav_path)
    
    # --- 3. 生成待审核 ---
    date = time.strftime("%Y-%m-%d")
    review_path = os.path.join(REVIEW_DIR, f"douyin_{author}_{date}.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(f"---\nstatus: pending\nsource: 抖音\nauthor: {author}\ndate: {date}\nurl: {url}\n---\n\n## 📇 知识卡片\n\n**来源：** 抖音 @{author}\n**时长：** {duration}\n**转写：** 智谱GLM-4-Voice | {elapsed:.0f}秒 | {len(text)}字\n**日期：** {date}\n\n**📝 全文：**\n{text}\n")
    
    print("\n" + "=" * 50)
    print("📲 请发送以下内容给用户审核：")
    print("=" * 50)
    print(f"""
📥 有一条抖音内容待审核

🎬 @{author} | {duration}
👍 {stats.get('点赞','?')}  💬 {stats.get('评论','?')}  ⭐ {stats.get('收藏','?')}

📝 内容摘要：
{text[:300]}...

✅ 同意入库 → 我回"确认"
❌ 放弃 → 我回"丢弃"
""")
    print(f"📂 待审核文件: {review_path}")
    print(f"📊 全文 {len(text)} 字")
    return review_path, text

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else input("抖音链接: ")
    process_douyin(url)
