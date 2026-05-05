#!/bin/bash
set -e
cd "$(dirname "$0")"

# Check for .env config
if [ ! -f .env ]; then
  echo "============================================"
  echo "  粵語學習 App - 首次配置"
  echo "============================================"
  echo ""
  echo "  未找到 .env 檔案。請先設定 API 密鑰："
  echo ""
  echo "  1. cp .env.example .env"
  echo "  2. 編輯 .env，填入你嘅 API 密鑰"
  echo "     nano .env"
  echo ""
  echo "  支援 Anthropic、DeepSeek 等相容 API"
  echo "============================================"
  exit 1
fi

echo "粵語學習 App 啟動中..."
echo "打開瀏覽器 → http://localhost:8899"
echo ""

python3 -m backend.server
