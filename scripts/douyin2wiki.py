#!/usr/bin/env python
"""抖音链接 → 下载 → 云端转写 → 纠错 → 直接存Raw（带"待审-"前缀）
新流程（2026-08-10 规范）：
  转写完成 → 直接存Raw（文件名"待审-日期-作者-主题.md"）→ 内容永不丢失
  晚上审核 → 做卡片 → 去掉"待审-"前缀 = 已入库
  9点推送/待办 → 扫描"待审-"前缀 = 待审核清单

2026-08-14 升级：新增TikHub解析通道（付费API，绕过抖音Argus反爬）
  流程：短链重定向拿aweme_id → TikHub拿直链 → 下载 → ffmpeg → ASR → 纠错 → 存Raw
  TikHub失败 → 自动降级现有DouyinParser（三套方案）
"""
import sys, os, json, requests, time, subprocess, uuid, re

sys.path.insert(0, os.path.expanduser(r"~/AppData/Local/hermes/AI-outbrain-2.0"))
from src.douyin_parser import DouyinParser

os.environ["PATH"] = r"C:\Users\Administrator\AppData\Local\hermes\bin;" + os.environ.get("PATH", "")

RAW_ROOT = r"C:\Vault\Raw（原始资料）"

# TikHub 配置（2026-08-14 阿念注册）
# 优先读环境变量（TIKHUB_API_KEY / TIKHUB_BASE_URL），兜底用硬编码
TIKHUB_API_KEY = os.environ.get("TIKHUB_API_KEY", "r7AzL/Eh2VGBlnypTd6+kU3fDiGmasg/5kCGjUW4CPG0lQigHHjYTAuVNw==")
TIKHUB_BASE_URL = os.environ.get("TIKHUB_BASE_URL", "https://api.tikhub.dev")
TIKHUB_API = f"{TIKHUB_BASE_URL}/api/v1/douyin/web/fetch_one_video"


def extract_aweme_id(url: str) -> str:
    """短链重定向拿aweme_id（数字ID）"""
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW)"}, timeout=15, allow_redirects=True)
    m = re.search(r'/video/(\d+)', r.url)
    if m:
        return m.group(1)
    # 直接URL可能已含ID
    m2 = re.search(r'(\d{15,20})', url)
    if m2:
        return m2.group(1)
    raise ValueError(f"无法提取aweme_id: {r.url[:80]}")


def parse_with_tikhub(url: str) -> dict:
    """TikHub解析：返回 {video_url, title, author, aweme_id}"""
    aweme_id = extract_aweme_id(url)
    resp = requests.get(TIKHUB_API, params={"aweme_id": aweme_id}, headers={
        "Authorization": f"Bearer {TIKHUB_API_KEY}",
    }, timeout=30)
    d = resp.json()
    if d.get("code") != 200:
        raise RuntimeError(f"TikHub返回错误: {d.get('message', d)}")
    detail = d["data"]["aweme_detail"]
    video = detail.get("video", {})
    urls = video.get("play_addr", {}).get("url_list", [])
    if not urls:
        raise RuntimeError("TikHub未返回视频直链（可能权限限制）")
    return {
        "video_url": urls[0],
        "title": detail.get("desc", "") or f"douyin_{aweme_id}",
        "author": detail.get("author", {}).get("nickname", ""),
        "aweme_id": aweme_id,
    }


def download_video(video_url: str, output_dir: str) -> str:
    """下载视频到临时文件，返回路径（带重试+断点续传）"""
    uid = uuid.uuid4().hex[:8]
    path = os.path.join(output_dir, f"v_{uid}.mp4")
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.douyin.com/",
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 断点续传：如果已有部分文件，用Range续传
            headers_range = dict(headers)
            existing = os.path.getsize(path) if os.path.exists(path) else 0
            if existing > 0:
                headers_range["Range"] = f"bytes={existing}-"
            r = requests.get(video_url, headers=headers_range, timeout=180, stream=True)
            if r.status_code == 416:  # Range不满足，重头下
                os.remove(path)
                existing = 0
                r = requests.get(video_url, headers=headers, timeout=180, stream=True)
            r.raise_for_status()
            mode = "ab" if existing > 0 else "wb"
            with open(path, mode) as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            # 验证文件有效（MP4头）
            if os.path.getsize(path) < 10000:
                raise RuntimeError("文件过小，下载可能不完整")
            return path
        except Exception as e:
            print(f"  ⚠️ 下载第{attempt+1}次失败: {str(e)[:60]}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def extract_audio(video_path: str) -> str:
    """ffmpeg提取音频（wav 16k单声道，适配SiliconFlow ASR）"""
    wav_path = video_path.replace(".mp4", ".wav")
    subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1", wav_path, "-y"],
                   capture_output=True, check=True)
    return wav_path


def process_douyin(url: str):
    """主流程：TikHub优先 → 降级DouyinParser → 下载 → 转写 → 存Raw"""
    tmp_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "douyin_wiki")
    os.makedirs(tmp_dir, exist_ok=True)
    video_path = None
    wav_path = None
    
    try:
        # 第一步：解析拿直链（TikHub优先）
        info = None
        tikhub_ok = False
        try:
            info = parse_with_tikhub(url)
            tikhub_ok = True
            print(f"✅ TikHub解析成功: {info['title'][:40]}")
        except Exception as e:
            print(f"⚠️ TikHub失败({str(e)[:60]})，降级DouyinParser...")
            parser = DouyinParser()
            info = parser.parse(url)
            if info:
                info = {
                    "video_url": info.get("video_url"),
                    "title": info.get("title", ""),
                    "author": info.get("author", ""),
                }
        
        if not info or not info.get("video_url"):
            raise RuntimeError("所有解析方案均失败")
        
        # 第二步：下载视频
        print(f"📥 下载视频...")
        video_path = download_video(info["video_url"], tmp_dir)
        print(f"✅ 下载完成: {os.path.getsize(video_path)/1024:.0f}KB")
        
        # 第三步：提取音频
        print(f"🔊 提取音频...")
        wav_path = extract_audio(video_path)
        print(f"✅ 音频就绪: {os.path.getsize(wav_path)/1024:.0f}KB")
        
        # 第四步：转写（SiliconFlow，失败降级本地whisper）
        try:
            from transcribe_siliconflow import transcribe
            print(f"🗣️ 转写中（SiliconFlow）...")
            text = transcribe(wav_path)
        except Exception as e:
            print(f"⚠️ SiliconFlow转写失败({str(e)[:50]})，降级本地whisper...")
            import whisper
            model = whisper.load_model("tiny", device="cpu")
            result = model.transcribe(wav_path, language="zh")
            text = result.get("text", "")
            print(f"✅ 本地whisper转写完成 {len(text)}字")
        
        # 第五步：纠错
        from fix_transcript import load_corrections, correct_text
        corrections = load_corrections()
        if corrections:
            text = correct_text(text, corrections)
        
        # 第六步：存Raw（待审-前缀）
        author = info.get("author", "未知")
        title = info.get("title", "未命名")[:20]
        safe_title = re.sub(r'[\\/:*?"<>|\s]+', '', title)
        date = time.strftime("%Y-%m-%d")
        # 按领域分类（简单规则）
        domain_map = {
            "投资|价值|股票|估值|财报|期权|理财": "投资/投资理念",
            "健康|养生|饮食|运动|睡眠": "个人/健康",
            "孩子|教育|育儿|家长": "个人/学习方法",
            "电商|AI|带货|直播": "电商/AI应用",
        }
        target_dir = "投资/投资理念"
        for kw, dirname in domain_map.items():
            if re.search(kw, title + author):
                target_dir = dirname
                break
        
        target_dir = os.path.join(RAW_ROOT, target_dir)
        os.makedirs(target_dir, exist_ok=True)
        filename = f"待审-{date}-{author}-{safe_title}.md"
        target = os.path.join(target_dir, filename)
        
        content = f"""---
status: pending
source: 抖音
author: {author}
date: {date}
url: {url}
domain: 投资
---

## 📇 知识卡片

**来源：** 抖音 @{author}
**日期：** {date}
**状态：** ⏳ 待审核（文件名带"待审-"前缀，审核入库后去掉前缀）

**📌 摘要：**
{text[:200]}

**🏷️ 建议分类：** {target_dir.replace(RAW_ROOT, '')}

**📝 全文（原始转写+纠错）：**
{text}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 已存: {target}")
        print(f"📊 全文 {len(text)} 字")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        raise
    finally:
        # 清理临时文件
        for p in [video_path, wav_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python douyin2wiki.py <抖音链接>")
        sys.exit(1)
    process_douyin(sys.argv[1])
