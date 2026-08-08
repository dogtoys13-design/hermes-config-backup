#!/usr/bin/env python
"""图片文字识别（OCR）：SiliconFlow 三档模型（2026-08-08）
主力: PaddlePaddle/PaddleOCR-VL-1.5（免费）
备用: deepseek-ai/DeepSeek-OCR（限时免费，输出干净无噪声）
兜底: Qwen/Qwen3-VL-8B-Instruct（收费约¥0.3/M，输出干净）
价格实测: PaddleOCR免费、DeepSeek-OCR限时免费、Qwen3-VL-8B约¥0.3/M"""
import sys, os, re, json, base64, requests

# API key 从 transcribe_siliconflow.py 复用
_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcribe_siliconflow.py")

def _get_key():
    with open(_KEY_FILE, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'API_KEY\s*=\s*["\'](sk-[^"\']+)["\']', src)
    if not m:
        raise RuntimeError("SiliconFlow API key not found")
    return m.group(1)

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODELS = [
    "PaddlePaddle/PaddleOCR-VL-1.5",   # 主力：免费
    "deepseek-ai/DeepSeek-OCR",        # 备用：限时免费，输出干净
    "Qwen/Qwen3-VL-8B-Instruct",       # 兜底：收费，输出干净
]

def _call(model, image_path):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": "提取图片里全部文字，只输出识别正文，不要多余话术。"}
            ]
        }]
    }
    headers = {"Authorization": f"Bearer {_get_key()}", "Content-Type": "application/json"}
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"], None
    return None, resp

def ocr_image(image_path):
    """按序尝试三个模型：PaddleOCR(免费) → DeepSeek-OCR(免费) → Qwen3-VL(收费)"""
    for model in MODELS:
        text, resp = _call(model, image_path)
        if text:
            return text
    return f"⚠️ 全部模型识别失败: {resp.status_code} {resp.text[:200]}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python ocr_image.py <图片路径> [图片路径2...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        print(f"===== {os.path.basename(p)} =====")
        print(ocr_image(p))
        print()
