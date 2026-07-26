#!/bin/bash
# ============================================================
# 每月归档脚本 — 30天无查看 / 无引用的笔记自动归档
# 规则：
#   1. 最后更新日期 ≥ 30天前
#   2. 无其他笔记通过 [[wikilink]] 引用
#   3. 不在 index.md / MOC 中主动引用
# 绝不删除任何文件，只移动到 90_Archive/
# 本脚本仅扫描和输出候选清单，具体的移动/MOC更新/简报由 AI 代理执行
# ============================================================

VAULT="/c/Vault"
WIKI_DIR="$VAULT/01_Wiki"
ARCHIVE_DIR="$VAULT/90_Archive"
LOG="$VAULT/log.md"
TODAY=$(date '+%Y-%m-%d')
THRESHOLD_DAYS=30

echo "=== 每月归档检查 | $TODAY ==="

# 确保归档目录存在
mkdir -p "$ARCHIVE_DIR"

# 收集所有 Wiki 文件
WIKI_FILES=$(find "$WIKI_DIR" -name "*.md" -not -path "*/_MOC/*" | sort)
ARCHIVE_LIST=""

for file in $WIKI_FILES; do
  # 获取最后修改日期
  FILE_DATE=$(stat -c '%Y' "$file")
  NOW=$(date '+%s')
  AGE_DAYS=$(( (NOW - FILE_DATE) / 86400 ))

  # 跳过30天内的
  [ "$AGE_DAYS" -lt "$THRESHOLD_DAYS" ] && continue

  REL_PATH="${file#$VAULT/}"

  # 检查是否有 [[wikilinks]] 引用（搜索所有文件）
  BASENAME=$(basename "$file" .md)
  LINK_COUNT=$(grep -r "\[\[$BASENAME\]\]" "$VAULT" --include="*.md" -l 2>/dev/null | grep -v "$file" | wc -l)

  # 检查是否在 index.md 或 MOC 中被引用
  IN_INDEX=0
  grep -q "\[\[$REL_PATH\]\]" "$VAULT/index.md" 2>/dev/null && IN_INDEX=1
  grep -q "\[\[$BASENAME\]\]" "$VAULT/index.md" 2>/dev/null && IN_INDEX=1

  # 只在无任何引用时归档
  if [ "$LINK_COUNT" -eq 0 ] && [ "$IN_INDEX" -eq 0 ]; then
    ARCHIVE_LIST="$ARCHIVE_LIST $file"
  fi
done

if [ -z "$ARCHIVE_LIST" ]; then
  echo "📭 无满足归档条件的文件"
  exit 0
fi

echo "📦 以下文件满足30天归档条件："
echo ""
echo "=== 按领域分类 ==="

# 按领域统计
MAIN_COUNT=0
SIDE_COUNT=0
PERSONAL_COUNT=0

for f in $ARCHIVE_LIST; do
  REL="${f#$VAULT/}"
  DEST="$ARCHIVE_DIR/$REL"
  mkdir -p "$(dirname "$DEST")"
  
  # 判断领域
  case "$REL" in
    01_Wiki/主业/*) DOMAIN="主业"; MAIN_COUNT=$((MAIN_COUNT+1)) ;;
    01_Wiki/副业/*) DOMAIN="副业"; SIDE_COUNT=$((SIDE_COUNT+1)) ;;
    01_Wiki/个人/*) DOMAIN="个人"; PERSONAL_COUNT=$((PERSONAL_COUNT+1)) ;;
    *) DOMAIN="其他" ;;
  esac
  
  # 获取类型（理论/流程/模板/案例）
  TYPE=$(echo "$REL" | grep -oE '(理论|流程|模板|案例)' | head -1)
  [ -z "$TYPE" ] && TYPE="未分类"
  
  # 获取最后修改日期
  FILE_DATE=$(stat -c '%y' "$f" 2>/dev/null | cut -d' ' -f1)
  [ -z "$FILE_DATE" ] && FILE_DATE="未知"
  
  echo "  [$DOMAIN][$TYPE] $REL (最后更新: $FILE_DATE)"
done

echo ""
echo "=== 统计 ==="
echo "  主业: ${MAIN_COUNT} 条"
echo "  副业: ${SIDE_COUNT} 条"
echo "  个人: ${PERSONAL_COUNT} 条"

# 更新日志
{
  echo ""
  echo "## $TODAY | archive | 自动归档 $(echo "$ARCHIVE_LIST" | wc -w) 条"
  for f in $ARCHIVE_LIST; do
    echo "- 归档: ${f#$VAULT/}"
  done
} >> "$LOG"

echo ""
echo "📊 本月共归档 $(echo "$ARCHIVE_LIST" | wc -w) 条笔记"