# ⚙️ Agent-CI-Lens: Configuration Guide (Model 6.1)

This document provides a detailed technical breakdown of the configuration files governing the Agent-CI-Lens orchestrator.

---

## 1. `agent_orchestrator.json` (System Control)
The "Command Center" managing pipeline behavior, resilience, and memory.

### Workflow Local (`workflow_local`)
Governs individual stage execution.
*   **`requires_llm`**: (Critical for Engine v2.0)
    *   `true`: Stage invokes an LLM agent (e.g., `STRATEGY`, `EXECUTING`). Enforces full cooldown delay.
    *   `false`: Stage runs as a pure local subprocess (e.g., `TESTING`). Bypasses LLM tokens and uses 0.1s adaptive delay.
*   **`max_retries`**: Number of self-correction attempts per stage. `LINTING` is typically set higher (5) to allow for iterative formatting.

### Memory Engine (`memory_engine`)
*   **`enabled`**: Toggle for the SQLite-based ACMI system.
*   **`max_execution_logs`**: (New) Defines the retention policy for the `execution_logs` table (default: 2000). Older records are auto-pruned during `make purge`.
*   **`max_reflections`**: Limit for AI-learned lessons in the database.

### Resilience (`resilience`)
*   **`smart_fallback`**: Automated provider switching (e.g., Groq -> Mistral) upon 429 Rate Limits.
*   **`fallback_matrix`**: Map of primary providers to their respective backup models and providers.

---

## 2. `.agents/agent_registry.json` (Agent DNA)
Defines the specialized profiles for AI workers.

*   **`architect`**: Specialized in goal refinement (INTENT/CONSTRAINTS/METRIC).
*   **`queen`**: Orchestrator for Atomic Task decomposition.
*   **`developer`**: The primary implementer (Python/Pytest).
*   **`auditor`**: Security and quality gatekeeper.
*   **`pedant`**: Formatting and Linter specialist.

**New in 6.1:** Usage of `max_tokens=500` for the Auditor is recommended to optimize speed and cost for binary (PASS/FAIL) decisions.

---

## 3. `agent_core/router_core/models.py` (Validation Layer)
Model 6.1 hardens the data layer using Pydantic V2.

### `ExecutionLogEntry` (Telemetry Model)
Every agent call is validated against this schema before DB insertion:
*   **`provider`**: Stores the LLM provider (e.g., `groq`, `mistral`, `local_skill`).
*   **`tokens_prompt` / `tokens_completion`**: Granular tracking of input vs. output.
*   **`tokens_used`**: Total consumption for ROI calculation.
*   **`duration_ms`**: Latency tracking for performance audits.

---

## 4. `.env` (Secrets & Dynamic Provisioning)
The orchestrator uses a **Smart Parser** for environment variables.

### Key Rotation & Fallbacks
*   **Multi-Key Support:** `GROQ_API_KEY=key1,key2` enables automatic rotation if `key1` hits a rate limit.
*   **Custom Base URLs:** `{PROVIDER}_BASE_URL` allows integration with local models (Ollama) or API proxies, maintaining OpenAI compatibility.

### Telemetry Support
The `APIClient` in `llm.py` now includes a cross-provider usage parser. It automatically detects and maps token metadata from:
1.  **OpenAI-compatible** (Groq, Mistral, Ollama)
2.  **Anthropic** (input/output tokens mapping)
3.  **Google Gemini** (usageMetadata mapping)

---

## 5. ACMI Database (Persistent Rules)
While not a config file, the `memory.db` file contains the **Mandatory Ruleset**.

*   **`is_mandatory=1`**: Rules with this flag are injected into the prompt regardless of the FTS5 search rank.
*   **Use Case:** Use this for "Iron Laws" that must never be forgotten (e.g., *Rule 93: Never write to SESSION.md*).
