# Agent-CI-Lens Knowledge Base

This file contains 100% accurate solutions for specific error patterns triggered during the pipeline.
It is continuously updated by the ACMI system based on successful reflections and architectural decisions.

---

## A. STRATEGY & PLANNING ERRORS (AGENT: QUEEN)

### @POLICY_VIOLATION: No task updates proposed.
**Error:** Router state machine transitioned to BLOCKED because Queen did not propose new tasks in the required structured format (`updated_tasks` list was empty or missing).
**Fix:** This is a STRATEGY stage failure. Review **Rule: NO-DUPLICATE PLANNING (Rule 92)** and **Rule: STATE MANAGEMENT**. Ensure that if tasks exist, only their status is updated. If no tasks exist, exactly one atomic task is proposed per GOAL.

### @History Violation: Queen tried to delete tasks/goals {'XXX'}
**Error:** Router detected a mismatch between the current state of `TASKS.md` and the proposed new state from Queen's response.
**Fix:** Queen failed to use the **Bimetric Shield** logic. Ensure all existing TASK and GOAL IDs are preserved in the response. The system will attempt an automatic revert, but the Queen must fix her output structure in the next attempt.

### @History Violation (Duplicate Task ID in Proposal)
**Error:** Queen proposed a new TASK ID that already exists in `[AGENT_PROGRESS]`.
**Fix:** Refer to **Rule: NO-DUPLICATE PLANNING (Rule 92)**. Queen must only propose new tasks if the list is empty or all existing tasks are completed (`[x]`).

---

## B. IMPLEMENTATION & TESTING ERRORS (AGENT: DEVELOPER)

### @Rate Limit (HTTP 429)
**Error:** `Rate limit reached for model...` (typically on Groq).
**Fix:** **No action required from the agent.** The Router's Resilience layer handles this via Key Rotation or Fallback to Mistral. Simply continue with the task using the provided fallback model.

### @ImportError: No module named
**Error:** Python cannot find the `src` or `tests` module.
**Fix:** You forgot to create an empty `__init__.py` file. Every new directory in `src/` and `tests/` must have one to be recognized as a package (Refer to **Rule 29**).

### @F821
**Error:** Ruff error F821 (undefined name).
**Fix:** You are using a variable or function without importing it. Check your imports at the top of the file. **Rule 95:** Ensure no inline imports inside functions.

### @ModuleNotFoundError: src
**Error:** Pytest cannot find the source code during collection.
**Fix:** In your test file, use absolute imports: `from src.module import function`. Ensure `tests/__init__.py` exists.

### @SIDE_EFFECT_ISOLATION_FAILURE
**Error:** A unit test failed because it performed direct I/O (File system access, console write) instead of using mocks.
**Fix:** Refer to **Rule: SIDE-EFFECT ISOLATION (Rule 42)**. Refactor code to separate pure logic from I/O wrappers to allow for isolated mocking.

### @ASYNC_BOUNDARY_VIOLATION
**Error:** Mixing synchronous and asynchronous code paths.
**Fix:** Refer to **Rule: ASYNC BOUNDARY (Rule 56)**. The function signature must be consistently `async def` or `def` throughout the entire call stack.

### @RESOURCE_CLEANUP_FAILURE
**Error:** A resource (file handle, DB connection) was not closed.
**Fix:** Refer to **Rule: RESOURCE CLEANUP (Rule 57)**. Always manage resources using context managers (`with` or `async with`).

### @PYDANTIC_OVER_DICT_FAILURE
**Error:** Function received a raw `dict` instead of a Pydantic model.
**Fix:** Refer to **Rule: PYDANTIC OVER DICT (Rule 58)**. All data transfer boundaries must use Pydantic models for strict schema validation.

---

## C. QUALITY GATE ERRORS (AGENT: PEDANT / AUDITOR)

### @RUFF_FAIL (Static Analysis)
**Error:** Ruff reported violations (e.g., E501, F401, PERF102).
**Fix:** Refer to **Rule: RUFF ZERO TOLERANCE (Rule 63)**. If the stage is LINTING, the Dumb Pedant skill should have auto-fixed it. If it escalated, the error is complex. Review the log for the specific Ruff code.

### @MYPY_FAIL (Type Checking)
**Error:** Mypy reported type incompatibility.
**Fix:** This is a logic error in typing. Refer to **Rule: MYPY STRICT BOUNDARY (Rule 64)**. The Developer must fix this in the next EXECUTING attempt.

### @W292
**Error:** Ruff W292 (no newline at end of file).
**Fix:** Ensure the very last line of every `.py` or `.md` file is a single empty newline character.

### @NOQA Justification Missing
**Error:** A `# noqa:` suppression was found without a comment.
**Fix:** Refer to **Rule: NOQA JUSTIFICATION (Rule 65)**. Every suppression must have a comment explaining why the standard is being intentionally bypassed.

### @COMPLEXITY_CEILING
**Error:** A function has a cyclomatic complexity > 10 (C901).
**Fix:** Refer to **Rule: COMPLEXITY CEILING (Rule 67)**. Refactor using the **Early Return Pattern (Rule 54)** or extract helper functions.

---

## D. VERIFICATION & SECURITY (AGENT: AUDITOR)

### @TEST_FAIL (Assertion Failure)
**Error:** A test in `pytest` failed an `assert` statement.
**Fix:** Review the test's `ACTION_LOG`. If the assertion message is empty, refer to **Rule: ASSERTION QUALITY (Rule 68)**. The bug is in the implementation (`src/`), not the test structure.

### @SECURITY_HALT
**Error:** `security-guard` skill detected a hardcoded secret.
**Fix:** **Immediate HALT.** Refer to **Rule: SECURITY SCAN SEQUENCE (Rule 70)**. The secret must be removed, rotated, and the process debugged.

### @REGRESSION_GUARD_FAIL
**Error:** Auditor detected that new changes broke previously passing tests.
**Fix:** Refer to **Rule: REGRESSION GUARD (Rule 69)**. The Developer must fix both the new feature and the regression simultaneously.

---

## E. VCS & DEPLOYMENT (AGENT: GIT-MGR / AUDITOR)

### @VCS_FAIL
**Error:** Stage `VCS_DELIVERY` failed (Git push or PR creation failure).
**Fix:** This is often a temporary sync issue. **If local tests pass, do not create new tasks.** Let the system retry the delivery. The Router will automatically revert the state to allow a retry.

### @COMMIT_VIOLATION
**Error:** Git commit message is non-standard or not atomic.
**Fix:** Refer to **Rule: ATOMIC COMMITS (Rule 75)**. All automated commits must follow Conventional Commits: `feat(scope): description`.

### @GHA_TIMEOUT
**Error:** Cloud workflow polling exceeded 15 minutes.
**Fix:** Refer to **Rule: GHA STATUS GATE (Rule 81)**. This indicates a deadlock in the cloud. Revert the last change and try running with local GHA simulation if available.

### @BRANCH_NAMING_FAIL
**Error:** Branch name does not match required pattern.
**Fix:** Refer to **Rule: BRANCH NAMING (Rule 74)**. Pattern: `type/GOAL-XXX-description`.

### @PR_DESCRIPTION_INCOMPLETE
**Error:** PR lacks required sections (What changed, Why, Verification).
**Fix:** Refer to **Rule: PR DESCRIPTION CONTRACT (Rule 76)**. Update the Git-Mgr metadata before PR creation.