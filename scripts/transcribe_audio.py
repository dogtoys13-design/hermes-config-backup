#!/usr/bin/env python
"""转写新音频到知识库 — 只处理未入库的新文件"""
import whisper, time, os, sys, json
from pathlib import Path

os.environ["PATH"] = r"C:\Users\Administrator\AppData\Local\hermes\bin;" + os.environ.get("PATH", "")
docs_dir = r"C:\Users\Administrator\AppData\Local\hermes\cache\documents"
raw_dir = r"C:\Vault\00_Raw"
out_dir = r"C:\Users\Administrator\AppData\Local\hermes\cron\output"
record_file = os.path.join(out_dir, "processed_record.json")
os.makedirs(out_dir, exist_ok=True)

# 1. 加载已处理记录
processed = set()
if os.path.exists(record_file):
    with open(record_file) as f:
        processed = set(json.load(f))

# 2. 找到所有 .m4a
all_m4a = [f for f in os.listdir(docs_dir) if f.endswith('.m4a')]

# 3. 筛选没处理过的
pending = [f for f in all_m4a if f not in processed]

if not pending:
    print(f"📭 没有新语音需要处理（共 {len(all_m4a)} 条，全部已处理）")
    sys.exit(0)

skipped = len(all_m4a) - len(pending)
print(f"总共 {len(all_m4a)} 条，待处理 {len(pending)} 条" + (f"（跳过 {skipped} 条已入库的）" if skipped else ""))

model = whisper.load_model("tiny", device="cpu")
print("模型加载完成\n")

for fname in pending:
    audio_path = os.path.join(docs_dir, fname)
    topic = fname.replace("doc_", "").split("_", 1)[-1].replace(".m4a", "")
    size_mb = os.path.getsize(audio_path) / 1024 / 1024
    idx = pending.index(fname) + 1
    
    print(f"[{idx}/{len(pending)}] {topic} ({size_mb:.1f}MB)...", flush=True)
    t0 = time.time()
    
    try:
        result = model.transcribe(audio_path, language="zh", beam_size=5)
        elapsed = time.time() - t0
        text = result["text"].strip()
        print(f"   ✅ {elapsed:.0f}秒，{len(text)}字", flush=True)
        
        # 保存文本
        with open(os.path.join(out_dir, f"new_{idx}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        
        # 标记已处理
        processed.add(fname)
        
    except Exception as e:
        print(f"   ❌ {e}", flush=True)

# 4. 保存处理记录
with open(record_file, "w") as f:
    json.dump(sorted(list(processed)), f, indent=2)

print(f"\n✅ 完成！本次处理 {len(pending)} 条新语音")
for f in pending:
    print(f"   ✅ {f}")
