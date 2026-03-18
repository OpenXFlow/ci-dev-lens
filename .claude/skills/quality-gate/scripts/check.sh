#!/bin/bash
# quality-gate/scripts/check.sh (v 1.2)
# Surgical Patch: Include tests directory in default linting target.
# Rule enforcement: English-only comments and outputs.

TARGET=${1:-"src/ tests/"}

# 1. Automatic silent attempt to fix formatting (Agent doesn't need to handle this)
uv run ruff check --fix $TARGET >/dev/null 2>&1
uv run ruff format $TARGET >/dev/null 2>&1

# 2. Strict check for remaining errors (that cannot be autofixed)
uv run ruff check $TARGET && RUFF_EXIT=0 || RUFF_EXIT=$?
uv run mypy $TARGET && MYPY_EXIT=0 || MYPY_EXIT=$?

if [ $RUFF_EXIT -ne 0 ]; then echo "RESULT:RUFF_FAIL"; exit 1; fi
if [ $MYPY_EXIT -ne 0 ]; then echo "RESULT:MYPY_FAIL"; exit 2; fi

echo "RESULT:PASS"
exit 0
