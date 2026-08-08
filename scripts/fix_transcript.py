#!/usr/bin/env python
"""抖音/语音转写纠错工具：按专有名词纠错表批量替换，输出精稿"""
import os, sys, re, json

ERROR_TABLE = r"C:\Vault\_system（系统）\转写纠错表.md"

# 从纠错表解析 正确→错误 映射
def load_corrections(table_path=ERROR_TABLE):
    corrections = {}
    if not os.path.exists(table_path):
        return corrections
    with open(table_path, encoding="utf-8") as f:
        lines = f.readlines()
    in_table = False
    for line in lines:
        line = line.strip()
        if line.startswith("| 正确") or line.startswith("|:---"):
            continue
        if line.startswith("|") and line.count("|") >= 3:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1] and parts[2] and "常见转写错误" not in parts[1]:
                correct = parts[1]
                wrongs = parts[2].replace("（正确）", "").split("/")
                for w in wrongs:
                    w = w.strip()
                    if w and w != correct and len(w) >= 2:
                        corrections[w] = correct
    return corrections

def correct_text(text, corrections):
    """按错误→正确映射替换，优先长词；避免正确词被错误词二次替换"""
    for wrong in sorted(corrections.keys(), key=len, reverse=True):
        correct = corrections[wrong]
        # 如果 wrong 是 correct 的子串（如 巴菲→巴菲特），用正则防止替换 correct 内部
        if wrong in correct:
            # 用正则：只替换不在 correct 上下文中的 wrong
            text = re.sub(
                r'(?<![一-龥A-Za-z])' + re.escape(wrong) + r'(?![一-龥A-Za-z])',
                correct, text
            )
        else:
            text = text.replace(wrong, correct)
    return text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_transcript.py <转写文件> [输出文件]")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    
    with open(src, encoding="utf-8") as f:
        text = f.read()
    
    corrections = load_corrections()
    before = text
    after = correct_text(text, corrections)
    
    # 统计替换次数
    count = 0
    for wrong, correct in corrections.items():
        n = before.count(wrong) - after.count(wrong)
        if n > 0:
            count += n
            print(f"  {wrong} → {correct} ×{n}")
    
    with open(dst, "w", encoding="utf-8") as f:
        f.write(after)
    print(f"✅ 完成：替换 {count} 处，输出 {dst}")
