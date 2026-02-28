
# 🛠️ Agent-CI-Lens User Guide: Terminal & Environment

## 1. Terminal Commands (Makefile Interface)

The `Makefile` serves as your primary control panel. Each command is designed to maintain the strict boundary between the human operator and the autonomous agents.

### Core Orchestration

*   **`make wake`** (Full Initialization)
    *   **What happens:** 
        1. Checks for `.env`. if missing, creates it from `.env.example`.
        2. Executes `uv sync --all-groups` to install all dependencies in the virtual environment.
        3. Automatically runs `make guard` and `make scan`.
    *   **Environment Impact:** Sets up a "clean slate." This is the first command you should run in a new container.

*   **`make flow`** (Start Autonomous Engine)
    *   **What happens:** Launches the main Python process (`agent_core/router.py`) in pipeline mode.
    *   **Logic:** The Router reads requirements from `TASKS.md` and cycles through agent states (Queen -> Developer -> Pedant -> Auditor).
    *   **Environment Impact:** Consumes real API credits. Physically creates or modifies files in `src/` and `tests/`.

*   **`make sim`** (Simulation Mode)
    *   **What happens:** Same as `flow`, but with the `--mock` flag enabled.
    *   **Logic:** The Router instructs the API Client to return predefined mock responses instead of calling LLM providers. Skills return success results without actual execution.
    *   **Environment Impact:** Safe for testing orchestrator logic without spending tokens or risking production code.

*   **`make info`** (Diagnostics)
    *   **What happens:** 
        1. Checks for the existence of `HALT.flag` in the cache. If found, it displays the reason for the emergency stop.
        2. Reads `agent_context/SESSION.md` and prints the current system state (e.g., `IDLE`, `EXECUTING`, `BLOCKED`).
    *   **Environment Impact:** Read-only. Provides a quick health check of the system.

*   **`make reset`** (Smart Reset)
    *   **What happens:** 
        1. Deletes the `HALT.flag` (releasing the emergency brake).
        2. Uses `sed` to prune `SESSION.md`. It **preserves** your `[USER_SECTION]` instructions but **wipes** everything in the `[AGENT_SECTION]` (activity logs and state history).
        3. Reverts the system state to `IDLE`.
    *   **Environment Impact:** Returns the orchestrator to its starting point without "forgetting" human instructions.

### Quality & Testing

*   **`make review`** (Static Analysis)
    *   **What happens:** Runs `ruff check`, `ruff format --check`, and `mypy` on the `src/` directory.
    *   **Environment Impact:** Read-only. Lists all violations of coding and typing standards.

*   **`make fix`** (Automatic Correction)
    *   **What happens:** Executes `ruff check --fix` and `ruff format`.
    *   **Environment Impact:** Actively modifies code in `src/` (e.g., fixing imports, adjusting indentation, removing unused variables).

*   **`make verify`** (Application Testing)
    *   **What happens:** Runs `pytest` on the `tests/` directory.
    *   **Environment Impact:** Verifies the functional logic of the target application (e.g., the calculator).

*   **`make self`** (Kernel Testing)
    *   **What happens:** Runs `pytest` on the `agent_tests/` directory.
    *   **Environment Impact:** Verifies the "brain" of the framework (XML parsing, validation logic, etc.).

*   **`make guard`** (Integrity Check)
    *   **What happens:** Executes `agent_core/validator.py`.
    *   **Logic:** Ensures API keys are present in `.env`, config paths are correct, and all mandatory Model 5.3 directories exist.
    *   **Environment Impact:** Prevents the pipeline from starting in a broken environment.

### Maintenance

*   **`make scan`** (Update Map)
    *   **What happens:** Runs `agent_core/indexer.py`.
    *   **Logic:** Scans all `.py` files in `src/` using AST (Abstract Syntax Tree) and generates an updated codebase map in `.claude/cache/AGENTS.md`.
    *   **Environment Impact:** Updates the "vision" of the AI agents.

*   **`make purge`** (Deep Clean)
    *   **What happens:** Finds and removes all temporary directories: `__pycache__`, `.pytest_cache`, and `.mypy_cache`.
    *   **Environment Impact:** Reclaims space and ensures old cached bytecode does not interfere with new tests.


## 2. Docker & Dev Container: Understanding the Environment

Agent-CI-Lens is designed specifically for **Unix-like environments** (Linux and macOS). 

### Why the Linux/Unix Requirement?
The "glue" that holds this system together relies on standard Unix utilities:
*   **Makefile Syntax:** Commands like `rm -rf`, `sed`, `grep`, and `find` have specific syntax requirements met by Linux/macOS. Standard Windows CMD will fail these commands.
*   **Shell Scripts:** Agent skills located in `.claude/skills/` are written in **Bash**.
*   **uv Toolchain:** While the package manager is cross-platform, the Makefile invokes it in a Linux-standard way.

### Supported Execution Environments

#### **A. Dev Container (Recommended for Windows/macOS/Linux)**
*   Your current setup. Even on Windows, VS Code "enters" a Linux container via Docker.
*   **Benefit:** 100% reproducible environment. Everything is guaranteed to work.

#### **B. Native Linux (Ubuntu, Debian, etc.)**
*   Runs directly in the terminal without Docker. Requires `uv`, `make`, and `git` installed natively.

#### **C. macOS**
*   Runs natively in the terminal (Zsh/Bash). macOS includes all necessary tools (`make`, `sed`, `grep`) out of the box.

#### **D. Windows + WSL2 (Windows Subsystem for Linux)**
*   The best alternative to Docker on Windows. By installing a distribution like Ubuntu from the Microsoft Store, the project runs identically to a native Linux system.

#### **E. Native Windows (PowerShell / CMD)**
*   **Unsupported.** 
*   PowerShell does not recognize the `Makefile` syntax (e.g., the `sed` file-pruning in `make reset`).
*   Bash skills (`.sh`) would require a complete rewrite into PowerShell (`.ps1`).

### Summary
The core logic is **OS-agnostic in Python** (Python code runs anywhere), but the automation layer is **OS-dependent** (Makefile and Bash). On Windows, you must use **Docker + Dev Container** or **WSL2** for a successful deployment.