# 🛠️ TROUBLESHOOTING GUIDE: Agent-CI-Lens (Model 6.0)

This document provides solutions for common exceptions, system locks, and state machine failures within the **Model 6.0** architecture.

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
*   **Cause:** A specific task has failed the maximum number of times (defined in `max_retries`). The orchestrator stops to prevent infinite loops and credit waste.
*   **Solution:**
    1.  Check `agent_context/SESSION.md` -> `### [FEEDBACK]` for the `LAST_ERROR`.
    2.  If the AI is "stuck," manually fix the code/test or provide a corrective hint in the `[CONTEXT]` section.
    3.  Reset the attempt counter in `TASKS.md` back to `[attempts: 0]` or run `make clean`.

### 2. `POLICY_VIOLATION`: No File Writes
*   **Cause:** An agent (usually Developer or Queen) sent a response without using `<file_write>` tags when they were expected to. This is common if the LLM is confused or hits an internal error.
*   **Solution:** Check the agent's `<thinking>` block in the logs. A `make clean` to refresh the session often helps.

### 3. `HISTORY_VIOLATION`: Missing Tasks
*   **Cause:** The Queen agent attempted to rewrite `TASKS.md` but accidentally deleted previous task history. This happens when the Pydantic model response is incomplete.
*   **Solution:** The Router automatically blocks this. No action is needed, as the system protects itself. The agent will retry on the next loop.

---

## 🧠 III. Agent Hallucinations & Logical Loops

### 1. Auditor "False Memory" Loop
*   **Symptom:** The `VERIFYING` stage fails repeatedly, even though tests and linting pass. The Auditor's feedback seems nonsensical or references past errors.
*   **Cause:** The `ACTION_LOG` is too long or contains old failure messages, confusing the Auditor.
*   **Solution:**
    1. **Pre-flight Compression:** This is now automated. The engine cleans the log before calling the Auditor.
    2. **Muzzle Patch:** Update `.agents/auditor.md` with a rule that forces it to trust `RESULT:PASS` from skills and not critique test quality.

### 2. Queen "Looping Inception"
*   **Symptom:** The system completes a goal but then immediately starts re-planning it, creating `TASK-002`, `TASK-003`, etc., for the same goal.
*   **Cause:** The Queen's prompt is too "eager," causing her to generate new tasks if the `GOAL-XXX` is not yet marked `[x]`.
*   **Solution:** Update `.agents/queen.md` with the **`NO-DUPLICATE PLANNING`** rule, which explicitly forbids creating new tasks if any task is still pending (`[ ]`).

---

## 🌐 IV. API & Networking (HTTP Exceptions)

| Exception / Error | Cause | Solution |
| :--- | :--- | :--- |
| `HTTP 429: Too Many Requests` | Rate limit hit (common on Groq). | Increase `loop_delay_seconds` in `agent_orchestrator.json`. |
| `HTTP 401: Unauthorized` | Invalid or missing API key in `.env`. | Check your keys and ensure they have the correct prefix (e.g., `gsk_`). |
| `HTTP 503: Service Unavailable` | LLM Provider is down. | The system will automatically attempt **Smart Fallback** if configured. |
| `TimeoutError` | Provider is too slow to respond. | Increase `http_read_timeout` in the configuration. |

---

## ☁️ V. VCS & Git Failures

### 1. `fatal: 'origin' does not appear to be a git repository`
*   **Cause:** The Git instance inside the container is not linked to a remote GitHub repository.
*   **Solution:** Configure the remote URL in your terminal:
    ```bash
    git remote add origin https://github.com/YourUser/YourRepo.git
    ```

### 2. `fatal: Authentication failed` during `git push`
*   **Cause:** The GITHUB_TOKEN is invalid, expired, or lacks the necessary permissions (`repo`, `workflow`).
*   **Solution:**
    1. Generate a new "Classic" Personal Access Token on GitHub with `repo` and `workflow` scopes.
    2. Update the `GITHUB_TOKEN` in your `.env` file.
    3. For interactive sessions, you may need to update the remote URL with the token: `git remote set-url origin https://oauth2:YOUR_NEW_TOKEN@github.com/...`

### 3. `422 Unprocessable Entity` on PR Creation
*   **Cause:** The system tried to create a Pull Request for a branch that already has an open PR. This is expected behavior during a retry loop.
*   **Solution:** No action needed. The "Resilience Patch" (v1.22+) automatically detects this error, logs `PR already exists...`, and continues to the GHA polling step.

---

## 🧪 VI. Quality Gate Failures (LINTING/TESTING)

### 1. `RUFF_FAIL` (Formatting)
*   **Solution:** This is now handled by the **"Dumb Pedant"**. The system runs `ruff --fix` automatically. If it persists, it indicates a complex syntax error that `ruff` cannot parse, which will be escalated to the AI Pedant.

### 2. `MYPY_FAIL` (Type Safety)
*   **Solution:** Mypy errors are treated as **Logic Errors**. The system will route the task back to the `Developer`. If the Developer can't fix it, you must either manually fix the code or provide a hint in the `[CONTEXT]` section.

### 3. `TEST_FAIL` (Pytest)
*   **Solution:** Look at the `### [FEEDBACK]` in `SESSION.md`. It contains the short traceback. The system will automatically route back to the `Developer` for a bug fix.

---

## 🛠️ VII. Maintenance Commands Matrix

| Command | Action | When to use? |
| :--- | :--- | :--- |
| `make status` | Shows current state and HALT reason. | First step in any troubleshooting. |
| `make clean` | Resets Agent Section, clears HALT/BLOCKED. | When the AI is stuck in a loop. |
| `make validate` | Checks system file integrity. | After manual file restructuring. |
| `make index` | Updates the codebase map (`AGENTS.md`). | When the AI "forgets" about new files. |
| `make purge` | Clears all Python caches and temp files. | Weird import errors or old code residue. |


## Best Practice for Operators
If the system fails repeatedly on the same task:
1. Stop the pipeline.
2. Read the `FEEDBACK` section.
3. Write a specific instruction in `SESSION.md` -> `## [USER_SECTION]` -> `### [CONTEXT]` (e.g., *"Stop using Union[int, float], use float only!"*).
4. Run `make pipeline` again.

**Agent-CI-Lens is a tool and you are the Pilot. Don't let the machine fly into a storm without guidance.**
