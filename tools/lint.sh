#!/bin/bash
set -euo pipefail

echo "🧹 Running Ruff lint..."
uvx ruff check src tests && echo "✅ Python lint passed" || { echo "❌ Python lint failed"; exit 1; }

echo "🧰 Running Ruff format check..."
uvx ruff format --check src tests && echo "✅ Python format OK" || { echo "❌ Python format issues"; exit 1; }

echo "📝 Running ESLint on frontend..."
if [ -d "frontend" ] && [ -f "package.json" ]; then
  if command -v npm >/dev/null 2>&1; then
    # Install deps if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
      echo "📦 Installing JS dependencies..."
      npm install --silent
    fi
    npm run lint:js && echo "✅ JavaScript lint passed" || { echo "❌ JavaScript lint failed"; exit 1; }
  else
    echo "⚠️  npm not found, skipping JS lint"
  fi
else
  echo "⚠️  No frontend or package.json found, skipping JS lint"
fi

echo "✅ All lint checks passed"


