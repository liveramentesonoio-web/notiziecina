#!/bin/zsh

set -euo pipefail

PROJECT_DIR="/Users/li/Documents/codex/italy-chinese-news-monitor"
VENV_DIR="$PROJECT_DIR/.venv"
APP_PORT="8765"

cd "$PROJECT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  /Users/li/.local/bin/uv venv
fi

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

source "$VENV_DIR/bin/activate"

python -c "import streamlit" >/dev/null 2>&1 || uv pip install -e .

if lsof -nP -iTCP:"$APP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  open "http://localhost:$APP_PORT"
  exit 0
fi

open "http://localhost:$APP_PORT"
exec streamlit run app.py --server.port "$APP_PORT" --browser.gatherUsageStats false
