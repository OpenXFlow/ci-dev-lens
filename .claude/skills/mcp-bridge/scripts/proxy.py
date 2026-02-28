#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
mcp-bridge/scripts/proxy.py
Mock proxy pre MCP nástroje — Fáza 1.

Použitie:
    uv run python .claude/skills/mcp-bridge/scripts/proxy.py --tool github --action create_issue --params '{"title": "Bug"}'
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()

SUPPORTED_TOOLS = {
    "github": ["create_issue", "comment_issue", "create_pr", "merge_pr"],
    "slack": ["notify", "post_message"],
    "jira": ["create_ticket", "update_ticket", "comment"],
}


def validate_call(tool: str, action: str) -> tuple[bool, str]:
    if tool not in SUPPORTED_TOOLS:
        return False, f"Neznámy nástroj: {tool}. Dostupné: {list(SUPPORTED_TOOLS.keys())}"
    if action not in SUPPORTED_TOOLS[tool]:
        return False, f"Neznáma akcia '{action}' pre {tool}. Dostupné: {SUPPORTED_TOOLS[tool]}"
    return True, ""


def mock_response(tool: str, action: str, params: dict) -> dict:
    timestamp = datetime.now().isoformat()
    return {
        "mock": True,
        "tool": tool,
        "action": action,
        "params": params,
        "result": f"MOCK_{tool.upper()}_{action.upper()}_OK",
        "timestamp": timestamp,
        "note": "Fáza 1 — reálne volanie príde v Fáze 2 cez MCP server",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP-Bridge: mock proxy")
    parser.add_argument("--tool", required=True, help="Nástroj (github, slack, jira)")
    parser.add_argument("--action", required=True, help="Akcia")
    parser.add_argument("--params", default="{}", help="JSON parametre")
    args = parser.parse_args()

    print(f"🌉 MCP-Bridge: {args.tool}.{args.action}")

    ok, reason = validate_call(args.tool, args.action)
    if not ok:
        print(f"❌ Validácia zlyhala: {reason}")
        print("RESULT:MCP_ERROR")
        sys.exit(1)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"❌ Neplatný JSON v params: {e}")
        sys.exit(1)

    result = mock_response(args.tool, args.action, params)
    print(f"✅ Mock výsledok: {result['result']}")
    print(f"RESULT:MCP_MOCK:tool={args.tool}:action={args.action}")
    sys.exit(0)


if __name__ == "__main__":
    main()
