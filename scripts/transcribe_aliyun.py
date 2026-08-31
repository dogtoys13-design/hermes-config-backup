#!/usr/bin/env python
"""阿里云百炼 ASR 转写（替代 SiliconFlow，2026-08-30 启用）
模型: qwen-audio-3.0-asr-flash（通义千问音频ASR，文件转写）
Key: 阿里云百炼 API Key（存独立文件 .aliyun_key）
"""
import os, requests, sys

# 阿里云配置（key 从独立文件读取）
def _load_key():
    keyfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aliyun_key")
    if os.path.exists(keyfile):
        with open(keyfile, encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("ALIYUN_API_KEY", "")

API_KEY = _load_key()
BASE_URL = "https://ws-05hru5usg694bs0k.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
PRIMARY_MODEL = "qwen-audio-3.0-asr-flash"
FALLBACK_MODEL = "qwen3-asr-flash"

def transcribe(audio_path: str) -> str:
    """转写音频文件，返回文本"""
    if not API_KEY:
        raise Exception("阿里云API Key未配置（.aliyun_key 文件缺失）")

    headers = {"Authorization": f"Bearer {API_KEY}"}
    ext = os.path.splitext(audio_path)[1].lower()
    content_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }.get(ext, "audio/wav")

    models = [PRIMARY_MODEL, FALLBACK_MODEL]
    last_err = None
    for model in models:
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, content_type)}
                data = {"model": model}
                resp = requests.post(
                    f"{BASE_URL}/audio/transcriptions",
                    headers=headers, files=files, data=data, timeout=300,
                )
            if resp.status_code == 200:
                text = resp.json().get("text", "")
                if text:
                    return text
                last_err = f"模型{model}返回空文本"
            else:
                last_err = f"模型{model}失败 {resp.status_code}: {resp.text[:150]}"
        except Exception as e:
            last_err = f"模型{model}异常: {str(e)[:100]}"
    raise Exception(f"阿里云ASR全部失败: {last_err}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python transcribe_aliyun.py <音频文件>")
        sys.exit(1)
    text = transcribe(sys.argv[1])
    print(text)
