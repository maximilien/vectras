#!/bin/bash
set -euo pipefail

set -a
[ -f .env ] && . .env
set +a

mkdir -p logs frontend tools

check_port() {
  local port=$1
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port $port busy. Killing..."
    lsof -ti :$port | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

stop_existing() {
  if [ -f .pid ]; then
    while read -r pid; do
      [ -n "${pid}" ] && kill ${pid} 2>/dev/null || true
    done < .pid
    rm -f .pid
  fi
  check_port ${VECTRAS_API_PORT:-8121}
  check_port ${VECTRAS_MCP_PORT:-8122}
  check_port ${VECTRAS_AGENT_PORT:-8123}
}

start_service() {
  local name=$1
  shift
  echo "🚀 Starting ${name}..."
  "$@" > "logs/${name}.log" 2>&1 &
  echo $! >> .pid
  sleep 2
}

stop_existing

start_service api uv run uvicorn src.vectras.apis.api:app --host ${VECTRAS_API_HOST:-localhost} --port ${VECTRAS_API_PORT:-8121}
start_service mcp uv run uvicorn src.vectras.mcp.server:app --host ${VECTRAS_MCP_HOST:-localhost} --port ${VECTRAS_MCP_PORT:-8122}
start_service agent uv run uvicorn src.vectras.agents.agent:app --host ${VECTRAS_AGENT_HOST:-localhost} --port ${VECTRAS_AGENT_PORT:-8123}

echo "✅ All services started. Logs in ./logs."
echo "🧪 API:    http://localhost:${VECTRAS_API_PORT:-8121}/health"
echo "🧪 MCP:    http://localhost:${VECTRAS_MCP_PORT:-8122}/health"
echo "🧪 Agent:  http://localhost:${VECTRAS_AGENT_PORT:-8123}/health"


