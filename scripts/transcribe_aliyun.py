#!/usr/bin/env python
"""阿里云百炼 ASR 转写（2026-08-31 验证可用）
模型: qwen-audio-3.0-asr-flash-filetrans（文件转写）
流程: 上传文件→提交转写任务→fetch→下载transcription_url→提取transcripts
Key: 阿里云百炼 API Key（存独立文件 .aliyun_key）
"""
import os, time, requests, base64

def _load_key():
    keyfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aliyun_key")
    if os.path.exists(keyfile):
        with open(keyfile, encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("ALIYUN_API_KEY", "")

API_KEY = _load_key()
MODEL = "qwen-audio-3.0-asr-flash-filetrans"
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/api/v1"
MAX_RETRY = 3

def _upload_file(audio_path):
    """上传音频文件到DashScope，返回file_id"""
    import dashscope
    dashscope.api_key = API_KEY
    from dashscope import files
    upload = files.Files.upload(file_path=audio_path, purpose="file-extract")
    if upload.status_code != 200:
        raise Exception(f"上传失败: {str(upload)[:200]}")
    uploaded = upload.output.get("uploaded_files", [])
    if not uploaded:
        raise Exception("上传返回为空")
    file_id = uploaded[0]["file_id"]
    # 获取下载URL
    info = files.Files.get(file_id)
    if info.status_code != 200:
        raise Exception(f"获取文件信息失败: {str(info)[:200]}")
    return info.output["url"]

def _submit_task(file_url):
    """提交转写任务，返回task_id"""
    import dashscope
    dashscope.api_key = API_KEY
    from dashscope.audio.qwen_asr.qwen_transcription import QwenTranscription
    result = QwenTranscription.call(model=MODEL, file_url=file_url, api_key=API_KEY)
    if result.status_code != 200:
        raise Exception(f"提交任务失败: {str(result)[:200]}")
    task_id = result.output.get("task_id")
    if not task_id:
        raise Exception(f"无task_id: {str(result)[:200]}")
    # 如果直接SUCCEEDED且有结果，返回
    return task_id

def _fetch_result(task_id):
    """获取转写结果文本"""
    import dashscope
    dashscope.api_key = API_KEY
    from dashscope.audio.qwen_asr.qwen_transcription import QwenTranscription
    # 轮询等待完成
    for _ in range(30):
        result = QwenTranscription.fetch(task_id, api_key=API_KEY)
        status = result.output.get("task_status", "")
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "CANCELED"):
            raise Exception(f"任务{status}: {str(result)[:200]}")
        time.sleep(2)
    else:
        raise Exception("转写超时")

    results = result.output.get("output", {}).get("results", [])
    if not results:
        # 检查output.output是否有直接文本
        raise Exception(f"无结果: {str(result.output)[:300]}")
    turl = results[0].get("transcription_url", "")
    if not turl:
        raise Exception("无transcription_url")
    r = requests.get(turl, timeout=30)
    if r.status_code != 200:
        raise Exception(f"结果下载失败: {r.status_code}")
    data = r.json()
    transcripts = data.get("transcripts", [])
    if not transcripts:
        raise Exception(f"无transcripts: {str(data)[:200]}")
    text = transcripts[0].get("text", "") if isinstance(transcripts[0], dict) else str(transcripts[0])
    return text

def transcribe(audio_path: str) -> str:
    """转写音频文件，返回文本"""
    if not API_KEY:
        raise Exception("阿里云API Key未配置（.aliyun_key 文件缺失）")
    last_err = None
    for attempt in range(MAX_RETRY):
        try:
            file_url = _upload_file(audio_path)
            task_id = _submit_task(file_url)
            return _fetch_result(task_id)
        except Exception as e:
            last_err = str(e)
            time.sleep(3)
    raise Exception(f"阿里云ASR失败(重试{MAX_RETRY}次): {last_err}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python transcribe_aliyun.py <音频文件>")
        sys.exit(1)
    text = transcribe(sys.argv[1])
    print(text)
