# 🏛️ Agent-CI-Lens — Codebase Map (Model 6.1.1)

This map describes the architecture, logical layers, and operational protocols of the Agent-CI-Lens orchestrator.

```text
agent-ci-lens/
├── .agents/               # [PROFILES] AI behavior and persona definitions
│   ├── agent_registry.json# Profile registry (models, providers, allowed skills)
│   ├── architect.md       # Persona: Goal Specification Specialist (v1.1)
│   ├── auditor.md         # Persona: Security & Quality Gatekeeper (v1.1)
│   ├── developer.md       # Persona: Senior Python Engineer (v1.2)
│   ├── pedant.md          # Persona: Code Cleaner and Linter (v1.1)
│   └── queen.md           # Persona: Lead Architect & Strategic Planner (v1.4)
│
├── .claude/               # [SYSTEM] Hidden system configuration and machine cache
│   ├── cache/             # Machine-readable state (memory.db, HALT.flag, pytest-report)
│   ├── rules/             # Engineering Iron Laws and Python coding standards
│   └── skills             # [TOOLS] Atomic capabilities available to agents
│
├── agent_context/         # [MEMORY] Runtime state and long-term project memory
│   ├── MEMORY.md          # Project history and high-level identity (v6.1)
│   ├── SESSION.md         # Bimetric scratchpad for the current active loop
│   ├── TASKS.md           # Goal decomposition and technical progress tracking
│   └── TROUBLESHOOTING.md # [ACMI RAG] KB of known errors and their solutions
│
├── agent_core/            # [LOGIC] The Brain: Framework orchestration engine
│   ├── router_core/       # Internal framework modules
│   │   ├── agent_actions.py # Pydantic schemas (AtomicTask contract) (v1.1)
│   │   ├── engine.py      # Main State Machine & Dispatcher (v2.0.2)
│   │   ├── git_local.py   # Native Git Wrapper (v1.2)
│   │   ├── github_client.py # Native GitHub REST API Client (v1.2)
│   │   ├── gh_models.py   # Pydantic models for GitHub API (v1.0)
│   │   ├── llm.py         # Agnostic API Client & RAG Heuristics (v3.10.0)
│   │   ├── managers.py    # State managers for agent_context (v1.11.4)
│   │   ├── models.py      # Pydantic schemas & Telemetry models (v1.14)
│   │   └── utils.py       # Shared utilities and loaders (v1.11)
│   ├── indexer.py         # Generates codebase map for agents (v2.1)
│   ├── memory_engine.py   # ACMI SQLite Core (Migrations V6) (v6.0.0)
│   ├── spec_gen.py        # Goal Specification Generator (v1.1.1)
│   ├── router.py          # CLI entry point
│   └── validator.py       # Shield: Integrity shield (v9.0)
│
├── agent_tests/           # [SYSTEM QA] Framework-level unit tests (Kernel)
├── src/                   # [APP] Target application source code
├── tests/                 # [APP QA] Unit tests for the target application
│
├── .env                   # [SECRETS] API keys, Provider Config, Mock toggles
├── agent_orchestrator.json# [CONFIG] Master pipeline settings
├── CHANGELOG.md           # Project evolution history
├── Makefile               # [CONTROL PANEL] Main interface for operators (v5.21)
├── pyproject.toml         # Toolchain and quality gate configuration
└── uv.lock                # Deterministic dependency lockfile
```

## I. Core Engine v2.0 (The Central Dispatcher)
The framework has evolved from a simple linear loop to a **Dispatcher-driven State Machine**. The `_execute_stage` method in `engine.py` acts as the central brain.

| State | Agent | Execution Type | Responsibility |
| :--- | :--- | :--- | :--- |
| **STRATEGY** | **Queen** | LLM | **Atomic Planning:** Decomposes goals into a strict `AtomicTask` (Code + Test). |
| **EXECUTING** | **Developer** | LLM | **Implementation:** Writes logic in `src/` and tests in `tests/`. |
| **LINTING** | **Pedant** | Hybrid | **Quality:** 1. Local `ruff` autofix. 2. AI Pedant fallback with attempt history. |
| **TESTING** | - | Subprocess | **Verification:** Runs `pytest` in a **Read-Only Lock** mode. No LLM allowed. |
| **VERIFYING** | **Auditor** | LLM | **Audit:** Final check after automated "Pre-flight Compression". |
| **VCS_DELIVERY** | **Router** | Native API | **Delivery:** Git push, PR creation, and GHA status polling. |

## II. ACMI RAG v2.0 (Intelligence Layer)
The **Agent-CI Memory Intelligence** system uses a tiered retrieval strategy:
1.  **Deterministic Mandatory Rules:** Injected directly into the prompt (e.g., *No inline imports*).
2.  **Semantic Contextual Search:** FTS5 BM25 search retrieves the top 6 rules relevant to task keywords.
3.  **Heuristic Keyword Extractor:** Prioritizes `backtick` terms and technical intent.
4.  **Organic Reflections:** Stores post-mortem lessons learned from past failures.

## III. Token Telemetry & Monitoring
The system implements full observability of AI costs through the `execution_logs` database table. Every API call logs `prompt_tokens`, `completion_tokens`, and `duration_ms` with provider-specific parsing.

## IV. Bimetric Safety Protocols
*   **Bimetric Shield:** Ensures that AI agents cannot modify user-owned sections or system core files.
*   **Testing Safety Lock:** A physical engine block that prevents any `FileWrite` operation during the TESTING state.

## V. Memory Management Philosophy: Agent-CI-Lens vs. Letta (MemGPT)
While emerging frameworks like Letta (MemGPT) focus on "Virtual Memory Paging" (agent-driven), Agent-CI-Lens prioritizes a "Hypervisor-driven" hard-state approach optimized for CI/CD.

| Feature | Letta / MemGPT | Agent-CI-Lens |
| :--- | :--- | :--- |
| **Memory Management** | **Agent-Driven:** Agent decides what to store/page. | **Hypervisor-Driven:** Engine manages context via RAG. |
| **Cognitive Load** | High (Agent manages logic + memory). | **Low:** Agent focuses purely on implementation. |
| **Auditability** | ❌ Low (Memory stored in hidden JSON/DB). | ✅ **High:** Human-readable Markdown (`SESSION.md`). |
| **Reproducibility** | ❌ Non-deterministic. | ✅ **High:** Git-linked state snapshots. |
| **Trust Model** | Probabilistic. | **Deterministic:** Hard-coded "Iron Laws" (Mandatory Rules). |

**Inference:** In a production environment, predictability and auditability are more valuable than memory flexibility. By offloading memory management to the Hypervisor, we eliminate hallucinations about the system's own state.
