#!/usr/bin/env python
"""LLM语境纠错：把转写原文交给DeepSeek，根据整个对话语境纠错
用法: python llm_fix.py <转写文件> [输出文件]

✅ 已恢复（2026-08-17 阿念批准）：SiliconFlow LLM 仅限 DeepSeek 系列模型
（deepseek-ai/*），其他模型（GLM-5.2等）禁止调用。
"""
import sys, os, json, time
import requests

# SiliconFlow DeepSeek-V4-Flash（仅限DeepSeek系列，阿念2026-08-17批准）
SILICONFLOW_KEY = "CHANGE_ME_LLM_KEY"
DEEPSEEK_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-V4-Flash"

SYSTEM_PROMPT = """你是一名专业的语音转写纠错专家。用户会给你一段语音转写文本，它可能有以下问题：
1. 同音字错误（如"段永平"写成"邓永平"、"期权"写成"旗权"、"卖put"写成"卖步子"）
2. 断句混乱、语气词残留（如"嗯""啊""对吧"）
3. 人名、术语错误（巴菲特、段永平、芒格、英伟达、海力士、长鑫、想想、小博、全哥、全嫂等）
4. 数字识别错误（如"1.5万亿"写成"11.5万亿"）

你的任务：
1. 结合整个对话的语境，把错别字纠正为正确的
2. 保持原文的意思、语气、风格不变
3. 不要重新组织语言、不要概括、不要删减内容
4. 人名术语必须纠正（用正确写法）
5. 输出纠正后的完整文本，不要加任何解释或前后缀

注意：这是"纠错"不是"改写"，保持原汁原味，只修正错误。"""

def llm_fix(text, api_key=None, timeout=180):
    """调用DeepSeek纠错，返回纠正后的文本"""
    key = api_key or SILICONFLOW_KEY
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,  # 低温度=少创造性，只纠错
        "max_tokens": 4000,
    }
    resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=timeout)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    raise Exception(f"DeepSeek纠错失败 {resp.status_code}: {resp.text[:200]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python llm_fix.py <转写文件> [输出文件]")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src.replace(".txt", "_llm纠错.txt")
    
    with open(src, encoding="utf-8") as f:
        text = f.read()
    
    print(f"📤 原文 {len(text)}字，发送DeepSeek语境纠错...")
    t0 = time.time()
    fixed = llm_fix(text)
    print(f"✅ 纠错完成 ({time.time()-t0:.0f}秒)，输出 {len(fixed)}字")
    
    with open(dst, "w", encoding="utf-8") as f:
        f.write(fixed)
    print(f"📁 已存: {dst}")
