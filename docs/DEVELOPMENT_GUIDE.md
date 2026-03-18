# 🏗️ Agent-CI-Lens: Framework Development Guide (Model 6.1)

This guide is intended for developers who wish to modify the orchestrator kernel, add new skills, or extend the system's capabilities.

---

## 1. Internal Coding Standards (Kernel)
When writing code for the **Agent-CI-Lens** kernel (`agent_core/`), you must adhere to higher standards than the target application:

*   **Pydantic & Type Safety:** Every core data structure MUST be a Pydantic V2 model in `agent_core/router_core/models.py`. 
*   **Telemetry Awareness:** Any method invoking an LLM must capture and propagate `usage` metadata to be recorded in the `execution_logs` table.
*   **Agnostic Design:** Maintain provider-neutrality. Use the `_parse_usage` parser in `llm.py` to handle cross-provider metadata differences.

---

## 2. Adding a New Skill
To give agents a new capability, follow these steps:

### Step A: Create the Script
Add your execution logic (Python or Bash) to a new subdirectory in `.claude/skills/`.
*   Ensure the script returns a `RESULT:` tag (e.g., `RESULT:PASS`, `RESULT:ERROR`) as its final output line.

### Step B: Register in the Engine
Update the `_run_skill_process` method in `agent_core/router_core/engine.py`. Add your skill to the `s_map` dictionary.

### Step C: Mandatory Rule Injection
If the new skill requires specific usage patterns (e.g., a specific CLI flag), add a corresponding rule to the **ACMI Knowledge Bank** and flag it as `is_mandatory=1` for the relevant agent role.

---

## 3. Extending the Dispatcher (State Machine)
The core logic has moved from a linear loop to a **Dispatcher Architecture**.

*   **`run_pipeline`**: Manages the high-level sequence of stages.
*   **`_execute_stage`**: The central dispatcher. If you add a new stage, you must define its routing here:
    *   Determine if it requires an LLM (`requires_llm` flag).
    *   Map it to a local skill or an AI agent.
    *   Implement any "Pre-flight" logic (like context compression).

---

## 4. Kernel Testing (`agent_tests/`)
Before committing any changes to the framework, you **must** run the kernel test suite.

```bash
make test-kernel
```

### Critical Test Areas:
*   **Telemetry Tests:** Verify that token counts are correctly parsed and stored in SQLite.
*   **Dispatcher Tests:** Ensure that `requires_llm: false` stages (like TESTING) never trigger an LLM call.
*   **RAG Tests:** Confirm that mandatory rules are correctly injected at the top of the prompt.
*   **Bimetric Shield:** Verify that core files remain read-only for agents.

---

## 5. The "Karpathy-Style" Workflow
When developing the framework itself, treat every core change as an experiment:

1.  **Define Goal:** Use `make spec` to define a clear architectural goal.
2.  **Monitor ROI:** Use `make tokens-last` after kernel tests to evaluate the "token cost" of your change.
3.  **Reflection:** If a kernel test fails, use the `REFLECTION` state to analyze the log and store the fix in the database for the next dev cycle.

---

## 💡 Framework Maintenance Tips
*   **Database Migrations:** All schema changes must be added as a new numbered entry in the `MIGRATIONS` dictionary within `memory_engine.py`.
*   **Clean Slate:** Use `make tokens-reset` before starting a major refactor to get clean telemetry data for your changes.
