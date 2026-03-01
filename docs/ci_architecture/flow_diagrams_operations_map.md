This document serves as the visual architectural map for **Agent-CI-Lens (Model 5.3)**. Using Mermaid diagrams, it explains how the orchestrator (Router) manages the information flow, system state transitions, and autonomous error correction.

---

# 🗺️ Architectural Flow & Operations Map

## 1. Primary System Lifecycle (State Machine)
This diagram illustrates the path from the user defining a Goal to its autonomous completion and auto-closure.

```mermaid
stateDiagram-v2
    [*] --> IDLE: make pipeline
    IDLE --> ANALYSE: GOAL found in USER_QUEUE
    ANALYSE --> PLANNING: Requirements assessed
    PLANNING --> EXECUTING: Technical tasks created
    
    state EXECUTING_LOOP {
        direction TB
        EXECUTING --> LINTING: Code & Tests written
        LINTING --> TESTING: Quality Gate PASS
        TESTING --> VERIFYING: Logic PASS
        
        LINTING --> EXECUTING: RUFF/MYPY FAIL (Fix needed)
        TESTING --> EXECUTING: Pytest FAIL (Bugfixing)
    }
    
    VERIFYING --> IDLE: TASK finished & Goal still open
    VERIFYING --> AUTO_CLOSE: All tasks [x] for current Goal
    AUTO_CLOSE --> IDLE: GOAL marked [x]
    
    EXECUTING_LOOP --> BLOCKED: attempts >= 3
    BLOCKED --> [*]: Manual intervention required
```

---

## 2. Bimetric Communication (Data Flow)
The Router acts as a "Hypervisor," isolating the User from the AI Agents. Agents never interact with raw files directly; they only see the context prepared by the Router.

```mermaid
flowchart LR
    subgraph UserZone [USER SECTION - Read Only for AI]
        U1[CONTEXT]
        U2[WORKSPACE]
    end

    subgraph AgentZone [AGENT SECTION - Write Area]
        A1[STATE]
        A2[FEEDBACK]
        A3[ACTION_LOG]
    end

    Operator((Human Operator)) -->|make pipeline| Router{ROUTER}
    Operator -->|Goal Definition| U1
    
    Router -->|1. Parse| UserZone
    Router -->|2. Parse| AgentZone
    Router -->|3. Build Prompt| LLM((AI Agent))
    
    LLM -->|4. XML Response| Router
    Router -->|5. Update State| AgentZone
    Router -->|6. Write Source| Src[(Source Code / Tests)]
    Router -->|7. Log Errors| A2
```

---

## 3. Autonomous Self-Correction Flow
This diagram details the internal logic when a Developer makes a coding error that is caught by the Linter (Pedant) or the Test Suite (Pytest).

```mermaid
flowchart TD
    Start(State: EXECUTING) --> Dev[Developer generates Code/Tests]
    Dev --> Router{Router Validation}
    
    Router -->|Success| Lint[State: LINTING]
    Router -->|No file write| Rej[POLICY_VIOLATION] --> Start
    
    Lint --> Pedant[Pedant: ruff check]
    Pedant -->|Fail| Fix[autofix.sh]
    Fix -->|Success| Test[State: TESTING]
    Fix -->|Permanent Fail| BackToDev[Route back to EXECUTING] --> Start
    
    Test --> Pytest[Developer: pytest verify]
    Pytest -->|PASS| Audit[State: VERIFYING]
    Pytest -->|FAIL| LogErr[Write error to FEEDBACK] --> Start
    
    Audit --> Auditor[Auditor: Final Check]
    Auditor -->|Approved| Success([TASK COMPLETED])
```

---

## 4. Agent Responsibility & Skill Matrix
A mapping of which agent controls which tools (Skills) and which parts of the system they are permitted to modify.

```mermaid
flowchart TB
    subgraph Queen [Architect / Planning]
        Q1[Analyze USER_QUEUE]
        Q2[Update AGENT_PROGRESS]
        Q3[Skill: context-compressor]
    end

    subgraph Developer [Engineer / Implementation]
        D1[Write src/ and tests/]
        D2[Skill: testing-pro]
        D3[Logic Bugfixing]
    end

    subgraph Pedant [Linter / Clean Code]
        P1[Ruff / Mypy enforcement]
        P2[Skill: quality-gate]
        P3[Import & Format cleanup]
    end

    subgraph Auditor [QA / Security Guard]
        A1[Skill: security-guard]
        A2[Final Code Verification]
        A3[Trigger HALT on Secrets]
    end
```

---

## 5. Diagram Legend

| Symbol | Meaning |
| :--- | :--- |
| **Rectangular Block** | An Action or a State (e.g., PLANNING). |
| **Diamond Shape** | Decision Point (e.g., Did tests pass?). |
| **Layered Block** | Sub-process or internal loop (e.g., Execution cycle). |
| **Dashed Line** | Feedback loop triggered by an error. |
| **Green Icon/Border** | Successful completion (Success). |
| **Red Icon/Border** | Failure or System Lock (Blocked/Halt). |

---

### How to use these diagrams during development:
1.  **Modifying `engine.py`:** Refer to **Diagram 1** to see where to insert new states or transition logic.
2.  **Modifying `managers.py`:** Refer to **Diagram 2** to ensure bimetric separation (User vs. Agent) is maintained.
3.  **Debugging Pipeline Failures:** Refer to **Diagram 3** to understand why the system might be "reverting" to a previous state during a run.