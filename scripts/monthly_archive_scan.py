# -*- coding: utf-8 -*-
"""月度归档独立扫描：Wiki（知识卡片）全部 .md，30天无修改 + 无引用 判定"""
import io, os, re, sys, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VAULT = r"C:\Vault"
WIKI = os.path.join(VAULT, "Wiki（知识卡片）")
TODAY = datetime.date(2026, 9, 1)
THRESHOLD = 30 * 86400
now_ts = datetime.datetime.now().timestamp()

# ---- 收集所有 md 文件（全库，用于引用检查）----
all_md = []
for root, dirs, files in os.walk(VAULT):
    # 跳过 .obsidian
    dirs[:] = [d for d in dirs if d != ".obsidian"]
    for f in files:
        if f.endswith(".md"):
            all_md.append(os.path.join(root, f))

candidates = []   # Wiki 下除 _MOC 的所有 md
moc_files = []
for p in all_md:
    if p.startswith(WIKI):
        rel = os.path.relpath(p, WIKI)
        if rel.startswith("_MOC"):
            moc_files.append(p)
        else:
            candidates.append(p)

def refs_in_file(needle_names, target_path, exclude_path):
    """检查某文件中是否引用 needle_names（basename 或相对路径）"""
    try:
        with open(target_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except Exception:
        return False
    for nm in needle_names:
        # [[nm]] / [[nm|别名]] / [[nm#锚点]] / [[nm.md]]
        pat = re.compile(r"\[\[\s*" + re.escape(nm) + r"(?:\||#|\.md|#\^|\s*]])")
        if pat.search(content):
            return True
        # 路径形式 [[.../nm]]
        pat2 = re.compile(r"\[\[[^\[\]]*/" + re.escape(nm) + r"(?:\||#|\.md|#\^|\s*]])")
        if pat2.search(content):
            return True
    return False

def get_age_days(path):
    st = os.stat(path)
    return (now_ts - st.st_mtime) / 86400

results = []
for c in candidates:
    base = os.path.splitext(os.path.basename(c))[0]
    rel_vault = os.path.relpath(c, VAULT).replace("\\", "/")
    age = get_age_days(c)
    if age < 30:
        continue
    # 引用检查：全库其他所有文件（含 Raw/Daily/_system/Archive/90_Archive/MOC/index）
    linked = False
    for other in all_md:
        if os.path.abspath(other) == os.path.abspath(c):
            continue
        if refs_in_file([base, rel_vault.replace(".md", "")], other, c):
            linked = True
            break
    if linked:
        continue
    mtime_str = datetime.datetime.fromtimestamp(os.stat(c).st_mtime).strftime("%Y-%m-%d")
    results.append((rel_vault, age, mtime_str))

print(f"=== 独立扫描 | Wiki候选 {len(candidates)} / 全库md {len(all_md)} | 30天阈值 ===")
if not results:
    print("NO_CANDIDATES")
else:
    for rel, age, mt in sorted(results):
        print(f"{rel} | age={age:.1f}d | mtime={mt}")
