# Agent-CI-Lens: Long-Term Memory (Model 6.1)

## Project Context
This project is an Agentic CI/CD Orchestrator (Agent-CI-Lens) designed for autonomous development loops.
- **Core Engine:** Pydantic-backed State Machine (v1.6) with strict Atomic Task contracts.
- **Intelligence Layer:** ACMI (Agent-CI Memory Intelligence) - A dual-source RAG system using SQLite FTS5 for rules and reflections.
- **Resilience:** Multi-provider key rotation and automated fallback (e.g., Groq -> Mistral).

## Technology Stack
- **Language:** Python 3.12 (Strict typing with Mypy).
- **Toolchain:** `uv` exclusively for dependency and environment management.
- **Infrastructure:** Pydantic (validation), Instructor (structured LLM), Stamina (retries), Structlog (logging).

## Execution & Delivery Strategy
- **Standard Flow:** Analyse -> STRATEGY (Planning) -> EXECUTING -> LINTING -> TESTING -> VERIFYING -> VCS_DELIVERY.
- **Atomic Contract:** Every task MUST be defined as an `AtomicTask` containing both `source_file` and `test_file`.
- **VCS Delivery:** GitHub API integration for PR creation and GHA (GitHub Actions) status polling.
- **Self-Correction:** The engine automatically reverts states upon GHA failure to allow AI-driven bug fixes in the cloud.

## Architectural Constraints
- **Bimetric Separation:** Strict isolation between `[USER_SECTION]` (Human-owned) and `[AGENT_SECTION]` (Machine-owned) in `SESSION.md`.
- **ACMI RAG Priority:** Human-verified rules always take precedence over AI-generated reflections in the prompt.
- **Zero Theater:** Results are only valid if verified by tool output (RESULT:PASS).
- **YAGNI & Cohesion:** Implement only requested logic; group by domain responsibility.