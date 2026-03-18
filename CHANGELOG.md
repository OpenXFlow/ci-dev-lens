# Changelog

## [Model 6.1.0] - 2026-03-16
### Added
- **Engine v2.0 (Central Dispatcher):** Refactored pipeline execution into a central dispatcher (`_execute_stage`), eliminating "Agentic Theater" and ensuring robust stage routing.
- **Token Telemetry & Monitoring:** Implemented persistent SQL-based tracking of LLM usage (`prompt`, `completion`, `total`) with provider-specific parsing (Groq, Mistral, OpenAI, Anthropic).
- **Advanced Telemetry Suite:** Added new management commands: `make tokens-last`, `make tokens-today`, `make tokens-total`, and `make tokens-reset` for granular cost and ROI analysis.
- **Deterministic Mandatory Rules:** Introduced V5 DB migration for `is_mandatory` flags, ensuring "Iron Laws" (like TDD atomicity) are injected into prompts regardless of FTS5 search results.
- **Architect Specification Tool:** Integrated `spec_gen.py` (Architect persona) and `make spec` to transform vague ideas into high-fidelity `INTENT/CONSTRAINTS/METRIC` goal definitions.
- **Role-Based RAG Filtering:** Implemented `AGENT_CATEGORY_MAP` to ensure agents receive only contextually relevant engineering rules based on their role.

### Changed
- **Atomic Task Contract:** Replaced string-based tasking with a strict Pydantic `AtomicTask` model, mandating simultaneous `source_file` and `test_file` definition to enforce TDD integrity.
- **Implicit TDD DNA:** Updated Queen's system prompt to mandate testing by default (with explicit opt-out) and strictly forbid "skeleton" or "placeholder" task planning.
- **Semantic RAG Heuristics:** Upgraded keyword extraction in `llm.py` with backtick prioritization, expanded stop-words filtering, and positional weighting (technical intent over verbs).
- **Enhanced Pipeline Logging:** Real-time terminal output now distinguishes between `Planned` (synthetic goals) and `Finished` (atomic tasks) for better operator observability.

### Fixed
- **TESTING Stage Integrity:** Resolved a critical arch-bug where the TESTING stage unnecessarily invoked LLM agents; it now runs as a pure, read-only local subprocess.
- **TESTING Safety Lock:** Implemented a physical lock in `engine.py` that blocks all file write attempts during the verification phase.
- **State Leakage Protection:** Hardened the `FEEDBACK` manager to clean up transient error states (`LAST_ERROR`) while preserving persistent goal metadata (`PLANNED`).
- **Linter Ping-Pong Prevention:** Introduced an accumulative feedback buffer for the `LINTING` stage, allowing the Pedant agent to see the history of the last 3 attempts.
- **Resilient Formatting:** Patched `Makefile` to handle environments missing the `column` utility without crashing the status report.

---

## [Model 6.0.0] - 2026-03-09
### Added
- **Smart Speed & Cost Optimization:** Implemented "Dumb Pedant" (local linting) and "Pre-flight Compression" (context pruning before auditing), significantly reducing API costs and LLM hallucinations.
- **Agent Safety Shield:** Integrated a core-level safeguard (Sanitization Shield) to prevent agents from prematurely marking tasks as completed (Anti-Privilege Escalation).
- **VCS Idempotency:** The system now intelligently handles existing Pull Requests (422 errors) and automatically waits for cloud test results via GHA Polling.
- **Goal-Based Branching:** Automated branching logic tied to the high-level objective (`feat/GOAL-XXX`) to ensure branch isolation and protect the `main` branch.

### Fixed
- **Semantic Parser:** Robust Regex-based parsing for `SESSION.md` and `TASKS.md`, implementing Postel's Law to tolerate minor formatting inconsistencies.
- **Routing Logic:** Fixed a state gap where the pipeline now correctly re-runs Linter and Testing stages after any code change or rollback.
- **Skill Standardization:** All utility scripts translated to English, paths updated for Model 5.3+, and types hardened for 100% Mypy compliance.

---

## [Model 5.5.0] - 2026-03-07
### Added
- **Native VCS Integration:** Replaced legacy bash scripts with native Python Git and GitHub API clients.
- **Look-Ahead Completion:** Automatic goal closure immediately following the final task execution.
- **State-Sync Logic:** Introduced Micro-commits to synchronize orchestrator meta-state to the cloud in real-time.

---

## [Model 5.4.0] - 2026-03-02
### Added
- **Network Hardening:** Migrated to `httpx` + `stamina` for enterprise-grade resilience against API timeouts and rate limits.
- **Structured Logging:** Implemented `structlog` and `rich` for beautiful local console output and machine-readable JSON logs in CI.

---

## [Model 5.3.0] - 2026-03-01
### Added
- **Bimetric Architecture:** Strict separation of human instructions from agent activity via the `[FEEDBACK]` section.
- **E2E Testing:** Introduced automated End-to-End verification flows (e.g., Palindrome flow).
- **Pydantic State:** Transitioned system configuration and state management to strict Pydantic V2 models.

---

## [v5.2.0] - 2025-02-25
### Added
- Initial Gold Master release. Core architecture (Router, Validator, Indexer) and base skill suite.
