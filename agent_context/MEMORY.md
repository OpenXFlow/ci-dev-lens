# Agent-CI-Lens: Long-Term Memory

## Project Context
This project is a Python calculator (`src/calculator.py`).
- **Current Run Context:** Always check `agent_context/SESSION.md` for specific operator instructions and the active state.
- **Goal Registry:** Always refer to `agent_context/TASKS.md` for high-level requirements (User Queue) and technical progress tracking.

## Technology Stack
- Language: Python 3.12
- Manager: uv
- Testing: pytest

## Execution Strategy
- ACTIVE GOAL: Always prioritize requirements defined in `agent_context/TASKS.md` under `## [USER_QUEUE]`.
- TASK TRACKING: Technical steps are managed in `## [AGENT_PROGRESS]`.

## Architectural Constraints
- STRICT TDD: No production code without a corresponding test.
- GOOGLE STYLE: Use Google Style Docstrings for all public methods.
- COMPLETION: Do not create redundant tasks. Once the requirements in `[USER_QUEUE]` are met and tests pass, the goal is finished.