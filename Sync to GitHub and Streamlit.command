#!/bin/zsh

set -euo pipefail

PROJECT_DIR="/Users/li/Documents/codex/italy-chinese-news-monitor"

cd "$PROJECT_DIR"

echo "Checking git status..."
git status --short

if [ -z "$(git status --porcelain)" ]; then
  echo ""
  echo "No local changes to sync."
  read -k1 "?Press any key to close..."
  exit 0
fi

COMMIT_MSG="Update Streamlit app $(date '+%Y-%m-%d %H:%M:%S')"

echo ""
echo "Staging changes..."
git add .

echo ""
echo "Committing..."
git commit -m "$COMMIT_MSG" || true

echo ""
echo "Pushing to GitHub..."
git push origin main

echo ""
echo "Sync complete."
echo "GitHub updated, Streamlit Cloud will auto-redeploy."
read -k1 "?Press any key to close..."
