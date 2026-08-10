#!/bin/bash
# ============================================================
# 每3天知识库深度扫描脚本 —— 3:00 AM 执行（避开早9点高峰）
# 功能：扫描 00_Raw/ 全部素材，输出清单供 AI 深度整理
# ============================================================

VAULT="/c/Vault"
RAW="$VAULT/Raw（原始资料）"
WIKI="$VAULT/Wiki（知识卡片）"
LOG="$VAULT/log.md"
TODAY=$(date '+%Y-%m-%d')
NOW=$(date '+%Y-%m-%d %H:%M')

echo "=========================================="
echo "📚 每日知识库深度整理 | $NOW"
echo "=========================================="

# === 1. 扫描 Raw 全部素材 ===
echo ""
echo "【1/5】扫描 Raw 原始素材..."
RAW_COUNT=$(find "$RAW" -name "*.md" | wc -l)
# 兼容Windows bash：用date +%s计算7天前（避免 date -d 不兼容）
SEVEN_DAYS_AGO=$(date -d '7 days ago' '+%Y-%m-%d' 2>/dev/null || python -c "import datetime; print((datetime.date.today()-datetime.timedelta(days=7)).isoformat())")
RAW_FILES=$(find "$RAW" -name "*.md" -newermt "$SEVEN_DAYS_AGO" 2>/dev/null | sort)
RAW_NEW=$(echo "$RAW_FILES" | grep -c . 2>/dev/null || echo "0")

echo "    📂 全部 Raw 素材: ${RAW_COUNT} 条"
echo "    🆕 最近7天新增: ${RAW_NEW} 条"
echo ""

# 列出待处理文件
echo "=== RAW文件清单（最近7天）==="
if [ "$RAW_NEW" -gt 0 ]; then
  while IFS= read -r file; do
    FSIZE=$(wc -c < "$file")
    echo "  📄 $(basename "$file")  (${FSIZE}bytes)"
    echo "     📍 $file"
  done <<< "$RAW_FILES"
else
  echo "  （无新增素材）"
fi

# === 2. 扫描 Wiki 全部条目 ===
echo ""
echo "【2/5】扫描 Wiki 结构化知识库..."
THEORY=$(find "$WIKI" -path "*/理论/*" -name "*.md" | wc -l)
PROCESS=$(find "$WIKI" -path "*/流程/*" -name "*.md" | wc -l)
TEMPLATE=$(find "$WIKI" -path "*/模板/*" -name "*.md" | wc -l)
CASE=$(find "$WIKI" -path "*/案例/*" -name "*.md" | wc -l)
TOTAL_WIKI=$((THEORY + PROCESS + TEMPLATE + CASE))

echo "    🏛️  理论: ${THEORY} | 🔧 流程: ${PROCESS} | 📋 模板: ${TEMPLATE} | 🎯 案例: ${CASE}"
echo "    📊 Wiki 总条目: ${TOTAL_WIKI}"

# === 3. 检查重复/冲突 ===
echo ""
echo "【3/5】检查潜在重复和冲突..."
find "$WIKI" -name "*.md" -not -path "*/_MOC/*" | while read -r f; do
  BASENAME=$(basename "$f" .md)
  DUPS=$(find "$WIKI" -name "*.md" -not -path "*/_MOC/*" | grep -v "^$f$" | xargs grep -l "$BASENAME" 2>/dev/null | wc -l)
  if [ "$DUPS" -gt 0 ]; then
    echo "    ⚠️  $(basename "$f") — 有 ${DUPS} 个文件内容关联"
  fi
done

# === 4. 检查 Wiki 文件的双向链接 ===
echo ""
echo "【4/5】检查双向链接覆盖率..."
# 统计所有出链数量（修复 $s 未定义bug）
TOTAL_LINKS=0
while read -r f; do
  C=$(grep -o '\[\[.*\]\]' "$f" 2>/dev/null | wc -l)
  TOTAL_LINKS=$((TOTAL_LINKS + C))
done < <(find "$WIKI" -name "*.md" -not -path "*/_MOC/*")
echo "    总计 ${TOTAL_LINKS} 个 [[wikilinks]]"

# 有出链的文件数
LINKED_FILES=$(find "$WIKI" -name "*.md" -not -path "*/_MOC/*" -exec grep -l '\[\[.*\]\]' {} \; | wc -l)
echo "    有双向链接的条目: ${LINKED_FILES}/${TOTAL_WIKI}"

# === 5. 输出汇总 ===
echo ""
echo "【5/5】汇总简报"
echo ""
echo "📋 ┌─────────────────────────────────────────────┐"
echo "    │ 📚 知识库日简报 · $TODAY               │"
echo "    ├─────────────────────────────────────────────┤"
echo "    │ 📂 Raw 素材:    ${RAW_COUNT} 条 (本周新 ${RAW_NEW})  │"
echo "    │ 📖 Wiki 条目:   ${TOTAL_WIKI} 条              │"
echo "    │ 🔗 链接受益:    ${LINKED_FILES}/${TOTAL_WIKI} 页有双向链接  │"
echo "    └─────────────────────────────────────────────┘"
