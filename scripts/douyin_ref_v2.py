"""
抖音 (Douyin) 视频内容提取器。

实现方案：
1. 解析短链接 → 获取真实视频 ID
2. 解析视频页面 → 获取标题、描述、作者
3. 用 yt-dlp 下载音频
4. 调用 transcriber 转文字

依赖: yt-dlp, faster-whisper, ffmpeg
"""

import json
import os
import re
import subprocess
import tempfile
from typing import Optional

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def resolve_short_url(url: str) -> Optional[str]:
    """解析抖音短链接（v.douyin.com/xxx），获取真实跳转 URL。"""
    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=15)
        return resp.url
    except Exception as e:
        print(f"[douyin] 短链接解析失败: {e}")
        return None


def extract_video_id(url: str) -> Optional[str]:
    """从抖音 URL 中提取 video_id。"""
    # 标准格式: douyin.com/video/{id}
    match = re.search(r"douyin\.com/video/(\d+)", url)
    if match:
        return match.group(1)

    # 短链接格式: v.douyin.com/{id}（需要解析后才能拿到 video_id）
    return None


def parse_mobile_page(video_url: str) -> dict:
    """解析抖音页面，提取视频信息。

    使用移动端页面获取标题、描述、作者等。
    """
    mobile_headers = HEADERS.copy()
    mobile_headers["User-Agent"] = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    )

    try:
        resp = requests.get(video_url, headers=mobile_headers, timeout=15)
        html = resp.text

        # 尝试从 HTML 的 <script id="RENDER_DATA"> 中提取
        match = re.search(
            r'<script id="RENDER_DATA"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if match:
            # 抖音 RENDER_DATA 是 URL 编码的 JSON
            import urllib.parse
            raw = match.group(1)
            decoded = urllib.parse.unquote(raw)
            data = json.loads(decoded)

            # 尝试提取视频信息（结构会变，需要健壮处理）
            return _extract_from_render_data(data)

        # 降级：提取 og:title 等 meta
        title = _extract_meta(html, 'property="og:title"')
        description = _extract_meta(html, 'property="og:description"')

        return {
            "title": title or "未知标题",
            "description": description or "",
            "author": "",
            "duration": 0,
        }

    except Exception as e:
        return {"error": f"页面解析失败: {e}"}


def _extract_from_render_data(data: dict) -> dict:
    """从抖音 RENDER_DATA JSON 中递归查找视频信息。"""
    try:
        # 尝试常见路径
        # 结构可能类似:
        # data -> __DEFAULT_SCOPE__ -> webapp.video-detail -> ...
        default = data.get("__DEFAULT_SCOPE__", {})
        if isinstance(default, dict):
            for key in default:
                item = default[key]
                if isinstance(item, dict):
                    video_info = item.get("videoInfoRes", {})
                    if video_info:
                        vid = video_info.get("item_list", [{}])[0]
                        return {
                            "title": vid.get("desc", "") or vid.get("title", ""),
                            "description": vid.get("desc", ""),
                            "author": (
                                vid.get("author", {})
                                .get("nickname", "")
                            ),
                            "duration": vid.get("video", {}).get("duration", 0),
                            "author_id": (
                                vid.get("author", {}).get("unique_id", "")
                            ),
                        }
    except Exception:
        pass
    return {}


def _extract_meta(html: str, pattern: str) -> Optional[str]:
    """从 HTML 中提取 meta 标签内容。"""
    match = re.search(
        rf'<meta\s+{pattern}\s+content="([^"]*)"',
        html,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def download_audio(url: str, output_dir: str = None) -> Optional[str]:
    """用 yt-dlp 下载抖音视频的音频。

    Args:
        url: 抖音视频链接
        output_dir: 输出目录（默认临时目录）

    Returns:
        音频文件路径，失败返回 None
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="douyin_audio_")

    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    try:
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",  # 最佳质量
            "--no-playlist",
            "-o", output_template,
            url,
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)

        # 找到生成的 mp3 文件
        for f in os.listdir(output_dir):
            if f.endswith(".mp3"):
                return os.path.join(output_dir, f)

        return None
    except subprocess.CalledProcessError as e:
        print(f"[douyin] yt-dlp 下载失败: {e.stderr}")
        return None
    except FileNotFoundError:
        print("[douyin] yt-dlp 未安装，请执行: pip install yt-dlp")
        return None
    except subprocess.TimeoutExpired:
        print("[douyin] 下载超时（>120秒）")
        return None


def get_info_via_ytdlp(url: str) -> Optional[dict]:
    """使用 yt-dlp 获取视频元数据（最可靠的方式）。

    直接使用 yt_dlp Python 库，兼容短链接和长链接。
    """
    try:
        import yt_dlp

        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_playlist': True,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None

            return {
                "title": info.get("title", ""),
                "uploader": info.get("uploader", "") or info.get("creator", ""),
                "description": (info.get("description", "") or "").strip(),
                "duration": info.get("duration", 0),
                "id": info.get("id", ""),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "comment_count": info.get("comment_count", 0),
                "upload_date": info.get("upload_date", ""),
                "thumbnail": info.get("thumbnail", ""),
            }
    except ImportError:
        print("[douyin] yt-dlp 未安装 (pip install yt-dlp)")
        return None
    except Exception as e:
        print(f"[douyin] yt-dlp 获取失败: {e}")
        return None


async def extract(url: str) -> dict:
    """从抖音视频链接提取内容。

    流程:
    1. 解析短链接 → 获取真实 URL
    2. 用 yt-dlp 获取视频信息（最可靠）
    3. 降级：页面解析
    4. （可选）下载音频 + 转文字

    Returns:
        {"title", "author", "content", "duration", "video_id", ...}
    """
    # 短链接 → 真实 URL
    resolved_url = resolve_short_url(url)
    if resolved_url:
        real_url = resolved_url
    else:
        # 即使短链接解析失败，也可以尝试提取 video_id 构造完整 URL
        vid = extract_video_id(url)
        if vid:
            real_url = f"https://www.douyin.com/video/{vid}"
        else:
            real_url = url

    # 优先使用 yt-dlp 获取元数据
    yt_info = get_info_via_ytdlp(real_url)

    if yt_info:
        video_id = yt_info.get("id", "") or extract_video_id(real_url) or ""
        content = yt_info.get("description", "") or yt_info.get("title", "")

        result = {
            "title": yt_info.get("title", f"抖音视频 {video_id}"),
            "author": yt_info.get("uploader", "") or yt_info.get("creator", ""),
            "content": content,
            "duration": yt_info.get("duration", 0),
            "video_id": video_id,
            "metadata": {
                "ytdlp_extract": True,
                "view_count": yt_info.get("view_count", 0),
                "like_count": yt_info.get("like_count", 0),
                "comment_count": yt_info.get("comment_count", 0),
                "upload_date": yt_info.get("upload_date", ""),
                "resolved_url": real_url,
            },
            "plain_text": content,
            "audio_path": None,
        }
        return result

    # 降级：页面解析
    resolved_url = resolve_short_url(url)
    if resolved_url:
        url = resolved_url

    video_id = extract_video_id(url)
    page_info = parse_mobile_page(url)

    if "error" in page_info:
        return page_info

    content = page_info.get("description", "") or page_info.get("title", "")

    result = {
        "title": page_info.get("title", f"抖音视频 {video_id or ''}"),
        "author": page_info.get("author", ""),
        "content": content,
        "duration": page_info.get("duration", 0),
        "video_id": video_id or "",
        "metadata": {
            "resolved_url": resolved_url or url,
            "page_author_id": page_info.get("author_id", ""),
            "ytdlp_extract": False,
        },
        "plain_text": content,
        "audio_path": None,
    }

    return result


# CLI 使用
if __name__ == "__main__":
    import asyncio
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else input("抖音链接: ")
    result = asyncio.run(extract(url))
    print(json.dumps(result, ensure_ascii=False, indent=2))
