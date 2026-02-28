# Memory Map — What is an Important Fact vs Noise

## Principle
Every record in the ACTION_LOG is either a **fact** (keep) or **noise** (discard).


## KEEP — Important Facts

| Pattern | Example | Why |
|------|---------|-------|
| `HALT` | `HALT activated: Max attempts` | Critical event |
| `TASK-XXX completed` | `Pipeline TASK-001 completed` | Permanent state |
| `TASK-XXX BLOCKED` | `TASK-002 BLOCKED after 3 attempts` | Permanent state |
| `Mypy error` | `Mypy error: incompatible type` | Technical debt |
| `API error` | `API error (groq): timeout` | Infrastructure |
| `attempts: [23]` | `[attempts: 3]` | Approaching HALT |
| `RESULT:` | `RESULT:PASS`, `RESULT:MYPY_FAIL` | Skill result |
| `Pipeline` | `Pipeline TASK-001 completed` | Workflow state |


## DISCARD — Noise

| Pattern | Example | Why |
|------|---------|-------|
| `Agent X finished. Skills: 0` | `Agent queen finished. Skills: 0` | Insignificant |
| `Token budget: X/Y` | `Token budget: 1234/8000` | Snapshot info |
| `Mock response` | `Mock response for agent: developer` | Debug noise |
| `STATE → X` | `STATE → PLANNING` | Captured in the [STATE] section |
| Duplicate lines | Same message twice | Redundancy |


## Special Rules

### Always keep the last line
Regardless of the type — the last action is always relevant for the context.

### Timestamps are secondary
If two records are identical except for timestamps, keep only the newer one.

### WORKSPACE section is not compressed
The file list is small and important — never shorten it.

### CONTEXT section is not compressed
Manually recorded context from an agent always has priority.