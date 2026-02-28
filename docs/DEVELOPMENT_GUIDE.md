# 🏗️ Agent-CI-Lens: Framework Development Guide

This guide is intended for developers who wish to modify the orchestrator kernel, add new skills, or extend the system's capabilities.

---

## 1. Internal Coding Standards
When writing code for the **Agent-CI-Lens** kernel (`agent_core/`), you must adhere to higher standards than the target application:

*   **Pydantic First:** Any new configuration or structured data must be defined as a Pydantic model in `models.py`.
*   **Agnostic Logic:** Never hardcode provider names (like "Groq"). Use the `EnvConfig` credentials map.
*   **Zero-Side-Effects:** Kernel utilities should be pure functions whenever possible to ensure they are easily testable.

---

## 2. Adding a New Skill
To give agents a new capability (e.g., "Database Migrator"), follow these steps:

### Step A: Create the Script
Add your execution logic (Python or Bash) to a new subdirectory in `.claude/skills/`.
*   Example: `.claude/skills/db-manager/scripts/migrate.py`

### Step B: Define the Metadata
Create a `SKILL.md` file in that same folder describing the usage, arguments, and expected results for the AI.

### Step C: Register in the Engine
Update the `_execute_skill` method in `agent_core/router_core/engine.py`. Add your skill to the `s_map` dictionary:
```python
s_map = {
    "db-manager": ".claude/skills/db-manager/scripts/migrate.py",
    # ...
}
```

---

## 3. Extending the State Machine
The system logic lives in `agent_core/router_core/engine.py` within the `run_pipeline` loop.

*   To add a **new State** (e.g., `DOCUMENTING`):
    1.  Add the state name to the `stages` list in `run_pipeline`.
    2.  Update `agent_orchestrator.json` to include the new stage in `workflow_local`.
    3.  Update the Pydantic `OrchestratorConfigModel` in `models.py` if the structure changes.

---

## 4. Kernel Testing (`agent_tests/`)
Before committing any changes to the framework, you **must** run the kernel test suite:

```bash
make self
```

### Adding Kernel Tests:
*   Use the `tmp_project` fixture from `conftest.py`. It creates a mock Model 5.3 environment in a temporary directory.
*   Test for **Fail-Fast** behavior: Ensure the system triggers a `HALT` or `BLOCKED` state when expected.
*   Test the **Smart Parser**: Ensure new `.env` patterns are correctly mapped to Pydantic models.

---

## 5. The "Atomic Feature" Workflow
When implementing a complex feature in the target application using the orchestrator, follow this 3-step loop:

1.  **Define the Goal:** Add a `GOAL-XXX` to `TASKS.md`.
2.  **Guide the Context:** Add specific technical constraints to `SESSION.md` (e.g., *"Use SQLAlchemy for the models"*).
3.  **Monitor the Flow:** Run `make flow`. If the agent gets stuck in a loop, do not just restart; update `TROUBLESHOOTING.md` with the fix so the machine learns.

---

## 💡 Framework Maintenance Tips
*   **Log Ambiguity:** If terminal logs become messy, check `utils.py`. We use specific emojis to make the state transitions scanable at a glance.
*   **Dependency Management:** Always use `uv add --group dev <package>` for kernel tools to keep them separated from the target application's production dependencies.

