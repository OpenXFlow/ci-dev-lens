This document defines the strict formatting requirements for the orchestrator's context files. 
Since the **Model 5.3** core uses Regex-based parsing to populate Pydantic models, any deviation from these rules will lead to parsing failures or state corruption.

---

# 📜 TASK_SESSION_format_rules.md

## 1. General Principles
*   **Case Sensitivity:** All section headers must be in **UPPERCASE**.
*   **Bracket Integrity:** Headers must be wrapped in `[` square brackets `]`.
*   **Whitespace:** One empty line is mandatory between a header and its content.

---

## 2. SESSION.md Structure
The `SessionManager` relies on specific Level 2 (`##`) and Level 3 (`###`) headers.

### A. Section Hierarchy
1.  **Level 2 Headers:** Used to define the Bimetric zones.
    *   `## [USER_SECTION]`
    *   `## [AGENT_SECTION]`
2.  **Level 3 Headers:** Used to define the state attributes.
    *   `### [CONTEXT]`
    *   `### [WORKSPACE]`
    *   `### [STATE]`
    *   `### [ACTION_LOG]`

### B. Spacing Rules
*   **Correct:**
    ```markdown
    ### [STATE]
    IDLE
    ```
*   **Incorrect (Parser will fail):**
    ```markdown
    ### [STATE] IDLE
    ```

---

## 3. TASKS.md Structure
The `TasksManager` uses strict patterns to track the progress of the State Machine.

### A. Task Naming Convention
Every task in the `[AGENT_PROGRESS]` section must follow this exact regex pattern:
`- [ ] TASK-XXX: <Description> [attempts: N]`

*   **TASK-XXX:** Must be a three-digit identifier (e.g., `TASK-001`).
*   **Description:** A single-line summary of the technical unit.
*   **[attempts: N]:** Mandatory suffix used by the `HaltManager` to prevent infinite loops.

### B. Flat Structure Requirement
While `[USER_QUEUE]` (Goals) can have nested bullet points for requirements, the `[AGENT_PROGRESS]` (Tasks) section **must be a flat list**. The parser does not support nested sub-tasks in the execution phase.

---

## 4. Forbidden Modifications
*   **Do not remove the horizontal separator (`---`):** It is used as a logical boundary between User and Agent territories.
*   **No Markdown Blocks inside tags:** Never wrap file content in ` ```python ` blocks when using `<file_write>` tags.
*   **W292 Compliance:** Every file must end with exactly one empty newline to satisfy the Ruff linter.

---

## 5. Failure Result
If these rules are violated, the Router will trigger a `POLICY_VIOLATION` or a `HISTORY_VIOLATION`, forcing an immediate **HALT** to protect the project integrity.