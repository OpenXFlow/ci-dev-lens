# MCP-Bridge Skill
## Purpose
Proxy layer for calling external tools (GitHub, Jira, Slack).
**Phase 1: Mock mode** — validates syntax, does not call real APIs.

## Usage
```
<<<SKILL:mcp-bridge|tool:github|action:create_issue|title:Bug in auth.py>>>
<<<SKILL:mcp-bridge|tool:slack|action:notify|message:Pipeline completed>>>
```

## Available Tools (Phase 1 — mock)
- `github` — issues, PRs, comments
- `slack` — notifications
- `jira` — tickets (if configured)

## Output (mock)
```
RESULT:MCP_MOCK:tool=github:action=create_issue
```
Real calls will be implemented in Phase 2 via MCP servers.