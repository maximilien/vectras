#!/bin/bash
set -euo pipefail

set -a
[ -f .env ] && . .env
set +a

usage() {
  cat <<USAGE
Usage: $0 [stop|status|help] [options]
  stop          Stop all Vectras services (default)
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

cmd=${1:-stop}

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

stop_services() {
  if [ -f .pid ]; then
    local line_num=0
    local service_names=("api" "mcp" "supervisor" "logging-monitor" "coding" "linting" "testing" "github" "ui")
    while read -r pid; do
      [ -n "${pid}" ] && kill ${pid} 2>/dev/null || true
      ((line_num++))
    done < .pid
    sleep 1
    line_num=0
    while read -r pid; do
      if kill -0 ${pid} 2>/dev/null; then
        local service_name=${service_names[$line_num]:-unknown}
        local process_name=$(get_process_name ${pid})
        echo "  💀 Force killing ${service_name} (PID: ${pid}, Process: ${process_name})"
        kill -9 ${pid} 2>/dev/null || true
      fi
      ((line_num++))
    done < .pid
    rm -f .pid
  fi

  for port in ${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123} 8124 8125 8126 8127 8128; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      lsof -ti :$port | xargs kill -9 2>/dev/null || true
    fi
  done

  echo "🛑 Stopped Vectras services"
}

case "$cmd" in
  help|-h|--help)
    usage
    exit 0
    ;;
  status)
    status
    ;;
  stop|*)
    stop_services
    ;;
esac


