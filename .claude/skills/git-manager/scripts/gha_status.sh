#!/bin/bash
# git-manager/scripts/gha_status.sh

echo "🔍 Kontrolujem stav GitHub Actions..."

if [ "$MOCK" = "true" ]; then
    # Deterministické mockovanie na základe .env
    RESULT=${GHA_MOCK_RESULT:-success}
    
    if [ "$RESULT" = "success" ]; then
        echo "✅ GHA Pipeline: PASS"
        echo "RESULT:GHA_PASS"
    else
        echo "❌ GHA Pipeline: FAIL"
        echo "Log: [MOCK_ERROR] Zlyhal linting na prostredí Ubuntu-22.04"
        echo "RESULT:GHA_FAIL"
    fi
else
    # Reálne volanie GitHub CLI
    STATUS=$(gh run list --limit 1 --json conclusion --jq '.[0].conclusion')
    if [ "$STATUS" = "success" ]; then
        echo "RESULT:GHA_PASS"
    else
        echo "RESULT:GHA_FAIL"
    fi
fi