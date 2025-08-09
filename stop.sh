#!/bin/bash
set -euo pipefail

cmd=${1:-stop}

status() {
  echo "ℹ️  Vectras services status"
  if [ -f .pid ]; then
    echo "- PID file exists (.pid):"
    while read -r pid; do
      [ -z "${pid}" ] && continue
      if kill -0 ${pid} 2>/dev/null; then
        echo "  ✅ Process running: ${pid}"
      else
        echo "  ⚠️  Stale PID: ${pid}"
      fi
    done < .pid
  else
    echo "- No PID file found"
  fi

  echo "- Ports:"
  for port in ${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123}; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "  ✅ Port $port listening"
    else
      echo "  ❌ Port $port not listening"
    fi
  done
}

stop_services() {
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

  for port in ${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123}; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      lsof -ti :$port | xargs kill -9 2>/dev/null || true
    fi
  done

  echo "🛑 Stopped Vectras services"
}

case "$cmd" in
  status)
    status
    ;;
  stop|*)
    stop_services
    ;;
esac


