#!/usr/bin/env python
"""语音转写：SiliconFlow 云端ASR（TeleSpeechASR为主，SenseVoice限流自动切换备用）"""
import sys, os, json, requests, time, subprocess

API_KEY = open(os.path.join(os.path.dirname(__file__), ".siliconflow_key"), encoding="utf-8").read().strip()
API_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
PRIMARY_MODEL = "FunAudioLLM/SenseVoiceSmall"  # 日常主力
FALLBACK_MODEL = "TeleAI/TeleSpeechASR"        # 备选：方言/嘈杂低音质时切换
FFMPEG = r"C:\Users\Administrator\AppData\Local\hermes\bin\ffmpeg.exe"

def transcribe(audio_path, language="zh"):
    """转写音频文件，自动转wav 16kHz，主模型失败自动切换备用"""
    # 转wav
    wav_tmp = audio_path + "_tmp.wav"
    subprocess.run([FFMPEG, "-y", "-i", audio_path, "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", wav_tmp], capture_output=True, check=True)
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    def _call(model):
        """内部：用指定模型调用一次，返回文本"""
        with open(wav_tmp, "rb") as f:
            files = {"file": (os.path.basename(wav_tmp), f, "audio/wav")}
            data = {"model": model, "language": language, "response_format": "json"}
            resp = requests.post(API_URL, headers=headers, files=files, data=data, timeout=180)
        # with块已关闭文件句柄，此处可安全读取
        if resp.status_code == 200:
            return resp.json().get("text", ""), None
        return None, resp
    
    # 主模型尝试
    try:
        text, resp = _call(PRIMARY_MODEL)
        if text is not None:
            os.remove(wav_tmp)
            return text
        if resp is not None and resp.status_code in (429, 500, 502, 503):
            print(f"⚠️ 主模型({PRIMARY_MODEL})限流({resp.status_code})，切换备用...")
            text, resp2 = _call(FALLBACK_MODEL)
            if text is not None:
                os.remove(wav_tmp)
                return text
            raise Exception(f"备用模型也失败 {resp2.status_code}: {resp2.text[:200]}")
        raise Exception(f"转写失败 {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"⚠️ 主模型超时，切换备用...")
        text, resp2 = _call(FALLBACK_MODEL)
        if text is not None:
            os.remove(wav_tmp)
            return text
        raise Exception(f"备用模型也失败 {resp2.status_code}: {resp2.text[:200]}")
    
    # 兜底清理
    if os.path.exists(wav_tmp):
        try: os.remove(wav_tmp)
        except: pass

if __name__ == "__main__":
    path = sys.argv[1]
    t0 = time.time()
    text = transcribe(path)
    elapsed = time.time() - t0
    print(f"✅ 转写完成 ({elapsed:.0f}秒, {len(text)}字)")
    print(text)
