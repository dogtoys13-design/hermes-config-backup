#!/usr/bin/env python
"""调用智谱 GLM-4.6V-Flash 识别图片文字"""
import sys, json, base64, requests

API_KEY = "4a9380755377494c8a9da4c4f07c6ed4.ox8tb8xjBJRkcAX6"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def ocr_image(image_path):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    payload = {
        "model": "glm-4.6v-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": "提取图片里全部文字，只输出识别正文，不要多余话术。"}
                ]
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    
    if resp.status_code == 200:
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return text
    else:
        return f"⚠️ 识别失败: {resp.status_code} {resp.text[:200]}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python ocr_image.py <图片路径>")
        sys.exit(1)
    result = ocr_image(sys.argv[1])
    print(result)
