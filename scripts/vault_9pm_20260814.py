# -*- coding: utf-8 -*-
"""9点汇总统计脚本 - 只读文件系统，输出各分区计数与今日新增"""
import os, sys, io, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VAULT = r"C:\Vault"
TODAY = "2026-08-14"

def walk_md(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".md"):
                out.append(os.path.join(dirpath, fn))
    return out

def fm_time(path):
    try:
        return datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
    except:
        return "?"

def read_frontmatter(path):
    """返回 (created, status) 粗略解析"""
    created, status = "", ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(1500)
        for line in head.splitlines():
            if line.startswith("created:") and not created:
                created = line.split(":", 1)[1].strip().split(" ")[0]
            if line.startswith("status:") and not status:
                status = line.split(":", 1)[1].strip()
    except:
        pass
    return created, status

# ---- Wiki ----
wiki_root = os.path.join(VAULT, "Wiki（知识卡片）")
wiki_files = walk_md(wiki_root)
moc_files = [p for p in wiki_files if "_MOC" in p.replace("\\", "/")]
today_wiki = []      # created==TODAY
today_wiki_mtime = []  # mtime==TODAY (含存量触碰)
for p in wiki_files:
    created, status = read_frontmatter(p)
    mt = fm_time(p)
    if created == TODAY:
        today_wiki.append((os.path.basename(p), created, status))
    elif mt == TODAY:
        today_wiki_mtime.append((os.path.basename(p), created, status, mt))

# ---- Raw ----
raw_root = os.path.join(VAULT, "Raw（原始资料）")
raw_files = walk_md(raw_root)
daishen = [os.path.relpath(p, VAULT) for p in raw_files if "待审-" in os.path.basename(p)]
daizhi = [os.path.relpath(p, VAULT) for p in raw_files if "待织-" in os.path.basename(p)]
today_raw = []
for p in raw_files:
    mt = fm_time(p)
    bn = os.path.basename(p)
    if mt == TODAY or TODAY in bn:
        today_raw.append((os.path.relpath(p, VAULT), mt))

# ---- Archive ----
arch_root = os.path.join(VAULT, "Archive（归档）")
arch_files = walk_md(arch_root)

# ---- 输出 ----
print("=== WIKI ===")
print("wiki_total:", len(wiki_files))
print("moc_count:", len(moc_files))
print("created_today(%s):" % TODAY, len(today_wiki))
for n, c, s in today_wiki:
    print("  NEW:", n, "| created:", c, "| status:", s)
print("mtime_today(created!=today):", len(today_wiki_mtime))
for n, c, s, mt in today_wiki_mtime:
    print("  MT:", n, "| created:", c, "| status:", s, "| mtime:", mt)
print()
print("=== RAW ===")
print("raw_total:", len(raw_files))
print("daishen_count:", len(daishen))
for p in daishen:
    print("  待审:", p)
print("daizhi_count:", len(daizhi))
for p in daizhi:
    print("  待织:", p)
print("today_raw_mtime_or_name:", len(today_raw))
for p, mt in today_raw:
    print("  RAW_TODAY:", p, "| mtime:", mt)
print()
print("=== ARCHIVE ===")
print("archive_total:", len(arch_files))
