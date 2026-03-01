# 🏛️ ARCHITECTURE.md

```markdown
# 🏛️ Agent-CI-Lens — Codebase Map (Model 5.3)

This map describes the architecture, logical layers, and operational protocols of the Agent-CI-Lens orchestrator.

```text
agent-ci-lens/
├── .agents/               # [PROFILES] AI behavior and persona definitions
│   ├── agents.json        # Profile registry (models, providers, allowed skills)
│   ├── auditor.md         # Persona: Security & Quality Gatekeeper
│   ├── developer.md       # Persona: Senior Python Engineer (Implementer)
│   ├── pedant.md          # Persona: Code Cleaner and Linter
│   └── queen.md           # Persona: Lead Architect & Strategic Planner
│
├── .claude/               # [SYSTEM] Hidden system configuration and machine cache
│   ├── cache/             # Machine-readable state (AGENTS.md, HALT.flag)
│   ├── rules/             # Engineering Iron Laws and Python coding standards
│   │ 
│   └── skills                      # [TOOLS] Atomic capabilities available to agents
│       ├── cascade-logic           # [CONTROL] Advanced task chaining and swarm orchestration
│       │   └── SKILL.md            # Execution rules for multi-agent planning
│       ├── context-compressor      # [OPTIMIZATION] ACTION_LOG pruning to save tokens
│       │   ├── references          # Intel for classification
│       │   │   └── memory-map.md   # Fact vs. Noise classification dictionary
│       │   ├── scripts             # Execution logic
│       │   │   └── summarize.py    # Python script for ACTION_LOG pruning
│       │   └── SKILL.md            # Token threshold triggers for compression
│       ├── func-audit              # [QA] Business logic verification methodology
│       │   └── SKILL.md            # Methodology for manual and automated logic review
│       ├── git-manager             # [VCS] Branch lifecycle and cloud integration
│       │   ├── references          # Standards for repository
│       │   │   └── branch-naming.md# Strict VCS naming conventions
│       │   ├── scripts             # Bash execution scripts
│       │   │   ├── gha_status.sh   # GitHub Actions result polling
│       │   │   ├── pr_create.sh    # Automated PR creation script
│       │   │   └── push.sh         # Safe code pushing wrapper
│       │   └── SKILL.md            # Branch lifecycle and cloud push policies
│       ├── handoff-manager         # [PERSISTENCE] State preservation between sessions
│       │   ├── assets              # Data templates
│       │   │   └── template.md     # Standardized schema for handoff files
│       │   ├── scripts             # Export logic
│       │   │   └── dump_state.py   # State preservation exporter
│       │   └── SKILL.md            # Cross-session continuity protocols
│       ├── mcp-bridge              # [INTEGRATION] External tool proxy (Slack, Jira)
│       │   ├── references          # Tool definitions
│       │   │   └── tools.md        # Catalog of external tool schemas
│       │   ├── scripts             # Proxy implementation
│       │   │   └── proxy.py        # Phase 1 protocol simulation
│       │   └── SKILL.md            # Multi-tool interaction standards
│       ├── quality-gate            # [LINTING] Static code analysis and formatting
│       │   ├── references          # Known solutions
│       │   │   └── errors.md       # Knowledge base for Ruff/Mypy resolutions
│       │   ├── scripts             # Linter wrappers
│       │   │   ├── autofix.sh      # Automated linting correction (Ruff)
│       │   │   └── check.sh        # Primary Quality Gate execution
│       │   └── SKILL.md            # Zero-Tolerance code quality enforcement
│       ├── security-guard          # [SECURITY] Secret and vulnerability scanning
│       │   ├── references          # Patterns for detection
│       │   │   └── patterns.md     # Regex database for secrets and unsafe code
│       │   ├── scripts             # Scanning logic
│       │   │   └── scan.py         # Pre-commit security scanner (Triggers HALT)
│       │   └── SKILL.md            # Mandatory security audit protocols
│       └── testing-pro             # [TESTING] Pytest execution and TDD enforcement
│           ├── references          # Test aids
│           │   ├── errors.md       # Guide for resolving Pytest failures
│           │   └── patterns.md     # Best practices for mocking DB/API
│           ├── scripts             # Execution wrappers
│           │   ├── coverage.py     # Code coverage measurement tool
│           │   └── verify.py       # Pytest result formatting engine
│           └── SKILL.md            # Test-Driven Development (TDD) cycle rules
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
│   │   ├── engine.py      # Main State Machine and Stage execution logic
│   │   ├── llm.py         # Agnostic API Client & Prompt construction
│   │   ├── managers.py    # File system handlers for context and tasks
│   │   └── utils.py       # Shared constants, logging, and environment loaders
│   ├── indexer.py         # Generates codebase map (AGENTS.md) for agents
│   ├── router.py          # CLI entry point for human/machine interaction
│   └── validator.py       # Shield: Integrity check of secrets and structure
│
├── agent_native/          # [PERFORMANCE] Rust-based optimizations (Phase 2)
│   └── info.md            # Implementation roadmap for native workers
│
├── agent_tests/           # [SYSTEM QA] Framework-level unit tests (Kernel)
│   ├── conftest.py        # Shared fixtures with Model 5.2 path injection
│   ├── test_indexer.py    # Verification of codebase mapping logic
│   ├── test_router.py     # Verification of State Machine and API routing
│   ├── test_skills.py     # Verification of internal skill execution
│   └── test_validator.py  # Verification of system integrity checks
│
├── src/                   # [APP] Target application source code (AI Playground)
│   └── __init__.py        # Makes src a valid Python package
│
├── tests/                 # [APP QA] Unit tests for the target application
│   └── __init__.py        # Makes tests a valid Python package
│
├── .env                   # [SECRETS] API keys (rotation support) and endpoints
├── .gitignore             # Git exclusion rules (venv, cache, local sessions)
├── agent_config.json      # [CONFIG] Master settings and API Fallback Matrix
├── CLAUDE.md              # AI Onboarding: Absolute rules and Startup protocols
├── Makefile               # [CONTROL PANEL] Main interface for humans and GHA
├── pyproject.toml         # Python toolchain and dependency management
└── uv.lock                # Deterministic dependency lockfile
```

## I. System States (State Machine)
The system is a managed process, not a random chat. Every state has a strictly defined responsibility and an assigned agent profile.

| State | Agent | Responsibility |
| :--- | :--- | :--- |
| **IDLE** | - | System is resting and waiting for a new goal in the `USER_QUEUE`. |
| **ANALYSE** | **Queen** | Codebase diagnostics. Queen identifies missing components and implementation requirements. |
| **PLANNING** | **Queen** | Decomposition of the goal into atomic technical tasks in `agent_context/TASKS.md`. |
| **EXECUTING** | **Developer** | Actual implementation of code in `src/` and unit tests in `tests/`. |
| **LINTING** | **Pedant** | Automated PEP8 (Ruff) and Type Hint (Mypy) validation. |
| **TESTING** | **Developer** | Execution of `pytest` to verify logical correctness. |
| **VERIFYING** | **Auditor** | Final security and quality audit before "handing over" the work. |
| **CLOUD_PUSH** | **Git-Mgr** | (Optional in CI_MODE=github) Pushes code to origin and creates a Pull Request. |
| **BLOCKED** | - | **Stopped:** Task failed 3 consecutive times. Requires human operator intervention. |

### Emergency Protocol: **HALT**
This is not a state, but an **emergency brake**. It activates immediately upon detection of an API key leak (Security Guard) or a critical system error. A `HALT.flag` file is created, physically blocking any further execution until the operator clears the error via `make reset`.

---

## II. Bimetric Communication Protocol
The system communicates asynchronously via files in `agent_context/`. This is the foundation of the human-in-the-loop workflow.

### 1. Direction: User ➡️ AI (Commanding the Machine)
Operator instructions are written directly into files, not the chat:
*   **Global Goals:** Add a new `- [ ] GOAL-XXX` to `agent_context/TASKS.md` under the `## [USER_QUEUE]` header.
*   **Contextual Instructions:** Write specific requirements (e.g., *"Use the Pandas library"* or *"Fix this specific bug"*) into `agent_context/SESSION.md` under `## [USER_SECTION]`.

### 2. Direction: AI ➡️ User (Feedback)
The system responds in three ways:
*   **Technical Progress:** Queen decomposes goals into technical steps in `TASKS.md` under `## [AGENT_PROGRESS]`.
*   **Action Log:** A detailed log of agent activities (e.g., *"Skill testing-pro -> RESULT:PASS"*) is maintained in `SESSION.md` under `## [AGENT_SECTION]`.
*   **Visual Logging:** The terminal displays emoji-coded status during `make flow`:
    *   🚀 **PIPELINE:** Phase start.
    *   🔄 **STATE:** State transition.
    *   ✅ **OK:** File successfully written or test passed.
    *   ⚠️ **WARN:** Retrying or API rate limit reached.
    *   ❌ **ERROR:** State failure or critical error.

---

## III. User Control Panel (Makefile Interface)
The `Makefile` serves as the primary dashboard for the operator:
*   **`make wake`**: Initialization. Sets up the environment and synchronizes dependencies.
*   **`make info`**: Status report. Shows the current session state and pending tasks.
*   **`make flow`**: Starts the "engine". AI cycles through states until the goal is achieved.
*   **`make reset`**: **Smart Reset.** Clears agent logs and releases BLOCKED/HALT states while preserving user instructions.
*   **`make sim`**: Simulation mode. Runs the flow using mock responses to save API tokens.

---

## IV. RAG Mechanism (Troubleshooting)
If the system encounters a known error, it consults `agent_context/TROUBLESHOOTING.md`. The operator can add records in the format `### @Error -> Solution`, which the Router injects as a "hint" to the Developer during the next attempt, closing the system's learning loop.

---

## V. Master Configuration (`agent_orchestrator.json`)
The command center of the orchestrator, managing high-level logic and resilience.

### 1. Global Workflow (`workflow_global`)
*   **`ci_mode`**: Switches between `local` (development) and `github` (automated cloud verification).
*   **`loop_mode`**: If `true`, the orchestrator automatically processes the next task in the queue.
*   **`loop_delay_seconds`**: Anti-spam delay to prevent API Rate Limits (429 errors).
*   **`max_task_attempts`**: Master circuit breaker. Blocks tasks after repeated failures.

### 2. Local Stages (`workflow_local`)
Allows fine-tuning of each phase (`ANALYSE`, `PLANNING`, etc.):
*   **`active`**: Toggles the phase on/off.
*   **`max_retries`**: Number of attempts the agent has to fix errors within that specific stage.
*   **`pause_after`**: Pauses the pipeline after a stage for manual review.

### 3. API Resilience (`resilience`)
*   **`smart_fallback`**: Automatically switches providers (e.g., Groq to Mistral) upon primary API failure.
*   **`fallback_matrix`**: Defines the backup model and provider for each primary source.

---

## VI. Future Perspective: Rust Integration (`agent_native`)
The framework is prepared for a Phase 2 transition to a hybrid execution engine:
1.  **Native Acceleration:** Rewriting the Worker agent in Rust to reduce RAM footprint from ~150MB to <5MB.
2.  **Lightning Fast Indexing:** Utilizing `tree-sitter` in Rust for sub-millisecond codebase mapping.
3.  **Security Sandbox:** Low-level execution wrapping using Linux namespaces to strictly isolate generated code.
4.  **Binary Integrity:** Replacing Python script logic with static binaries for 100% deterministic CI/CD environments.
```