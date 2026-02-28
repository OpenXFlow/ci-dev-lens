#!/bin/bash
# git-manager/scripts/pr_create.sh
# Použitie: bash pr_create.sh <title> <body>

TITLE=$1
BODY=$2

echo "🎋 Vytváram Pull Request: $TITLE"

if [ "$MOCK" = "true" ]; then
    echo "[MOCK] gh pr create --title \"$TITLE\" --body \"$BODY\""
    echo "RESULT:PR_CREATED:https://github.com/mock/repo/pull/1"
else
    # Vyžaduje nainštalované GitHub CLI (gh)
    PR_URL=$(gh pr create --title "$TITLE" --body "$BODY")
    echo "RESULT:PR_CREATED:$PR_URL"
fi