# Quality Gate Skill
## Purpose
Static code analysis before running tests.
Executed exclusively by the **Pedant** agent.

## Lifecycle
This skill runs in the `LINTING` state — after `EXECUTING` and before `TESTING`.

## Procedure (Step-by-step)

### Step 1: Run check
```
<<<SKILL:quality-gate|action:check|target:src/>>>
```

### Step 2: Evaluate the result

**If Ruff fails:**
```
<<<SKILL:quality-gate|action:autofix|target:src/>>>
```
Repeat max **3x**. If it still fails → HALT.

**If Mypy fails:**
- DO NOT FIX it yourself
- Return the error to the Developer:
```
<<<SESSION:update_context|Mypy error: <copy exact error>. Developer must fix the logic.>>>
```
Immediately terminate the LINTING step.

## Rules (ABSOLUTE)
1. You fix **only** Ruff errors (formatting, imports).
2. Mypy errors = logic error = Developer problem.
3. Never use `# noqa` on your own.
4. All rules originate from `pyproject.toml` — do not invent your own.
5. Modify **only** files in the `changed_files` list.

## Output
After a successful pass of both (Ruff + Mypy):
```
<<<SESSION:update_context|Quality Gate: PASS. Ruff OK, Mypy OK.>>>
```