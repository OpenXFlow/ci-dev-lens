#!/bin/bash
# quality-gate/scripts/autofix.sh
# Automatická oprava Ruff chýb
# Použitie: bash autofix.sh [target]
# Príklad:  bash autofix.sh src/

set -e

TARGET=${1:-"src/"}

echo "🔧 Ruff autofix: $TARGET"
uv run ruff check --fix "$TARGET"

echo "🔧 Ruff format: $TARGET"
uv run ruff format "$TARGET"

# Overenie po oprave
echo "🔍 Re-check po autofix..."
uv run ruff check "$TARGET" && echo "RESULT:AUTOFIX_OK" || echo "RESULT:AUTOFIX_FAIL"