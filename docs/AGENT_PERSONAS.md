
# 🤖 Agent-CI-Lens: Persona Guide (Model 5.3)

In Agent-CI-Lens, the "mind" of each agent is defined by a Markdown file in the `.agents/` directory. These files are **System Prompts**. They define the constraints, tools, and decision-making logic for each specialized role.

---

## 1. `queen.md` (The Architect)
The **Queen** is the strategist. She does not write application code; she analyzes requirements and breaks them down into technical sub-tasks.

### Use this persona when:
*   You want to change how goals are decomposed into tasks.
*   The AI is creating too many (or too few) tasks at once.
*   The planning logic lacks architectural depth.

### Example Improvements:
*   **Constraint:** *"Never plan more than 3 tasks per batch to ensure focus."*
*   **Logic:** *"Always prioritize database schema tasks before UI implementation."*

---

## 2. `developer.md` (The Implementer)
The **Developer** is the workhorse. This persona is responsible for writing the actual Python code in `src/` and the corresponding tests in `tests/`.

### Use this persona when:
*   The generated code is "lazy" (using snippets instead of full files).
*   You want to enforce specific coding patterns (e.g., specific Logging instead of print).
*   The agent is struggling with MyPy or Type Hints.

### Example Improvements:
*   **Constraint:** *"Always use the `logging` module for any diagnostic output; never use `print()`."*
*   **Style:** *"Enforce the use of Pydantic models for all data-transfer objects."*

---

## 3. `pedant.md` (The Cleaner)
The **Pedant** is the mechanical quality gate. This persona exclusively handles the `LINTING` state, focusing on Ruff formatting and import sorting.

### Use this persona when:
*   The linter is stuck in a loop and the Pedant doesn't know how to fix a recurring error.
*   You want the Pedant to be more aggressive in using the `autofix` skill.

### Example Improvements:
*   **Instruction:** *"If Ruff fails on rule I001, prioritize the `autofix` skill immediately."*
*   **Constraint:** *"Do not attempt to fix logic errors; focus strictly on syntax and formatting."*

---

## 4. `auditor.md` (The Gatekeeper)
The **Auditor** is the final defense. This persona runs security scans and performs a final sanity check on the code and tests before the goal is marked complete.

### Use this persona when:
*   You want to add new security checklists (e.g., checking for specific hardcoded strings).
*   The agent is approving code that contains `TODO` comments or debug junk.
*   You want to refine the Git Commit Message generation logic.

### Example Improvements:
*   **Checklist:** *"Reject any code that contains the word 'FIXME' or 'DEBUG_ONLY'."*
*   **Verification:** *"Ensure that every new function has a 100% test coverage report in the log before approval."*

---

## ⚙️ How to Update Personas (Operator Strategy)

When you modify these files, you are performing "Behavioral Engineering." 

| Scenario | Recommendation |
| :--- | :--- |
| **Agents are getting stuck in loops** | Update the specific agent's `<constraints>` block with a "Stop Condition." |
| **Code quality is dropping** | Add a new requirement to the `Developer`'s `<workflow>` or the `Auditor`'s `<checklist>`. |
| **Planning is too complex** | Refine the `Queen`'s `<execution_rules>`. |

### The "Surgical Fix" Rule
When updating personas, try to add **Constraints** rather than long descriptions. AI models respond better to negative constraints (*"Never do X"*) and explicit formatting rules (*"Always output Y in format Z"*).

**Note:** After modifying any `.md` file in the `.agents/` folder, it is recommended to run `make reset` to ensure the next session starts with the updated persona context.