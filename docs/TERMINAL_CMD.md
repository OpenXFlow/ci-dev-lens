# 🛠️ Agent-CI-Lens User Guide: Terminal & Environment (Model 6.1)

## 1. Core Orchestration Commands

The `Makefile` serves as your primary control panel. Each command is designed to maintain the strict boundary between the human operator and the autonomous agents.

*   **`make boot`** (Full Initialization)
    *   **Action:** Syncs dependencies via `uv`, runs system validation, and indexes the codebase.
    *   **Use Case:** Run this first in every new environment or after a major core update.

*   **`make pipeline`** (Start Autonomous Engine)
    *   **Action:** Launches the main Python process in autonomous mode.
    *   **Logic:** Reads `TASKS.md`, invokes agents, and applies changes to `src/` and `tests/`.

*   **`make mock`** (Simulation Mode)
    *   **Action:** Runs the pipeline using predefined mock responses to save API tokens.
    *   **Use Case:** Testing state machine logic or RAG injection without costs.

*   **`make spec TASK="description"`** (Goal Specification)
    *   **Action:** Invokes the **Architect** agent to transform a vague idea into a high-fidelity `INTENT/CONSTRAINTS/METRIC` goal.
    *   **Output:** Structured Markdown to be pasted into `TASKS.md`.

*   **`make status`** (Diagnostics)
    *   **Action:** Reports HALT status, current session state, and a summary of Token Telemetry.

*   **`make clean`** (Smart Reset)
    *   **Action:** Wipes the agent's work session (ACTION_LOG, FEEDBACK) but preserves human instructions in the User Section. Resets state to `IDLE`.

---

## 2. Token Telemetry Suite (Cost & Performance Monitoring)

Model 6.1 introduces persistent SQL-based tracking of all LLM interactions to monitor costs and ROI.

*   **`make tokens-last`**
    *   **Usage:** Shows detailed token breakdown (Prompt vs. Completion) for the most recent GOAL.
*   **`make tokens-today`**
    *   **Usage:** Shows cumulative usage in the last 24 hours.
*   **`make tokens-total`**
    *   **Usage:** Shows the all-time project total usage and average response times per provider.
*   **`make tokens GOAL=001`**
    *   **Usage:** Filters telemetry for a specific Goal ID.
*   **`make tokens-reset`**
    *   **Usage:** Nukes the entire telemetry history (requires manual confirmation).
*   **`make tokens-remove-legacy`**
    *   **Usage:** Cleans up old database records that are missing provider metadata.

---

## 3. Quality & Testing

*   **`make lint` / `make lint-fix`**
    *   **Action:** Runs `ruff` and `mypy`. `lint-fix` attempts to automatically correct formatting and simple import errors.
*   **`make test`**
    *   **Action:** Executes `pytest` on the application code (`tests/`).
*   **`make test-kernel`**
    *   **Action:** Executes `pytest` on the orchestrator's core logic (`agent_tests/`).
*   **`make validate`**
    *   **Action:** Performs a Pydantic-based integrity check of `.env`, `agent_orchestrator.json`, and the directory structure.

---

## 4. Knowledge Base (ACMI RAG)

*   **`make knowledge-add CATEGORY="X" CONTENT="Y" [MANDATORY=true]`**
    *   **Action:** Adds a new engineering rule to the persistent SQLite database.
    *   **Mandatory Flag:** If `true`, the rule is injected into every relevant prompt regardless of search relevance.
*   **`make knowledge-export-debug FILE="debug.json"`**
    *   **Action:** Exports the entire `knowledge_bank` table to a JSON file for manual auditing or backup.

---

## 5. Maintenance

*   **`make index`**
    *   **Action:** Updates the codebase AST map (`AGENTS.md`) so agents can "see" current function signatures.
*   **`make purge`**
    *   **Action:** Clears temporary caches and executes a DB `VACUUM` to reclaim disk space.
*   **`make purge --hard`**
    *   **Action:** **Dangerous.** Deletes the entire `memory.db` and Knowledge Bank.

---

## 6. Supported Environments

Agent-CI-Lens is optimized for **Unix-like environments** (Linux/macOS) via Docker:

1.  **Dev Container (Default):** Runs in a Debian-based container with `uv` and `sqlite3` pre-installed.
2.  **WSL2 (Windows):** Fully supported. Mirror the Linux setup.
3.  **macOS:** Fully supported natively.

**Note:** Native Windows (PowerShell/CMD) is **unsupported** due to the heavy reliance on POSIX-compliant Makefile syntax and Bash-based agent skills.
