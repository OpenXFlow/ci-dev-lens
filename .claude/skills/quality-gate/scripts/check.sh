#!/bin/bash
TARGET=${1:-"src/"}

# 1. Automatický tichý pokus o opravu formátovania (Agent to nemusí riešiť)
uv run ruff check --fix "$TARGET" >/dev/null 2>&1
uv run ruff format "$TARGET" >/dev/null 2>&1

# 2. Až teraz prísna kontrola (či zostali chyby, ktoré sa nedajú autofixnúť)
uv run ruff check "$TARGET" && RUFF_EXIT=0 || RUFF_EXIT=$?
uv run mypy "$TARGET" && MYPY_EXIT=0 || MYPY_EXIT=$?

if [ $RUFF_EXIT -ne 0 ]; then echo "RESULT:RUFF_FAIL"; exit 1; fi
if [ $MYPY_EXIT -ne 0 ]; then echo "RESULT:MYPY_FAIL"; exit 2; fi

echo "RESULT:PASS"
exit 0