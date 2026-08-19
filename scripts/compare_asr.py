#!/usr/bin/env python
"""双ASR模型对比测试：SenseVoiceSmall vs TeleSpeechASR
用法: python compare_asr.py <音频文件或抖音链接>
输出: 两个模型的转写文本 + 纠错表替换次数（错别字密度对比）
"""
import sys, os, time, subprocess, requests, uuid

API_KEY = "sk-oblkrvgfnogxovzpjhcrylgsfdoqjndunkoaqovxmwkruflz"
API_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
FFMPEG = r"C:\Users\Administrator\AppData\Local\hermes\bin\ffmpeg.exe"
MODELS = ["FunAudioLLM/SenseVoiceSmall", "TeleAI/TeleSpeechASR"]

def transcribe_with_model(audio_path, model):
    """用指定模型转写，返回文本"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        data = {"model": model, "language": "zh", "response_format": "json"}
        resp = requests.post(API_URL, headers=headers, files=files, data=data, timeout=300)
    if resp.status_code == 200:
        return resp.json().get("text", "")
    return f"[ERROR {resp.status_code}] {resp.text[:100]}"

def count_errors(text):
    """统计纠错表替换次数 = 错别字密度"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fix_transcript import load_corrections
    corrections = load_corrections()
    count = 0
    for wrong in corrections:
        count += text.count(wrong)
    return count

def to_wav(input_path):
    """转16kHz wav"""
    wav = input_path + "_cmp.wav"
    subprocess.run([FFMPEG, "-y", "-i", input_path, "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", wav], capture_output=True, check=True)
    return wav

if __name__ == "__main__":
    src = sys.argv[1]
    wav = to_wav(src)
    
    print("=" * 50)
    print("🔬 双ASR模型对比测试")
    print("=" * 50)
    
    results = {}
    for model in MODELS:
        t0 = time.time()
        text = transcribe_with_model(wav, model)
        elapsed = time.time() - t0
        errs = count_errors(text)
        results[model] = {"text": text, "errors": errs, "time": elapsed}
        short = model.split("/")[-1]
        print(f"\n📊 {short}: {elapsed:.0f}秒, {len(text)}字, 错别字密度: {errs}处")
    
    os.remove(wav)
    
    print("\n" + "=" * 50)
    # 结论
    a, b = MODELS
    if results[a]["errors"] < results[b]["errors"]:
        winner = a
    elif results[a]["errors"] > results[b]["errors"]:
        winner = b
    else:
        winner = "平局"
    print(f"🏆 结论: {winner}")
    print(f"   SenseVoiceSmall: {results[a]['errors']}处错 | {results[a]['time']:.0f}秒 | {len(results[a]['text'])}字")
    print(f"   TeleSpeechASR:   {results[b]['errors']}处错 | {results[b]['time']:.0f}秒 | {len(results[b]['text'])}字")
    
    # 保存两份转写供人工查看
    out_dir = r"C:\Vault\_待审核"
    ts = time.strftime("%Y%m%d_%H%M")
    with open(os.path.join(out_dir, f"ASR对比_{ts}_SenseVoice.txt"), "w", encoding="utf-8") as f:
        f.write(results[a]["text"])
    with open(os.path.join(out_dir, f"ASR对比_{ts}_TeleSpeech.txt"), "w", encoding="utf-8") as f:
        f.write(results[b]["text"])
    print(f"\n📁 两份转写已存: _待审核/ASR对比_{ts}_*.txt")
