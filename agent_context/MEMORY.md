# Agent-CI-Lens: Long-Term Memory (Model 6.0)

## Project Context
This project is a Python-based Agentic CI/CD Orchestrator (Agent-CI-Lens).
- **Core Engine:** Pydantic-backed State Machine (v1.5).
- **Networking:** Hardened stack using `httpx` (sync context manager) and `stamina` for retries.
- **VCS Strategy:** Native Python integration replacing legacy bash scripts.

## Technology Stack
- Language: Python 3.12
- Manager: uv
- Libraries: httpx, stamina, structlog, rich, pydantic.

## Execution & Delivery Strategy
- **Standard Flow:** Analyse -> Planning -> Executing -> Linting -> Testing -> Verifying -> VCS_DELIVERY.
- **VCS Delivery:** Controlled via `agent_orchestrator.json` (vcs_control).
- **Modes:** 
  1. `local_git`: Local branches and atomic commits.
  2. `github`: Automated PR creation and GHA polling via GitHub REST API.
  3. `local_act`: (Planned) Local GHA simulation.

## Architectural Constraints
- **Bimetric Separation:** System state and flags belong in `agent_context/SESSION.md` -> `### [FEEDBACK]`. Never write to `[USER_SECTION]`.
- **TDD Enforcement:** Every logic change requires a corresponding test in `tests/`.
- **Zero Theater:** No task is marked completed without verified tool output (Pass/Fail).
- **Self-Correction:** If VCS_DELIVERY (GHA) fails, the engine must route back to EXECUTING to fix cloud-specific issues.