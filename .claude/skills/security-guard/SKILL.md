# Security-Guard Skill
## Purpose
Scans code before commit — looks for secrets, vulnerabilities, and dangerous patterns.
Executed by the **Auditor** in the `VERIFYING` state.

## Procedure

### Step 1: Run scan
```
<<<SKILL:security-guard|action:scan|target:src/>>>
```

### Step 2: Evaluate the result

**If a SECRET is found:**
```
<<<SESSION:update_context|SECURITY: Secret found in <file>. HALT required.>>>
```
→ Immediate HALT. No exceptions.

**If a WARN (dangerous pattern) is found:**
- Log to ACTION_LOG
- Continue — not a blocker
- Developer must fix before merge

**If PASS:**
```
<<<SESSION:update_context|Security-Guard: PASS. No secrets or critical vulnerabilities found.>>>
```

## Rules (ABSOLUTE)
1. Found secret = HALT. Always. No exceptions.
2. Never remove a secret yourself — only report it.
3. Scan `tests/` as well, not just `src/`.