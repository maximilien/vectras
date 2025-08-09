#!/bin/bash
set -euo pipefail

if [ -f .pid ]; then
  while read -r pid; do
    [ -n "${pid}" ] && kill ${pid} 2>/dev/null || true
  done < .pid
  sleep 1
  while read -r pid; do
    if kill -0 ${pid} 2>/dev/null; then
      kill -9 ${pid} 2>/dev/null || true
    fi
  done < .pid
  rm -f .pid
fi

for port in ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123}; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    lsof -ti :$port | xargs kill -9 2>/dev/null || true
  fi
done

echo "🛑 Stopped Vectras services"


