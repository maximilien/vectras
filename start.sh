#!/bin/bash
set -euo pipefail

set -a
[ -f .env ] && . .env
set +a

mkdir -p logs frontend tools

usage() {
  cat <<USAGE
Usage: $0 [start|restart|status|help] [options]
  start         Start all Vectras services (default)
  restart       Stop all services and start them again
  status        Show status of all services
  help          Show this help

Services:
  - UI (Frontend)
  - API
  - MCP Server
  - Supervisor Agent
  - Log Monitor Agent
  - Coding Agent
  - Linting Agent
  - Testing Agent
  - GitHub Agent
USAGE
}

cmd=${1:-start}

check_port() {
  local port=$1
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port $port busy. Killing..."
    lsof -ti :$port | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

get_process_name() {
  local pid=$1
  if [ -n "${pid}" ] && kill -0 ${pid} 2>/dev/null; then
    ps -p ${pid} -o comm= 2>/dev/null || echo "Unknown"
  else
    echo "Not running"
  fi
}

status() {
  echo "ℹ️  Vectras services status"
  if [ -f .pid ]; then
    echo "- PID file exists (.pid):"
    local line_num=0
    local service_names=("api" "mcp" "supervisor" "logging-monitor" "coding" "linting" "testing" "github" "ui")
    while read -r pid; do
      [ -z "${pid}" ] && continue
      local service_name=${service_names[$line_num]:-unknown}
      if kill -0 ${pid} 2>/dev/null; then
        local process_name=$(get_process_name ${pid})
        echo "  ✅ ${service_name} (PID: ${pid}, Process: ${process_name})"
      else
        echo "  ⚠️  ${service_name} (PID: ${pid}, Process: Not running)"
      fi
      ((line_num++))
    done < .pid
  else
    echo "- No PID file found"
  fi

  echo "- Ports:"
  local ports=(${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123} 8124 8125 8126 8127 8128)
      local port_names=("UI" "API" "MCP" "Supervisor" "Logging Monitor" "Coding" "Testing" "Linting" "GitHub")
  for i in "${!ports[@]}"; do
    local port=${ports[$i]}
    local name=${port_names[$i]}
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "  ✅ Port $port ($name) listening"
    else
      echo "  ❌ Port $port ($name) not listening"
    fi
  done
}

stop_existing() {
  echo "🔄 Checking for existing services..."
  
  # Stop processes from PID file
  if [ -f .pid ]; then
    echo "📋 Found PID file, stopping existing processes..."
    local line_num=0
    local service_names=("api" "mcp" "supervisor" "logging-monitor" "coding" "linting" "testing" "github" "ui")
    while read -r pid; do
      if [ -n "${pid}" ] && kill -0 ${pid} 2>/dev/null; then
        local service_name=${service_names[$line_num]:-unknown}
        local process_name=$(get_process_name ${pid})
        echo "  🛑 Stopping ${service_name} (PID: ${pid}, Process: ${process_name})"
        kill ${pid} 2>/dev/null || true
      fi
      ((line_num++))
    done < .pid
    sleep 2
    # Force kill any remaining processes
    line_num=0
    while read -r pid; do
      if [ -n "${pid}" ] && kill -0 ${pid} 2>/dev/null; then
        local service_name=${service_names[$line_num]:-unknown}
        local process_name=$(get_process_name ${pid})
        echo "  💀 Force killing ${service_name} (PID: ${pid}, Process: ${process_name})"
        kill -9 ${pid} 2>/dev/null || true
      fi
      ((line_num++))
    done < .pid
    rm -f .pid
  fi
  
  # Check and clear ports (including new agent ports)
  for port in ${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123} 8124 8125 8126 8127 8128; do
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

start_services() {
  stop_existing

  start_service api env -u VIRTUAL_ENV uv run uvicorn src.vectras.apis.api:app --host ${VECTRAS_API_HOST:-localhost} --port ${VECTRAS_API_PORT:-8121}
  start_service mcp env -u VIRTUAL_ENV uv run uvicorn src.vectras.mcp.server:app --host ${VECTRAS_MCP_HOST:-localhost} --port ${VECTRAS_MCP_PORT:-8122}
  start_service supervisor env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.supervisor:app --host ${VECTRAS_AGENT_HOST:-localhost} --port ${VECTRAS_AGENT_PORT:-8123}
  start_service logging-monitor env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.logging_monitor:app --host localhost --port 8124
  start_service coding env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.coding:app --host localhost --port 8125
  start_service linting env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.linting:app --host localhost --port 8127
  start_service testing env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.testing:app --host localhost --port 8126
  start_service github env -u VIRTUAL_ENV uv run uvicorn src.vectras.agents.github:app --host localhost --port 8128
  start_service ui env -u VIRTUAL_ENV uv run uvicorn src.vectras.frontend.app:app --host ${VECTRAS_UI_HOST:-localhost} --port ${VECTRAS_UI_PORT:-8120}

  echo "✅ All services started. Logs in ./logs."
  echo "🧪 UI:           http://localhost:${VECTRAS_UI_PORT:-8120}/"
  echo "🧪 API:          http://localhost:${VECTRAS_API_PORT:-8121}/health"
  echo "🧪 MCP:          http://localhost:${VECTRAS_MCP_PORT:-8122}/health"
  echo "🧪 Supervisor:   http://localhost:${VECTRAS_AGENT_PORT:-8123}/health"
  echo "🧪 Log Monitor:  http://localhost:8124/health"
  echo "🧪 Coding:       http://localhost:8125/health"
  echo "🧪 Linting:      http://localhost:8127/health"
  echo "🧪 Testing:      http://localhost:8126/health"
  echo "🧪 GitHub:       http://localhost:8128/health"
}

case "$cmd" in
  help|-h|--help)
    usage
    exit 0
    ;;
  status)
    status
    ;;
  restart)
    echo "🔄 Restarting all Vectras services..."
    start_services
    ;;
  start|*)
    start_services
    ;;
esac


