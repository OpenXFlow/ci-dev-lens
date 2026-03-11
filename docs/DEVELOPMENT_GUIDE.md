# 🏗️ Agent-CI-Lens: Framework Development Guide (Model 6.0)

This guide is intended for developers who wish to modify the orchestrator kernel, add new skills, or extend the system's capabilities.

---

## 1. Internal Coding Standards
When writing code for the **Agent-CI-Lens** kernel (`agent_core/`), you must adhere to higher standards than the target application:

*   **Pydantic First:** Any new configuration or structured data must be defined as a Pydantic model in `agent_core/router_core/models.py`. The system relies on this for type safety and validation.
*   **Agnostic Logic:** Never hardcode provider names (like "Groq") or file paths. Use the `EnvConfig` credentials map and `ROOT` constants.
*   **Zero-Side-Effects:** Kernel utilities should be pure functions whenever possible to ensure they are easily testable.
*   **Minimal Dependencies:** Do not add external libraries to `pyproject.toml` unless absolutely necessary. Prefer standard library modules (e.g., `sqlite3`, `tomllib`).

---

## 2. Adding a New Skill
To give agents a new capability (e.g., "Database Migrator"), follow these steps:

### Step A: Create the Script
Add your execution logic (Python or Bash) to a new subdirectory in `.claude/skills/`.
*   Example: `.claude/skills/db-manager/scripts/migrate.py`
*   Ensure the script returns a `RESULT:` tag (e.g., `RESULT:PASS`, `RESULT:MIGRATE_FAIL`) as its final output line.

### Step B: Define the Metadata
Create a `SKILL.md` file in that same folder describing the usage, arguments, and expected results for the AI.

### Step C: Register in the Engine
Update the `_run_skill_process` method in `agent_core/router_core/engine.py`. Add your skill to the `s_map` dictionary:```python
s_map = {
    "db-manager": ".claude/skills/db-manager/scripts/migrate.py",
    # ...
}
```

---

## 3. Extending the State Machine
The system logic lives in `agent_core/router_core/engine.py` within the `run_pipeline` loop.

*   To add a **new State** (e.g., `DOCUMENTING`):
    1.  Add the state name to the `stages` list in `run_pipeline` (e.g., `("DOCUMENTING", "developer")`).
    2.  Update `agent_orchestrator.json` to include the new stage in `workflow_local`, making sure to define its `requires_llm` flag.
    3.  Create or update a Persona file in `.agents/` to handle the logic for this new state.
    4.  Update the Pydantic `OrchestratorConfigModel` in `models.py` if the structure changes.

---

## 4. Kernel Testing (`agent_tests/`)
Before committing any changes to the framework, you **must** run the kernel test suite and ensure all tests pass (currently 117/117).

```bash
make test-kernel
```

### Adding Kernel Tests:
*   **Specialization:** Do not add all tests to `test_router.py`. Use the specialized files:
    *   `test_git_wrapper.py` for low-level Git commands.
    *   `test_vcs_flow.py` for high-level Git/GitHub integration logic in the engine.
    *   `test_router.py` for core state management, agent calls, and managers.
*   **Fixtures:** Use the `tmp_project` fixture from `conftest.py`. It creates a mock Model 6.0 environment in a temporary directory.
*   **Test for Fail-Fast behavior:** Ensure the system triggers a `HALT` or `BLOCKED` state when expected.
*   **Test for Resilience:** Ensure the system correctly handles API errors, rollbacks, and state inconsistencies.

---

## 5. The "Atomic Feature" Workflow
When implementing a complex feature in the target application using the orchestrator, follow this 3-step loop:

1.  **Define the Goal:** Add a `GOAL-XXX` to `TASKS.md`.
2.  **Guide the Context:** Add specific technical constraints to `SESSION.md` (e.g., *"Use SQLAlchemy for the models"*).
3.  **Monitor the Flow:** Run `make pipeline`. If the agent gets stuck, analyze the `FEEDBACK` and `ACTION_LOG` sections in `SESSION.md` to understand the root cause. Adjust context or agent personas as needed.

---

## 💡 Framework Maintenance Tips
*   **Log Ambiguity:** If terminal logs become messy, check `utils.py`. We use specific emojis to make the state transitions scanable at a glance.
*   **Dependency Management:** Always use `uv add --group dev <package>` for kernel tools to keep them separated from the target application's production dependencies.
*   **Configuration First:** Before modifying Python code, always check if the desired behavior can be achieved by adjusting `agent_orchestrator.json`.
