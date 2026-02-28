# Handoff-Manager Skill
## Purpose
"Save Game" — saves the complete state before ending a session or upon HALT.
Triggered **automatically by the Router** before transitioning to IDLE or BLOCKED.

## When it runs
- Pipeline successfully completed → before IDLE
- HALT activated → before BLOCKED
- Manually: `make status` displays the last handoff

## What it saves
- Current STATE, CONTEXT, WORKSPACE
- Active and completed tasks from TASKS.md
- Last 10 records of the ACTION_LOG
- Timestamp and reason for termination

## Output
File: `.claude/cache/handoff-<timestamp>.md`

In a new session, Claude reads this file and knows:
- Where the pipeline ended
- What was finished
- What needs to be completed