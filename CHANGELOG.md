# Changelog

All notable changes to the Agent-CI-Lens project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Model 5.3.0] - 2026-02-28
### Added
- **Licensing:** MIT License headers added to all source files and a dedicated `LICENSE.md` in root.
- **Networking Hardening:** Implemented `loop_delay_seconds` for rate-limit protection and smart provider fallback (Groq -> Mistral).
- **Agent Pragmatism:** Introduced "Completion over Perfection" and explicit STOP CONDITION for the Queen agent to prevent redundant task generation.

### Changed
- **Linter Optimization:** Strict Ruff rules (ANN, TRY, PERF) enabled. Configured pragmatic docstyle ignores (D100, D104, D417) to prevent AI "Docstring Loops".
- **Truth Hierarchy:** Updated `MEMORY.md` to serve as the primary source of truth for agent reasoning over long-term goals.
- **Validation Shield:** Enhanced `validator.py` with deep Pydantic schema verification for all orchestrator settings.

### Fixed
- **Zero-Tolerance Quality:** Resolved 100% of Mypy and Ruff violations (unused arguments, type-hinting, docstyles).
- **Test Integrity:** Achieved 108/108 pass rate for kernel tests. Updated `conftest.py` fixtures to accurately mock the Model 5.3 structure.

---

## [Model 5.2.1] - 2026-02-27
### Added
- **Rate Limit Protection:** Added `loop_delay_seconds` to `agent_config.json` and implemented sleep logic in `engine.py`.
- `CHANGELOG.md` to track architectural evolution.
- `agent_native/` directory as an architectural marker for Phase 2 Rust integration.

### Changed
- **Massive Architectural Refactoring (Model 5.2):** Established strict bimetric isolation of the orchestrator from the target application workspace.
- Migrated kernel logic to `agent_core/`.
- Migrated system memory to `agent_context/`.
- Migrated framework tests to `agent_tests/`.

---

## [v7.7.0] - Autonomous Resilience and Bimetric Logic
### Added
- **Smart Fallback:** Added to `APIClient` for automatic provider switching.
- **Silent Sanitization:** Automatic removal of Markdown code blocks from AI responses.
- **Bimetric Section Logic:** Strictly separated `[USER_SECTION]` from `[AGENT_SECTION]`.

---

## [v6.0.0] - OOP Calculator & Infrastructure Split
### Changed
- **Infrastructure Split:** Split test suite into kernel and application logic.
- Refactored `calculator.py` to use an Object-Oriented (class-based) approach.

---

## [v5.6.0] - Gold Master
### Added
- Initial commit: Agent-CI-Lens v5.6 (Gold Master).
- Core architecture (Router, Validator, Indexer).
- Full skill suite (Testing, Security, Git, MCP).