#!/bin/bash
# ============================================================
# 每月归档脚本 — 30天无查看 / 无引用的笔记自动归档
# 规则：
#   1. 最后更新日期 ≥ 30天前
#   2. 无其他笔记通过 [[wikilink]] 引用
#   3. 不在 index.md / MOC 中主动引用
# 绝不删除任何文件，只移动到 90_Archive/
# 本脚本仅扫描和输出候选清单，具体的移动/MOC更新/简报由 AI 代理执行
#
# 2026-09-01 修复：目录改为 Wiki（知识卡片）/_system（系统）；while-read 处理含空格文件名
# ============================================================

VAULT="/c/Vault"
WIKI_DIR="$VAULT/Wiki（知识卡片）"
MOC_DIR="$WIKI_DIR/_MOC"
ARCHIVE_DIR="$VAULT/90_Archive"
LOG="$VAULT/_system（系统）/log.md"
INDEX_FILE="$VAULT/_system（系统）/index.md"
TODAY=$(date '+%Y-%m-%d')
THRESHOLD_DAYS=30

echo "=== 每月归档检查 | $TODAY ==="

# 确保归档目录存在
mkdir -p "$ARCHIVE_DIR"

# 候选清单文件（避免含空格文件名被单词拆分）
TMPLIST=$(mktemp)
ARCHIVE_LIST_FILE=$(mktemp)

# 收集所有 Wiki 文件（排除 _MOC 索引）
find "$WIKI_DIR" -name "*.md" -not -path "*/_MOC/*" | sort > "$TMPLIST"

while IFS= read -r file; do
  [ -z "$file" ] && continue

  # 获取最后修改日期
  FILE_DATE=$(stat -c '%Y' "$file")
  NOW=$(date '+%s')
  AGE_DAYS=$(( (NOW - FILE_DATE) / 86400 ))

  # 跳过30天内的
  [ "$AGE_DAYS" -lt "$THRESHOLD_DAYS" ] && continue

  REL_PATH="${file#$VAULT/}"

  # 检查是否有 [[wikilinks]] 引用（搜索所有文件）
  BASENAME=$(basename "$file" .md)
  LINK_COUNT=$(grep -r "\[\[$BASENAME\]\]" "$VAULT" --include="*.md" -l 2>/dev/null | grep -v -F "$file" | wc -l)

  # 检查是否在 index.md 或 MOC 中被引用
  IN_INDEX=0
  grep -q "\[\[$REL_PATH\]\]" "$INDEX_FILE" 2>/dev/null && IN_INDEX=1
  grep -q "\[\[$BASENAME\]\]" "$INDEX_FILE" 2>/dev/null && IN_INDEX=1
  grep -rq "\[\[$BASENAME\]\]" "$MOC_DIR" --include="*.md" 2>/dev/null && IN_INDEX=1

  # 只在无任何引用时归档
  if [ "$LINK_COUNT" -eq 0 ] && [ "$IN_INDEX" -eq 0 ]; then
    echo "$file" >> "$ARCHIVE_LIST_FILE"
  fi
done < "$TMPLIST"

TOTAL=$(wc -l < "$ARCHIVE_LIST_FILE" | tr -d ' ')

if [ "$TOTAL" -eq 0 ]; then
  echo "📭 无满足归档条件的文件"
  rm -f "$TMPLIST" "$ARCHIVE_LIST_FILE"
  exit 0
fi

echo "📦 以下文件满足30天归档条件："
echo ""
echo "=== 按领域分类 ==="

# 按领域统计
MAIN_COUNT=0
SIDE_COUNT=0
PERSONAL_COUNT=0
OTHER_COUNT=0

while IFS= read -r f; do
  [ -z "$f" ] && continue
  REL="${f#$VAULT/}"
  DEST="$ARCHIVE_DIR/$REL"
  mkdir -p "$(dirname "$DEST")"

  # 判断领域（当前术语：电商/投资/个人）
  case "$REL" in
    Wiki（知识卡片）/电商/*) DOMAIN="电商"; MAIN_COUNT=$((MAIN_COUNT+1)) ;;
    Wiki（知识卡片）/投资/*) DOMAIN="投资"; SIDE_COUNT=$((SIDE_COUNT+1)) ;;
    Wiki（知识卡片）/个人/*) DOMAIN="个人"; PERSONAL_COUNT=$((PERSONAL_COUNT+1)) ;;
    *) DOMAIN="其他"; OTHER_COUNT=$((OTHER_COUNT+1)) ;;
  esac

  # 获取类型（理论/流程/模板/案例）
  TYPE=$(echo "$REL" | grep -oE '(理论|流程|模板|案例)' | head -1)
  [ -z "$TYPE" ] && TYPE="未分类"

  # 获取最后修改日期
  FILE_DATE=$(stat -c '%y' "$f" 2>/dev/null | cut -d' ' -f1)
  [ -z "$FILE_DATE" ] && FILE_DATE="未知"

  echo "  [$DOMAIN][$TYPE] $REL (最后更新: $FILE_DATE)"
done < "$ARCHIVE_LIST_FILE"

echo ""
echo "=== 统计 ==="
echo "  电商: ${MAIN_COUNT} 条"
echo "  投资: ${SIDE_COUNT} 条"
echo "  个人: ${PERSONAL_COUNT} 条"
[ "$OTHER_COUNT" -gt 0 ] && echo "  其他: ${OTHER_COUNT} 条"

# 更新日志
{
  echo ""
  echo "## $TODAY | archive | 自动归档 ${TOTAL} 条"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    echo "- 归档: ${f#$VAULT/}"
  done < "$ARCHIVE_LIST_FILE"
} >> "$LOG"

echo ""
echo "📊 本月共归档 ${TOTAL} 条笔记"

rm -f "$TMPLIST" "$ARCHIVE_LIST_FILE"
