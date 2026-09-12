#!/usr/bin/env bash
# Start backend (8000) and frontend (5173) dev servers in background.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
mkdir -p "$LOG_DIR"

start_if_free() {
  local port="$1" name="$2" dir="$3" cmd="$4"
  if lsof -ti tcp:"$port" >/dev/null 2>&1; then
    echo "port $port ($name): already listening, skipping"
    return
  fi
  echo "starting $name on port $port (log: $LOG_DIR/$name.log)"
  (cd "$dir" && nohup $cmd >"$LOG_DIR/$name.log" 2>&1 &)
}

start_if_free 8000 backend "$ROOT_DIR/backend" "uvicorn main:app --reload --port 8000"
start_if_free 5173 frontend "$ROOT_DIR/frontend" "npm run dev -- --port 5173"
