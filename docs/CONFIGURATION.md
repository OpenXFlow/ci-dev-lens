
# ⚙️ Agent-CI-Lens: Configuration Guide (Model 5.3)

This document provides a detailed technical breakdown of the configuration files that govern the Agent-CI-Lens orchestrator.

---

## 1. `agent_orchestrator.json` (System Control)
Located in the project root, this file acts as the "Command Center." it defines how the pipeline behaves, handles errors, and manages memory.

### Workflow Global (`workflow_global`)
*   **`ci_mode`**: Sets the execution target. `local` for manual dev work; `github` for automated cloud integration.
*   **`loop_mode`**: When `true`, the orchestrator automatically starts the next goal in the `USER_QUEUE` upon success.
*   **`loop_delay_seconds`**: (Critical) The wait time between tasks. Set this to `15` or higher when using free tiers (e.g., Groq) to prevent **HTTP 429 Rate Limit** errors.
*   **`max_task_attempts`**: The master circuit breaker. If a task fails 3 times across all stages, it is marked as `[BLOCKED]`.

### Workflow Local (`workflow_local`)
Manages individual stages (`ANALYSE`, `PLANNING`, `EXECUTING`, `LINTING`, `TESTING`, `VERIFYING`).
*   **`active`**: Toggles the stage on or off.
*   **`max_retries`**: How many times an agent can attempt to fix its own errors within that specific stage.
*   **`pause_after`**: If `true`, the engine stops after this stage and waits for the operator to run `make flow` again.

### Resilience (`resilience`)
*   **`smart_fallback`**: When `true`, if a primary API provider (e.g., Groq) fails, the system automatically redirects the request to a backup provider defined in the matrix.
*   **`fallback_matrix`**: Defines the backup model for each provider. Example: If `GROQ` fails, the system switches to `MISTRAL` using the `mistral-large-latest` model.

### Memory Management (`memory_management`)
*   **`yellow_zone_threshold`**: (0.0 - 1.0) Percentage of context window usage that triggers the `context-compressor` to prune the `ACTION_LOG`.
*   **`red_zone_threshold`**: (0.0 - 1.0) Critical limit that triggers an emergency **HALT** to prevent data loss or model confusion.

---

## 2. `.agents/agent_registry.json` (Agent DNA)
This file is the "Registry" of all AI workers. It defines their "brains" and the tools they are allowed to use.

### Profile Settings
*   **`role`**: Descriptive name of the agent's purpose.
*   **`model`**: The specific LLM ID (e.g., `llama-3.3-70b-versatile` or `mistral-large-latest`).
*   **`provider`**: The identifier used to find API keys in `.env`. Thanks to our **Smart Parser**, you can add any provider (e.g., `OLLAMA`) here as long as `{PROVIDER}_API_KEY` exists in `.env`.
*   **`temperature`**: (0.0 - 2.0) Sets the creativity level. `0.0` is recommended for Pedant/Auditor for deterministic results.
*   **`max_tokens`**: The maximum response size allowed for the agent.
*   **`allowed_skills`**: A whitelist of capabilities (e.g., `testing-pro`, `quality-gate`) the agent is authorized to invoke.

---

## 3. `pyproject.toml` (Quality Gates & Standards)
This file configures the Python toolchain and defines the strictness of the "Quality Gates."

### Toolchain (`[project]` & `[dependency-groups]`)
*   The system uses **`uv`** exclusively.
*   **Dependencies**: Includes `pydantic` for schema validation and `requests` for API communication.
*   **Dev Groups**: Tools like `ruff`, `mypy`, and `pytest` are pinned here to ensure agents use the same versions as the operator.

### Ruff: Tier 1 Gate (Mechanical Integrity)
*   **`select`**: Enables specific rules. We use `ANN` (Type Hints), `D` (Docstrings), `S` (Security), and `TRY` (Exception handling).
*   **`convention = "google"`**: Forces agents to write documentation in the standard Google Style.
*   **`ignore`**: Strategically disables pedantic rules.
    *   `D100`, `D104`: Ignored to allow fast file creation without mandatory module-level headers.
    *   `D417`: Ignored to allow **One-line Docstrings** for simple methods.
*   **`per-file-ignores`**: Completely disables documentation requirements for the `tests/` and `agent_tests/` folders to prioritize execution speed over test verbosity.

### Mypy: Tier 2 Gate (Logical Integrity)
*   **`disallow_untyped_defs = true`**: Forces the Developer agent to provide Type Hints for every function.
*   **`strict_equality = true`**: Prevents logic bugs where different types are compared (e.g., `string == int`).

---


## 4. `.env` (Secrets & Environment Overrides)
Located in the project root, the `.env` file is strictly ignored by Git. It is the only place where private credentials and environment-specific toggles should reside.

### System Control (Simulation)
*   **`MOCK`**: (`true`/`false`) If set to `true`, the orchestrator will not call real LLM APIs. Instead, it will use predefined responses from `utils.py`. This is essential for testing framework logic without incurring costs.
*   **`GHA_MOCK_RESULT`**: (`success`/`failure`) Determines the outcome of simulated GitHub Actions during the `CLOUD_PUSH` stage.

### Dynamic API Credentials (The Smart Parser)
Model 5.3 uses a **Smart Parser** to load credentials. This allows you to add any LLM provider without modifying the Python source code.

*   **`{PROVIDER}_API_KEY`**: The API key for a specific service.
    *   *Example:* `GROQ_API_KEY`, `OPENAI_API_KEY`, `LOCAL_API_KEY`.
    *   The `{PROVIDER}` prefix must match the `provider` field in `agent_registry.json` (case-insensitive).
*   **`{PROVIDER}_BASE_URL`**: (Optional) The custom endpoint for the provider.
    *   Essential for local models (e.g., `OLLAMA_BASE_URL=http://localhost:11434/v1`).
    *   Used for regional endpoints or API proxies.

### Advanced Credential Features

#### 1. Key Rotation (High Availability)
The orchestrator supports **comma-separated keys** for any provider to prevent downtime due to rate limits.
*   *Example:* `GROQ_API_KEY=key_one,key_two,key_three`
*   If the first key returns an **HTTP 429 (Rate Limit)** or **401 (Unauthorized)** error, the system automatically rotates to the next key in the list.

#### 2. GitHub Integration
*   **`GITHUB_TOKEN`**: A Personal Access Token (PAT) required for the `git-manager` skill to push code and create Pull Requests when `ci_mode` is set to `github`.

---

## 💡 Configuration Summary Table

| File | Scope | Git Status | Format |
| :--- | :--- | :--- | :--- |
| `agent_orchestrator.json` | Pipeline & Logic | Tracked | Nested JSON |
| `agent_registry.json` | Agent Personas | Tracked | Structured JSON |
| `pyproject.toml` | Standards & Tools | Tracked | TOML |
| `.env` | Secrets & Mocking | **Ignored** | Key=Value |

**Pro-Tip for Developers:** 
If you add a new API provider (e.g., `DEEPSEEK`), simply add `DEEPSEEK_API_KEY=...` to your `.env` and set `"provider": "deepseek"` in the registry. The Pydantic `EnvConfig` model will automatically detect, validate, and inject the credentials into the `APIClient`.
