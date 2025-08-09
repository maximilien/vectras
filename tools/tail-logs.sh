#!/bin/bash
set -euo pipefail

cmd=${1:-all}

status() {
  echo "Ports: API ${VECTRAS_API_PORT:-8121}, MCP ${VECTRAS_MCP_PORT:-8122}, Agent ${VECTRAS_AGENT_PORT:-8123}"
  for port in ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122} ${VECTRAS_AGENT_PORT:-8123}; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "✅ Port $port listening"
    else
      echo "❌ Port $port not listening"
    fi
  done
}

case "$cmd" in
  all)
    tail -f logs/api.log logs/mcp.log logs/agent.log || true
    ;;
  api)
    tail -f logs/api.log || true
    ;;
  mcp)
    tail -f logs/mcp.log || true
    ;;
  agent)
    tail -f logs/agent.log || true
    ;;
  status)
    status
    ;;
  *)
    echo "ℹ️  Usage: $0 [all|api|mcp|agent|status]"
    exit 1
    ;;
esac


