#!/bin/bash
# git-manager/scripts/push.sh
# Použitie: bash push.sh <branch_name>

set -e
BRANCH_NAME=$1

if [ -z "$BRANCH_NAME" ]; then
    echo "❌ ERROR: Názov vetvy je povinný."
    exit 1
fi

echo "🌿 Prepínam na vetvu: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME" || git checkout "$BRANCH_NAME"

echo "📤 Odosielam kód do origin..."
if [ "$MOCK" = "true" ]; then
    echo "[MOCK] git push origin $BRANCH_NAME"
    echo "RESULT:PUSH_OK"
else
    git push origin "$BRANCH_NAME"
    echo "RESULT:PUSH_OK"
fi