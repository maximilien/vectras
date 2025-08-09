#!/bin/bash
set -euo pipefail

set -a
[ -f .env ] && . .env
set +a

usage() {
  cat <<USAGE
Usage: $0 [all|unit|integration|help]
  all           Run unit and integration tests (default)
  unit          Run unit tests only
  integration   Run integration tests only
  help          Show this help
USAGE
}

target="${1:-all}"
case "$target" in
  help|-h|--help)
    usage
    exit 0
    ;;
  unit)
    echo "🧪 Running unit tests..."
    env -u VIRTUAL_ENV uv run pytest -q tests/unit
    ;;
  integration)
    echo "🧪 Running integration tests..."
    env -u VIRTUAL_ENV uv run pytest -q tests/integration -k test_components_end_to_end
    ;;
  all|*)
    echo "🧪 Running unit tests..."
    env -u VIRTUAL_ENV uv run pytest -q tests/unit
    echo "🧪 Running integration tests..."
    env -u VIRTUAL_ENV uv run pytest -q tests/integration -k test_components_end_to_end
    ;;
esac

echo "✅ All tests passed"


