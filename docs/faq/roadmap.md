# 🗺️ Agent-CI-Lens Strategic Roadmap

This document outlines the architectural evolution of the orchestrator, tracking our progress from a resilient core to a high-performance autonomous swarm.

---

## ✅ COMPLETED PHASES

### 📍 Phase 1: Network Hardening
**Goal:** Establish a resilient infrastructure for reliable AI communication.
*   **Networking:** Migrated from legacy `urllib` to `httpx` for modern session management.
*   **Resilience:** Integrated `stamina` for intelligent retries with exponential backoff.
*   **Observability:** Implemented structured logging via `structlog` and `rich`.

### 📍 Phase 2: Native VCS Integration
**Goal:** Remove external CLI dependencies and integrate directly with Version Control.
*   **Git Core:** Implemented a native Python Git wrapper for atomic local commits.
*   **GitHub API:** Developed a native REST client for automated PR creation and management.
*   **Auto-Closure:** Enabled "Look-Ahead Completion" to automatically finalize goals.

### 📍 Phase 3: Intelligence & Stability (Model 6.0)
**Goal:** Optimize pipeline speed, reduce API costs, and harden system logic.
*   **State Merging:** Consolidated Analyse and Planning into a unified `STRATEGY` phase.
*   **Dumb Pedant:** Introduced local `ruff` auto-fixes to reduce unnecessary LLM calls.
*   **Context Safety:** Implemented "Pre-flight Compression" to prevent Auditor hallucinations.

---

## 🚀 FUTURE PHASES (Path to 100/100)

### 📍 Phase 4: ACMI (Memory Intelligence)
**Goal:** Transition from text-based memory to a structured SQL/AST RAG system.
*   **Structured Storage:** Implement an SQLite core with WAL mode for high-integrity persistent state.
*   **Deep Indexing:** Utilize AST parsing to store and retrieve specific code signatures instead of full files.
*   **Self-Reflection:** Automated post-goal analysis to store error patterns and prevent future regressions.

### 📍 Phase 5: External Ecosystem (MCP Protocol)
**Goal:** Connect the orchestrator to external enterprise tools via Model Context Protocol.
*   **Real Integration:** Replace current mocks with a production-ready `mcp_client.py`.
*   **Tool Swarm:** Enable agents to independently interact with **Jira**, **Slack**, and external DBs.
*   **Automation:** Autonomous issue tracking and team notifications throughout the pipeline.

### 📍 Phase 6 & 8: The Fleet (Parallel Swarm)
**Goal:** Maximize development throughput via concurrent task execution.
*   **Parallel Agents:** Run multiple specialized agents simultaneously on independent tasks.
*   **Git Worktrees:** Support concurrent development across multiple isolated Git branches.
*   **Fleet Controller:** Central orchestration logic to manage dependencies and resolve merge conflicts.

### 📍 Phase 7: Native Acceleration (Rust Kernel)
**Goal:** Achieve enterprise-scale performance with a hybrid execution engine.
*   **Rust Indexer:** Port the AST indexing logic to Rust using `tree-sitter` for instant codebase mapping.
*   **Memory Safety:** Implement a low-level execution sandbox for generated code isolation.
*   **Performance:** Reduce system footprint and latency to sub-millisecond levels for large projects.

---
*Roadmap updated: 2026-03-09. All completed phases are verified with a 100% test pass rate.*