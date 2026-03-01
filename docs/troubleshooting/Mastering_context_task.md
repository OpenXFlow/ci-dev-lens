# 📘 Operator’s Guide: Mastering Context & Tasks

## I. TASKS.md — The Strategic Roadmap
This file defines **what** needs to be built. You control the `## [USER_QUEUE]` section.

### 1. Anatomy of a Perfect Goal
A goal should not just be a title; it should be a mini-specification.

**❌ Bad Goal:**
```markdown
- [ ] GOAL-001: Fix the calculator.
```
*Why? Too vague. AI doesn't know what is broken or where to look.*

**✅ Good Goal:**
```markdown
- [ ] GOAL-002: Implement standard deviation in statistics module.
   - Requirement: Add `std_dev(data: list[float]) -> float` to `src/stats.py`.
   - Requirement: Must handle empty lists by raising `ValueError`.
   - Requirement: Use the population standard deviation formula.
   - Requirement: 100% test coverage in `tests/test_stats.py`.
```

### 2. Batching vs. Atomicity
*   **Simple Task:** One Goal with a few requirements.
*   **Complex Feature:** Break it into multiple Goals to avoid context overflow.

**Example of Complex Decomposition:**
```markdown
- [ ] GOAL-003: Database Layer - Part 1: Schema & Connection.
- [ ] GOAL-004: Database Layer - Part 2: CRUD operations for Users.
```

---

## II. SESSION.md — The Tactical Control
This file defines **how** the AI should behave right now. You control `## [USER_SECTION]`.

### 1. Using `### [CONTEXT]` for Style & Rules
Use this to enforce architectural decisions without changing the system prompt.

**Example: Enforcing a Specific Library**
```markdown
### [CONTEXT]
TECHNOLOGY SHIFT: We are moving from `json` to `pydantic` for data validation.
- Every new class must inherit from `pydantic.BaseModel`.
- Do not use raw dictionaries for function arguments.
```

**Example: Strict Formatting Instructions**
```markdown
### [CONTEXT]
STRICT DOCSTYLE: The Pedant is being too aggressive. 
- Use ONLY one-line docstrings for getters and setters.
- Full Google Style is mandatory ONLY for the logic in `engine.py`.
```

### 2. Handling "Fresh Starts"
If the project is messy and you want to wipe the slate clean:
```markdown
### [CONTEXT]
CLEAN SLATE: I have manually deleted the `src/old_logic/` folder.
- Forget all previous implementations of the Auth system.
- Start building the new JWT-based Auth from scratch.
```

---

## III. The "Correction" Cycle (Human-in-the-Loop)
If the AI is stuck in a loop or makes a recurring logical error, use the `[CONTEXT]` to "scold" and redirect it.

**Example: Fixing a recurring Logic Error**
```markdown
### [CONTEXT]
CRITICAL CORRECTION: In the last 3 attempts, you kept forgetting to close the file handle.
- MANDATORY: Use `with open(...)` context managers.
- Do not submit code that uses `f.close()` manually.
- Check `FEEDBACK` for the specific traceback from the last crash.
```

**Example: Breaking a Planning Loop**
```markdown
### [CONTEXT]
PLANNING GUIDANCE: You are creating too many small tasks. 
- Merge the next 3 steps into one single TASK-005. 
- I want the logic and the unit tests implemented in one go.
```

---

## IV. Pro-Tips for Efficient Communication

### 1. Use Keywords to Trigger Weights
LLMs react strongly to specific formatting. Use these prefixes in your instructions:
*   `MANDATORY:` — Use for absolute rules.
*   `FORBIDDEN:` — Use to stop the AI from using specific patterns (e.g., `FORBIDDEN: Do not use global variables.`).
*   `PREFERENCE:` — For "nice to have" code style.
*   `HINT:` — To point the AI toward a specific file or regex pattern.

### 2. The `[WORKSPACE]` Section
While the Indexer maps the whole project, you can use the `[WORKSPACE]` section in `SESSION.md` to focus the AI's attention:
```markdown
### [WORKSPACE]
- src/auth/jwt_handler.py  <-- Primary focus
- tests/test_auth.py       <-- Secondary focus
```

### 3. Whitespace & Parsing Rules (Absolute Laws)
To prevent the Pydantic parser from failing:
1.  **Never** delete the `---` separator between sections.
2.  **Always** ensure there is exactly one empty line after a `### [HEADER]`.
3.  **Never** write inside the `## [AGENT_SECTION]`. The Router will overwrite anything you put there.

---

## V. Summary Checklist before running `make pipeline`
- [ ] Is my Goal in `TASKS.md` specific enough?
- [ ] Did I remove old/conflicting instructions from `SESSION.md`?
- [ ] Is there a clear "Definition of Done" for the AI?
- [ ] Are any technical constraints (typing, docstrings) explicitly stated if they differ from the default?

**By following these rules, you reduce "Agent Theatre" (useless iterations) and save thousands of tokens.**