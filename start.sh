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
  echo "🔄 Checking for existing services..."
  
  # Stop processes from PID file
  if [ -f .pid ]; then
    echo "📋 Found PID file, stopping existing processes..."
    while read -r pid; do
      if [ -n "${pid}" ] && kill -0 ${pid} 2>/dev/null; then
        echo "  🛑 Stopping process ${pid}"
        kill ${pid} 2>/dev/null || true
      fi
    done < .pid
    sleep 2
    # Force kill any remaining processes
    while read -r pid; do
      if [ -n "${pid}" ] && kill -0 ${pid} 2>/dev/null; then
        echo "  💀 Force killing process ${pid}"
        kill -9 ${pid} 2>/dev/null || true
      fi
    done < .pid
    rm -f .pid
  fi
  
  # Check and clear ports
  for port in ${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123}; do
    check_port $port
  done
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

start_service api env -u VIRTUAL_ENV uv run uvicorn src.vectras.apis.api:app --host ${VECTRAS_API_HOST:-localhost} --port ${VECTRAS_API_PORT:-8121}
start_service mcp env -u VIRTUAL_ENV uv run uvicorn src.vectras.mcp.server:app --host ${VECTRAS_MCP_HOST:-localhost} --port ${VECTRAS_MCP_PORT:-8122}
start_service agent env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.agent:app --host ${VECTRAS_AGENT_HOST:-localhost} --port ${VECTRAS_AGENT_PORT:-8123}
start_service ui env -u VIRTUAL_ENV uv run uvicorn src.vectras.frontend.app:app --host ${VECTRAS_UI_HOST:-localhost} --port ${VECTRAS_UI_PORT:-8120}

echo "✅ All services started. Logs in ./logs."
echo "🧪 UI:     http://localhost:${VECTRAS_UI_PORT:-8120}/"
echo "🧪 API:    http://localhost:${VECTRAS_API_PORT:-8121}/health"
echo "🧪 MCP:    http://localhost:${VECTRAS_MCP_PORT:-8122}/health"
echo "🧪 Agent:  http://localhost:${VECTRAS_AGENT_PORT:-8123}/health"


