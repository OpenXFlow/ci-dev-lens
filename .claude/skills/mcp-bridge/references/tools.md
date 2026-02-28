# MCP-Bridge — Available Tools

## GitHub
| Action | Parameters | Description |
|-------|-----------|-------|
| `create_issue` | `title`, `body`, `labels` | Creates a GitHub issue |
| `comment_issue` | `issue_id`, `body` | Adds a comment |
| `create_pr` | `title`, `branch`, `base` | Creates a PR |
| `merge_pr` | `pr_id` | Merges a PR |

## Slack
| Action | Parameters | Description |
|-------|-----------|-------|
| `notify` | `message` | Sends a notification |
| `post_message` | `channel`, `message` | Posts a message to a channel |

## Jira
| Action | Parameters | Description |
|-------|-----------|-------|
| `create_ticket` | `title`, `description`, `type` | Creates a ticket |
| `update_ticket` | `ticket_id`, `status` | Updates the status |
| `comment` | `ticket_id`, `body` | Adds a comment |

## Phase 2 — Real MCP Servers
Currently, all calls are mocks. Phase 2 will replace `proxy.py` with real MCP servers.
Configuration will be located in `.agents/mcp-config.json`.