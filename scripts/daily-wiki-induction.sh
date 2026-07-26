#!/bin/bash
# ============================================================
# 每日 Raw → Wiki 自动归纳脚本
# 功能：扫描 00_Raw 中新增的素材，生成/更新 Wiki 条目
# 运行方式：Hermes Cron 每日调度
# ============================================================

VAULT="/c/Vault"
RAW_DIR="$VAULT/00_Raw"
WIKI_DIR="$VAULT/01_Wiki"
LOG="$VAULT/log.md"
TODAY=$(date '+%Y-%m-%d')

echo "=== 每日 Raw→Wiki 归纳 | $TODAY ==="
echo ""

# 扫描 Raw 中最近7天的新文件
RAW_FILES=$(find "$RAW_DIR" -name "*.md" -newermt "$(date -d '7 days ago' '+%Y-%m-%d')" 2>/dev/null | sort)

if [ -z "$RAW_FILES" ]; then
  echo "📭 最近7天无新 Raw 素材，跳过本次处理"
  exit 0
fi

echo "📄 发现 $(echo "$RAW_FILES" | wc -l) 个待处理素材"
echo "$RAW_FILES"
echo ""

# 输出给 Hermes Agent 处理
echo "TASK: 请处理以下 Raw 素材，按 SCHEMA.md 规范整理到 Wiki："
for f in $RAW_FILES; do
  echo "  - $f"
done
