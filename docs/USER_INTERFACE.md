# 🖥️ Agent-CI-Lens: User Interface Guide (Model 6.0)

In Agent-CI-Lens, the "User Interface" is not a graphical window, but a set of structured Markdown files located in the `agent_context/` directory. These files govern the communication, memory, and task execution of the autonomous agents.

---

## 1. `MEMORY.md` (Long-Term Project Context)
This file serves as the "Knowledge Base" for the project. It provides the AI agents with high-level information that does not change frequently.

### Purpose:
- To define the technology stack (e.g., Python 3.12, Pytest, FastAPI).
- To store permanent architectural decisions.
- To provide historical context that agents must respect across multiple sessions.

### Operator Strategy:
When starting a new project or shifting a major architectural direction, update this file. It prevents the agents from asking basic questions or choosing incorrect libraries.

---

## 2. `SESSION.md` (Active Work-Session & Communication)
This is the most dynamic file in the system. It implements **Bimetric Isolation** to protect human instructions from being overwritten by AI.

### The Bimetric Split:
1. **`[USER_SECTION]`**: The "Command Deck". This section is Read-Only for agents. It contains instructions from you (the operator).
2. **`[AGENT_SECTION]`**: The "Engine Room". This is where the Router records the system state and logs.

### Components:
- **`[CONTEXT]`**: Where you provide specific, immediate instructions (e.g., *"Focus on performance optimization"*).
- **`[WORKSPACE]`**: A listing of files currently relevant to the task.
- **`[STATE]`**: Shows the current state of the machine (IDLE, STRATEGY, EXECUTING, etc.).
- **`[FEEDBACK]`**: A dedicated channel for the system to report errors. By separating errors from `[CONTEXT]`, we ensure the AI never confuses a bug report with a human instruction.
- **`[ACTION_LOG]`**: A chronological record of every skill used and every agent response.

---

## 3. `TASKS.md` (Goal Tracking & Decomposition)
This file is the "Engine's Blueprint". It manages the transformation of high-level human goals into low-level technical steps.

### The Hierarchical Structure:
1. **`## [USER_QUEUE]`**: The list of human-defined objectives (**GOAL-XXX**).
2. **`## [AGENT_PROGRESS]`**: The technical decomposition created by the **Queen** agent (**TASK-XXX**).

### Execution Logic:
- **GOAL**: A high-level requirement (e.g., *"Implement authentication"*).
- **TASK**: An atomic, verifiable unit of work (e.g., *"Create src/auth.py and tests/test_auth.py"*).
- **STRATEGY Phase**: In Model 6.0, the Queen agent performs analysis and planning in a single `STRATEGY` phase (Chain of Thought), generating the entire task list at once for efficiency.
- **Attempts**: Tracks how many times a task has been attempted. After 3 failed attempts, the task is marked as `[BLOCKED]`.

### Rule:
Always maintain **Flat Syntax**. Never use nested bullet points, as the Router uses regex to parse these lines precisely.

---

## 4. `TROUBLESHOOTING.md` (Closed-Loop Learning / RAG)
This file acts as the system's "Self-Correction Memory". It implements a simple but powerful RAG (Retrieval Augmented Generation) mechanism.

### The `### @` Mechanism:
When a task fails, the Router scans the error log for keywords. It then looks into `TROUBLESHOOTING.md` for matching headers.

### Entry Format:
```markdown
### @ErrorKeyword
**Cause:** Description of why this happens.
**Solution:** Step-by-step fix that the agent must follow.
```

### Why it works:
If an agent makes a mistake (e.g., a specific Mypy error), and you record the solution here, the Router will automatically feed that solution to the agent on its next attempt. This prevents the system from repeating the same mistakes.

---

## 💡 Operator Best Practices

| Action | Correct File |
| :--- | :--- |
| **I want to change the app's database** | Update `MEMORY.md` |
| **I want to give a hint for a specific error** | Update `TROUBLESHOOTING.md` |
| **I want to define a new feature request** | Add to `TASKS.md` |
| **I want to tell the agent it's being lazy** | Update `SESSION.md` `[CONTEXT]` |

**Crucial Note:** Never delete the `---` or the section headers in these files. The orchestrator's regular expressions depend on this exact structure to navigate the project's state.
