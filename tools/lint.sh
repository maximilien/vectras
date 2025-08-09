#!/bin/bash
set -euo pipefail

echo "🧹 Running Ruff lint..."
uvx ruff check src tests && echo "✅ Lint passed" || { echo "❌ Lint failed"; exit 1; }

echo "🧰 Running Ruff format check..."
uvx ruff format --check src tests && echo "✅ Format OK" || { echo "❌ Format issues"; exit 1; }

echo "✅ All lint checks passed"


