#!/bin/bash
set -euo pipefail

set -a
[ -f .env ] && . .env
set +a

usage() {
  cat <<USAGE
Usage: $0 [all|unit|integration|e2e|e2e-real|e2e-simple|help] [options]
  all           Run unit and integration tests (default)
  unit          Run unit tests only
  integration   Run integration tests only
  e2e           Run comprehensive end-to-end tests (requires OpenAI API key)
  e2e-real      Run real e2e test that creates actual PR (requires OpenAI API key)
  e2e-simple    Run simple e2e test that focuses on core capabilities (requires OpenAI API key)
  help          Show this help

Options for e2e:
  -v, --verbose Show detailed step-by-step output
USAGE
}

target="${1:-all}"
verbose=false

# Parse options for e2e
if [ "$target" = "e2e" ]; then
  shift
  while [[ $# -gt 0 ]]; do
    case $1 in
      -v|--verbose)
        verbose=true
        shift
        ;;
      *)
        echo "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
  done
fi

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
  e2e)
    echo "🚀 Running comprehensive end-to-end tests..."
    echo "⚠️  This requires OpenAI API key to be set"
    
    # Check if OpenAI API key is set
    if [ -z "${OPENAI_API_KEY:-}" ]; then
      echo "❌ OPENAI_API_KEY is not set. Please set it before running e2e tests:"
      echo "   export OPENAI_API_KEY=your_api_key_here"
      exit 1
    fi
    
    # Run the e2e test with appropriate verbosity
    if [ "$verbose" = true ]; then
      echo "📝 Running with verbose output..."
      env -u VIRTUAL_ENV uv run pytest -v -s tests/integration/test_comprehensive_e2e.py
    else
      env -u VIRTUAL_ENV uv run pytest -q tests/integration/test_comprehensive_e2e.py
    fi
    ;;
  e2e-real)
    echo "🚀 Running real end-to-end test that creates actual PR..."
    echo "⚠️  This requires OpenAI API key to be set"
    
    # Check if OpenAI API key is set
    if [ -z "${OPENAI_API_KEY:-}" ]; then
      echo "❌ OPENAI_API_KEY is not set. Please set it before running e2e tests:"
      echo "   export OPENAI_API_KEY=your_api_key_here"
      exit 1
    fi
    
    # Run the real e2e test that creates actual artifacts
    env -u VIRTUAL_ENV uv run pytest -v -s tests/integration/test_real_e2e_workflow.py
    ;;
  e2e-simple)
    echo "🚀 Running simple end-to-end test that focuses on core capabilities..."
    echo "⚠️  This requires OpenAI API key to be set"
    
    # Check if OpenAI API key is set
    if [ -z "${OPENAI_API_KEY:-}" ]; then
      echo "❌ OPENAI_API_KEY is not set. Please set it before running e2e tests:"
      echo "   export OPENAI_API_KEY=your_api_key_here"
      exit 1
    fi
    
    # Run the simple e2e test
    env -u VIRTUAL_ENV uv run pytest -v -s tests/integration/test_simple_e2e.py
    ;;
  all|*)
    echo "🧪 Running unit tests..."
    env -u VIRTUAL_ENV uv run pytest -q tests/unit
    echo "🧪 Running integration tests..."
    env -u VIRTUAL_ENV uv run pytest -q tests/integration -k test_components_end_to_end
    ;;
esac

echo "✅ All tests passed"


