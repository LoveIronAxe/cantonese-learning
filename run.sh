#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 啟動粵語學習 App..."
echo "http://localhost:8899"
python3 -m backend.server
