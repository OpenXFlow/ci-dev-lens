# 🧠 Agent Logic & Behavior

## 🔄 Current Execution Model: Sequential State Machine

Currently, **Agent-CI-Lens** operates as a **Strictly Sequential State Machine**. It does not support parallel agent execution in its current version (Model 6.0). 

### Why Serial Execution?
1. **Context Continuity:** By running agents in a serial "relay race" (STRATEGY → EXECUTING → LINTING → TESTING → VERIFYING), we ensure that each agent has access to the 100% accurate, up-to-date state of the previous step.
2. **Deterministic Feedback Loops:** If a failure occurs at any stage, the system can perform a clean rollback and retry without managing complex race conditions between multiple agents.
3. **Hypervisor Pattern:** The Router acts as a central authority, validating every move before the next stage begins.

### The Self-Correction Engine
* While the execution is serial, it is highly dynamic. The system uses structured feedback to "heal" itself

### Fix-logic-vs-test
* When a test fails, does the swarm fix the code or adjust the test?
* The short answer:** The system follows a **Code-First, Test-Validated** approach.

### The Decision Mechanism:
When a failure occurs in the `TESTING` stage, the Router (Hypervisor) triggers a **Rollback**. The decision on whether to fix the code or the test is handled by the **Developer Agent** in the subsequent `EXECUTING` attempt, but it is strictly governed by our architecture.

### Visualizing the Flow:
Refer to the **Diagram 3 (Autonomous Self-Correction Flow)** in [flow_diagrams_operations_map.md](../ci_architecture/flow_diagrams_operations_map.md).

1. **The Reversion:** If `pytest` returns `FAIL`, the Engine wipes the current success markers and routes the state back to `EXECUTING`.
2. **The Context:** The Developer receives the full error log from `SESSION.md`.
3. **The Strategy:**
   - **Default Behavior:** The prompt instructs the Developer to treat the **Requirement** (from `TASKS.md`) as the truth. Usually, this means the **code is fixed** to match the test.
   - **Test Adjustment:** If the Developer identifies that the code is correct but the test case itself is flawed (e.g., incorrect assertion), the agent is permitted to update the test.
4. **The Gatekeeper:** The final decision is audited by the **Auditor** in the `VERIFYING` stage. If the Auditor detects that the Developer "cheated" by weakening the test instead of fixing the bug, the task is rejected.

## 🚀 Looking for Parallelism ?

Check our [Strategic Roadmap](../faq/roadmap.md) to see how we plan to transition into a parallel Swarm architecture with Rust-based acceleration.
