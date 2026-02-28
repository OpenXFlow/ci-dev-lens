# Context-Compressor Skill
## Purpose
Compresses SESSION.md when the Router detects a Yellow Zone (70% of the context window).
Triggered **automatically by the Router** — agents do not call it directly.

## When it runs
- Token budget ≥ 70% → Yellow Zone → Router calls compression
- Token budget ≥ 90% → Red Zone → emergency compression + possible HALT

## What it compresses
- `ACTION_LOG` — the primary source of context growth
- Preserves: `STATE`, `CONTEXT`, `WORKSPACE` untouched

## Procedure
1. Archive the original ACTION_LOG → `.claude/cache/session-archive-<timestamp>.md`
2. Extract "important facts" (see `references/memory-map.md`)
3. Replace ACTION_LOG with the shortened version
4. Log how many tokens were saved

## Output
```
<<<SESSION:update_context|[COMPRESSED] Original log archived. Active facts: X>>>
```