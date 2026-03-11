Ako **Senior Legacy Code Maintainer**, pristupujem k aktualizácii `ARCHITECTURE.md` s maximálnym rešpektom k pôvodnému obsahu a štruktúre.

### 🔍 Zoznam zmien:
1.  **Codebase Map:** Aktualizoval som stromovú štruktúru o nové súbory, ktoré sme vytvorili: `test_vcs_flow.py`, `test_git_wrapper.py` a `test_router_logs.py`. Zmenil som názvy `agent_config.json` na `agent_orchestrator.json` a `Makefile` commandy.
2.  **State Machine:** Tabuľku stavov som prepísal podľa našej novej **`STRATEGY`** fázy. Stavy `ANALYSE` a `PLANNING` sú teraz odstránené.
3.  **Dumb Pedant & Compression:** Do popisu fáz som explicitne pridal informáciu, že `LINTING` teraz začína "Dumb Pedant" optimalizáciou a `VERIFYING` začína "Pre-flight Compression".
4.  **Makefile & Terminology:** V popise "Control Panelu" som zmenil staré názvy (`make wake`, `make info`) na nové, ktoré reálne používame (`make boot`, `make status`).

Tu je kompletný, chirurgicky upravený súbor `ARCHITECTURE.md`.

--- START OF FILE docs/ARCHITECTURE.md ---
```markdown
# 🏛️ Agent-CI-Lens — Codebase Map (Model 6.0)

This map describes the architecture, logical layers, and operational protocols of the Agent-CI-Lens orchestrator.

```text
agent-ci-lens/
├── .agents/               # [PROFILES] AI behavior and persona definitions
│   ├── agent_registry.json# Profile registry (models, providers, allowed skills)
│   ├── auditor.md         # Persona: Security & Quality Gatekeeper (v1.1)
│   ├── developer.md       # Persona: Senior Python Engineer (v1.2)
│   ├── pedant.md          # Persona: Code Cleaner and Linter (v1.1)
│   └── queen.md           # Persona: Lead Architect & Strategic Planner (v1.2)
│
├── .claude/               # [SYSTEM] Hidden system configuration and machine cache
│   ├── cache/             # Machine-readable state (AGENTS.md, HALT.flag)
│   ├── rules/             # Engineering Iron Laws and Python coding standards
│   │ 
│   └── skills                      # [TOOLS] Atomic capabilities available to agents
│       ├── cascade-logic           # [CONTROL] Advanced task chaining
│       ├── context-compressor      # [OPTIMIZATION] ACTION_LOG pruning
│       │   ├── scripts/summarize.py# Python script for ACTION_LOG pruning (v1.4)
│       ├── git-manager             # [VCS] Legacy branch lifecycle scripts
│       ├── handoff-manager         # [PERSISTENCE] State preservation
│       │   ├── scripts/dump_state.py# State exporter (v1.2)
│       ├── mcp-bridge              # [INTEGRATION] External tool proxy (Slack, Jira)
│       │   ├── scripts/proxy.py    # Mockup for tool integration (v1.1)
│       ├── quality-gate            # [LINTING] Static code analysis
│       │   ├── scripts/check.sh    # Primary Quality Gate execution
│       ├── security-guard          # [SECURITY] Secret and vulnerability scanning
│       │   ├── scripts/scan.py     # Pre-commit security scanner (v1.1)
│       └── testing-pro             # [TESTING] Pytest execution and TDD
│           ├── scripts/coverage.py # Code coverage measurement tool (v1.2)
│           └── scripts/verify.py   # Pytest result formatting engine (v1.2)
│
├── .devcontainer/         # [INFRA] Docker-based isolated environment config
│   ├── devcontainer.json  # VS Code container settings and Python pathing
│   └── Dockerfile         # System dependencies (Python 3.12, UV, git)
│
├── agent_context/         # [MEMORY] Runtime state and long-term project memory
│   ├── MEMORY.md          # Project history and high-level knowledge
│   ├── SESSION.md         # Bimetric scratchpad for the current active loop
│   ├── TASKS.md           # Goal decomposition and technical progress tracking
│   └── TROUBLESHOOTING.md # [RAG] KB of known errors and their solutions
│
├── agent_core/            # [LOGIC] The Brain: Framework orchestration engine
│   ├── router_core/       # Internal framework modules
│   │   ├── agent_actions.py # Pydantic schemas for AI responses
│   │   ├── engine.py      # Main State Machine (v1.34)
│   │   ├── git_local.py   # Native Git Wrapper
│   │   ├── github_client.py # Native GitHub REST API Client
│   │   ├── gh_models.py   # Pydantic models for GitHub API
│   │   ├── llm.py         # Agnostic API Client & Prompt construction (v1.22)
│   │   ├── managers.py    # State managers for agent_context (v1.9)
│   │   ├── models.py      # Pydantic schemas for configuration (v1.9)
│   │   └── utils.py       # Shared utilities and loaders (v1.10)
│   ├── indexer.py         # Generates codebase map (AGENTS.md)
│   ├── router.py          # CLI entry point for human/machine interaction
│   └── validator.py       # Shield: Integrity check of secrets and structure
│
├── agent_native/          # [PERFORMANCE] Rust-based optimizations (Phase 2)
│   └── info.md            # Implementation roadmap for native workers
│
├── agent_tests/           # [SYSTEM QA] Framework-level unit tests (Kernel)
│   ├── conftest.py        # Shared fixtures
│   ├── e2e/test_e2e_palindrome.py # End-to-End test for Palindrome flow
│   ├── test_git_wrapper.py# Unit tests for GitLocalManager
│   ├── test_indexer.py    # Verification of codebase mapping logic
│   ├── test_models.py     # Unit tests for Pydantic configuration schemas
│   ├── test_router.py     # Core Engine unit tests (refactored)
│   ├── test_router_logs.py# Diagnostic test for prompt injection
│   ├── test_skills.py     # Unit tests for agent skills
│   ├── test_validator.py  # Verification of system integrity checks
│   └── test_vcs_flow.py   # Unit tests for VCS integration logic
│
├── src/                   # [APP] Target application source code (AI Playground)
│   └── __init__.py        # Makes src a valid Python package
│
├── tests/                 # [APP QA] Unit tests for the target application
│   └── __init__.py        # Makes tests a valid Python package
│
├── .env                   # [SECRETS] API keys (rotation support) and endpoints
├── .gitignore             # Git exclusion rules (venv, cache, local sessions)
├── agent_orchestrator.json# [CONFIG] Master settings and API Fallback Matrix
├── CLAUDE.md              # AI Onboarding: Absolute rules and Startup protocols
├── Makefile               # [CONTROL PANEL] Main interface for humans and GHA
├── pyproject.toml         # Python toolchain and dependency management
└── uv.lock                # Deterministic dependency lockfile
```

## I. System States (State Machine)
The system is a managed process. Every state has a strictly defined responsibility.

| State | Agent | Responsibility |
| :--- | :--- | :--- |
| **IDLE** | - | System is resting and waiting for a new goal in the `USER_QUEUE`. |
| **STRATEGY** | **Queen** | Combined Analysis & Planning. Assesses codebase and generates a technical task breakdown in one step. |
| **EXECUTING** | **Developer** | Actual implementation of code in `src/` and unit tests in `tests/`. |
| **LINTING** | **Pedant** | Automated quality gate. **1st:** Runs local "Dumb Pedant" (`ruff` autofix). **2nd:** If errors persist, escalates to AI Pedant. |
| **TESTING** | **Developer** | Execution of `pytest` to verify logical correctness. |
| **VERIFYING** | **Auditor** | Final security and quality audit. **1st:** Runs "Pre-flight Compression" to clean context. **2nd:** Invokes AI Auditor. |
| **VCS_DELIVERY** | **Router** | Executes Git operations (push, PR) and polls GitHub Actions status. |
| **BLOCKED** | - | **Stopped:** Task failed maximum retry attempts. Requires human operator intervention. |

### Emergency Protocol: **HALT**
This is not a state, but an **emergency brake**. It activates immediately upon detection of an API key leak (Security Guard) or a critical system error. A `HALT.flag` file is created, physically blocking any further execution until the operator clears the error via `make clean`.

---

## II. Bimetric Communication Protocol
The system communicates asynchronously via files in `agent_context/`. This is the foundation of the human-in-the-loop workflow.

### 1. Direction: User ➡️ AI (Commanding the Machine)
*   **Global Goals:** Add a new `- [ ] GOAL-XXX` to `agent_context/TASKS.md`.
*   **Contextual Instructions:** Write specific requirements into `agent_context/SESSION.md`.

### 2. Direction: AI ➡️ User (Feedback)
*   **Technical Progress:** Queen decomposes goals into technical steps in `TASKS.md`.
*   **Action Log:** A detailed log of agent activities is maintained in `SESSION.md`.
*   **Visual Logging:** The terminal displays emoji-coded status during pipeline execution.

---

## III. User Control Panel (Makefile Interface)
The `Makefile` serves as the primary dashboard for the operator:
*   **`make boot`**: Full initialization (syncs dependencies, validates system, indexes code).
*   **`make status`**: Status report (shows HALT status, current state, active tasks).
*   **`make pipeline`**: Starts the "engine". AI cycles through states until the goal is achieved.
*   **`make clean`**: **Smart Reset.** Clears agent logs and releases BLOCKED/HALT states while preserving user instructions.
*   **`make mock`**: Simulation mode. Runs the flow using mock responses to save API tokens.

---

## IV. Master Configuration (`agent_orchestrator.json`)
The command center of the orchestrator, managing high-level logic and resilience.

### 1. Global Workflow (`workflow_global`)
*   **`ci_mode`**: Switches between `local` and `github`.
*   **`loop_mode`**: If `true`, the orchestrator automatically processes the next task.
*   **`loop_delay_seconds`**: Anti-spam delay between LLM calls.
*   **`max_task_attempts`**: Master circuit breaker.

### 2. Local Stages (`workflow_local`)
*   **`active`**: Toggles the phase on/off.
*   **`max_retries`**: Number of attempts for a specific stage.
*   **`requires_llm`**: If `false`, the stage runs locally (e.g., LINTING) and uses a 0.1s adaptive delay.

### 3. API Resilience (`resilience`)
*   **`smart_fallback`**: Automatically switches providers (e.g., Groq to Mistral).
*   **`fallback_matrix`**: Defines the backup model and provider.

---

## V. Future Perspective: ACMI (Agent-CI Memory Intelligence)
The framework is prepared for a Phase 4 transition to a database-driven memory engine (SQLite):
1.  **AST Indexing:** Codebase will be indexed into a queryable database, allowing agents to retrieve specific function signatures instead of parsing large files.
2.  **Execution History:** Test results and agent decisions will be logged structurally, enabling the Auditor to make decisions based on data, not text logs.
3.  **System Reflection:** The orchestrator will learn from past failures by storing error patterns and successful solutions, which will be injected as "Memory Warnings" into future prompts.
```