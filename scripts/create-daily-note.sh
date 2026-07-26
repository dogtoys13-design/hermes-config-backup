#!/bin/bash
# 日记生成脚本 — 从模板创建今天的日记
VAULT_DIR="/c/Vault"
TEMPLATE="$VAULT_DIR/templates/日记模板.md"
DAILY_DIR="$VAULT_DIR/daily"

DATE=$(date '+%Y-%m-%d')
YEAR=$(date '+%Y')
MONTH=$(date '+%m')
DAY=$(date '+%d')
WDAY=$(date '+%A')
HOUR_MIN=$(date '+%H:%M')

# 中文星期
case $WDAY in
  Monday)    WDAY_CN="星期一" ;;
  Tuesday)   WDAY_CN="星期二" ;;
  Wednesday) WDAY_CN="星期三" ;;
  Thursday)  WDAY_CN="星期四" ;;
  Friday)    WDAY_CN="星期五" ;;
  Saturday)  WDAY_CN="星期六" ;;
  Sunday)    WDAY_CN="星期日" ;;
esac

OUTFILE="$DAILY_DIR/$DATE.md"

if [ -f "$OUTFILE" ]; then
  echo "❌ 今天的日记已存在: $OUTFILE"
  echo "📄 已有内容:"
  head -5 "$OUTFILE"
  exit 0
fi

# 替换模板占位符
sed -e "s/{{date:YYYY年M月D日}}/$YEAR年$MONTH月$DAY日/" \
    -e "s/{{date:dddd}}/$WDAY_CN/" \
    -e "s/{{time}}/$HOUR_MIN/" \
    "$TEMPLATE" > "$OUTFILE"

echo "✅ 日记已创建: $OUTFILE"
