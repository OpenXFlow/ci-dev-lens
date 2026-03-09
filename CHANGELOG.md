# Changelog

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

## [v5.6.0] - 2025-02-25
### Added
- Initial Gold Master release. Core architecture (Router, Validator, Indexer) and base skill suite.

