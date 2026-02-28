# Testing-Pro Skill
## Purpose
Running tests and checking coverage for a Python project.
Executed exclusively by the **Developer** agent in the `TESTING` state.

## Lifecycle
This skill runs after `LINTING` (Quality Gate PASS) and before `VERIFYING`.

## Procedure (Step-by-step)

### Step 1: Run tests
```
<<<SKILL:testing-pro|action:verify|target:tests/ >>>
```

### Step 2: Evaluate the result

**If tests pass:**
```
<<<SKILL:testing-pro|action:coverage|target:src/ >>>
```

**If tests fail:**
- Analyze the error in `## [ACTION_LOG]`
- Fix the logic in the code
- Repeat max **3x** (tracked via `[attempts: N]` in TASKS.md)
- If it still fails → HALT

**If coverage < 80%:**
- Write missing tests
- Run verify again

### Step 3: Success
```
<<<SESSION:update_context|Testing-Pro: PASS. X/Y tests OK. Coverage: Z%>>>
```

## Rules
1. Write tests in `tests/unit/` for unit tests.
2. Write tests in `tests/integration/` for integration tests.
3. Do not write E2E tests — too expensive for the free tier.
4. Every new function must have at least one unit test.
5. Coverage limit: **80%** (defined in `pyproject.toml`).

## Test Types
- **Unit tests:** Fast, isolated, without DB/API. The majority of tests.
- **Integration tests:** Only if the Queen explicitly requests them in TASKS.md.
- **E2E tests:** Not written by the Developer agent — too expensive.