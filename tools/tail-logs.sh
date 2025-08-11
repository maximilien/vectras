#!/bin/bash
set -euo pipefail

cmd=${1:-all}

status() {
  echo "Ports: API ${VECTRAS_API_PORT:-8121}, MCP ${VECTRAS_MCP_PORT:-8122}, UI ${VECTRAS_UI_PORT:-8120}"
  echo "Agents: Supervisor ${VECTRAS_AGENT_PORT:-8123}, Log Monitor 8124, Coding 8125, Linting 8127, Testing 8126, GitHub 8128"
  
  # Check core services
  for port in ${VECTRAS_UI_PORT:-8120} ${VECTRAS_API_PORT:-8121} ${VECTRAS_MCP_PORT:-8122}; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "✅ Port $port listening"
    else
      echo "❌ Port $port not listening"
    fi
  done
  
  # Check agents
  for port in ${VECTRAS_AGENT_PORT:-8123} 8124 8125 8126 8127 8128; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "✅ Port $port listening"
    else
      echo "❌ Port $port not listening"
    fi
  done
}

case "$cmd" in
  all)
    tail -f logs/ui.log logs/api.log logs/mcp.log logs/supervisor.log logs/log-monitor.log logs/coding.log logs/linting.log logs/testing.log logs/github.log || true
    ;;
  ui)
    tail -f logs/ui.log || true
    ;;
  api)
    tail -f logs/api.log || true
    ;;
  mcp)
    tail -f logs/mcp.log || true
    ;;
  supervisor)
    tail -f logs/supervisor.log || true
    ;;
  log-monitor)
    tail -f logs/log-monitor.log || true
    ;;
      coding)
      tail -f logs/coding.log || true
      ;;
  linting)
    tail -f logs/linting.log || true
    ;;
  testing)
    tail -f logs/testing.log || true
    ;;
  github)
    tail -f logs/github.log || true
    ;;
  agents)
    tail -f logs/supervisor.log logs/log-monitor.log logs/coding.log logs/linting.log logs/testing.log logs/github.log || true
    ;;
  core)
    tail -f logs/ui.log logs/api.log logs/mcp.log || true
    ;;
  status)
    status
    ;;
  *)
    echo "ℹ️  Usage: $0 [all|ui|api|mcp|supervisor|log-monitor|coding|linting|testing|github|agents|core|status]"
    echo ""
    echo "Commands:"
    echo "  all         - Tail all service logs"
    echo "  ui          - Tail UI logs"
    echo "  api         - Tail API logs"
    echo "  mcp         - Tail MCP logs"
    echo "  supervisor  - Tail Supervisor agent logs"
    echo "  log-monitor - Tail Log Monitor agent logs"
    echo "  coding      - Tail Coding agent logs"
    echo "  linting     - Tail Linting agent logs"
    echo "  testing     - Tail Testing agent logs"
    echo "  github      - Tail GitHub agent logs"
    echo "  agents      - Tail all agent logs"
    echo "  core        - Tail core service logs (UI, API, MCP)"
    echo "  status      - Check port status"
    exit 1
    ;;
esac


