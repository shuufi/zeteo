#!/usr/bin/env bash
# Kill processes listening on backend (8000) and frontend (5173) dev ports.
set -euo pipefail

for port in 8000 5173; do
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -z "$pids" ]; then
    echo "port $port: nothing listening"
    continue
  fi
  echo "port $port: killing pid(s) $pids"
  kill $pids
done
