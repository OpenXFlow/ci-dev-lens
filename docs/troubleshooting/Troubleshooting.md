# 🛠️ TROUBLESHOOTING GUIDE: Agent-CI-Lens

This document provides solutions for common exceptions, system locks, and state machine failures within the **Model 5.3/6.0** architecture.

---

## 🚨 I. The HALT Protocol (Emergency Stop)

**Symptoms:** The pipeline immediately exits with an error; `make pipeline` refuses to start.

### 1. The `HALT.flag` File
*   **Cause:** A critical security or system error occurred. The system creates `.claude/cache/HALT.flag` to prevent further credit consumption or data leakage.
*   **Identification:** Run `make status`. It will display the reason stored inside the flag.
*   **Solution:**
    1.  Read the reason in `.claude/cache/HALT.flag`.
    2.  Fix the underlying issue (e.g., remove a hardcoded API key).
    3.  **Clear the lock:** Run `make clean` or manually delete the `.claude/cache/HALT.flag` file.

### 2. `SECURITY_HALT`: Secret Detected
*   **Cause:** The `security-guard` skill found an API key, password, or private key in the source code.
*   **Solution:** 
    *   Move the secret to the `.env` file.
    *   Clean the `src/` or `tests/` file.
    *   Restart the pipeline.

---

## 🚦 II. Pipeline State Failures

### 1. `BLOCKED` State
*   **Cause:** A specific task has failed 3 consecutive times (`[attempts: 3]`). The orchestrator stops to prevent infinite loops.
*   **Solution:**
    1.  Check `agent_context/SESSION.md` -> `### [FEEDBACK]` for the `LAST_ERROR`.
    2.  If the AI is "stuck," manually fix the code or the test.
    3.  Reset the attempt counter in `TASKS.md` back to `[attempts: 0]` or run `make clean`.

### 2. `POLICY_VIOLATION`: No File Writes
*   **Cause:** An agent (usually Developer or Queen) sent a response without using `<file_write>` tags when they were expected to.
*   **Solution:** Check if the model is having context window issues. Usually, a `make clean` to refresh the session helps.

### 3. `HISTORY_VIOLATION`: Missing Tasks
*   **Cause:** The Queen agent attempted to rewrite `TASKS.md` but accidentally deleted previous task history.
*   **Solution:** The Router automatically blocks this. You may need to manually restore `TASKS.md` from Git if the AI corrupted the file structure.

---

## 🌐 III. API & Networking (HTTP Exceptions)

| Exception / Error | Cause | Solution |
| :--- | :--- | :--- |
| `HTTP 429: Too Many Requests` | Rate limit hit (common on Groq). | Increase `loop_delay_seconds` in `agent_orchestrator.json`. |
| `HTTP 401: Unauthorized` | Invalid or missing API key in `.env`. | Check your keys and ensure they have the correct prefix (e.g., `gsk_`). |
| `HTTP 503: Service Unavailable` | LLM Provider is down. | The system will automatically attempt **Smart Fallback** if configured. |
| `TimeoutError` | Provider is too slow to respond. | Increase `http_read_timeout` in the configuration. |

---

## 🧹 IV. Parsing & Markdown Issues

### 1. The Malformed Checkbox
*   **Symptom:** You see `-[ ] TASK-001` or `- [x]TASK-001` (missing spaces).
*   **Cause:** Incorrect `re.sub` logic or AI formatting error.
*   **Solution:** Manually fix the space in `TASKS.md` to look exactly like `- [ ]` or `- [x]`. (Fixed in Kernel v1.5, but can happen if manually edited).

### 2. Header Parsing Failure
*   **Symptom:** `SESSION.md` or `TASKS.md` is not being updated, or log entries are empty.
*   **Cause:** Missing level 3 headers (e.g., `### [STATE]` instead of `### [STATE]`).
*   **Solution:** Ensure every header has a space after the `###` and the text is in `[UPPERCASE]`.

---

## 🧪 V. Quality Gate Failures (LINTING/TESTING)

### 1. `RUFF_FAIL` (Formatting)
*   **Solution:** Usually, the `Pedant` agent fixes this automatically via `autofix`. If it persists, check for syntax errors in your Python file that prevent the formatter from running.

### 2. `MYPY_FAIL` (Type Safety)
*   **Solution:** Mypy errors are treated as **Logic Errors**. The system will route the task back to the `Developer`. If the Developer can't fix it, you must manually add the missing Type Hints.

### 3. `TEST_FAIL` (Pytest)
*   **Solution:** Look at the `### [FEEDBACK]` in `SESSION.md`. It contains the short traceback. Fix the logic in `src/` to match the expectations in `tests/`.

---

## 🛠️ VI. Maintenance Commands Matrix

| Command | Action | When to use? |
| :--- | :--- | :--- |
| `make status` | Shows current state and HALT reason. | First step in any troubleshooting. |
| `make clean` | Resets Agent Section, clears HALT/BLOCKED. | When the AI is stuck in a loop. |
| `make validate` | Checks system file integrity. | After manual file restructuring. |
| `make index` | Updates the codebase map (`AGENTS.md`). | When the AI "forgets" about new files. |
| `make purge` | Clears all Python caches and temp files. | Weird import errors or old code residue. |

---

## 🧠 Best Practice for Operators
If the system fails repeatedly on the same task:
1. Stop the pipeline.
2. Read the `FEEDBACK` section.
3. Write a specific instruction in `SESSION.md` -> `## [USER_SECTION]` -> `### [CONTEXT]` (e.g., *"Stop using Union[int, float], use float only!"*).
4. Run `make pipeline` again.

**Agent-CI-Lens is a tool — you are the Pilot. Don't let the machine fly into a storm without guidance.**