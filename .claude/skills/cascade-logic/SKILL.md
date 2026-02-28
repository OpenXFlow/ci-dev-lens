# Cascade-Logic Skill (MOCK - MVP Phase)

## Purpose
This skill is deactivated in Phase 1 (MVP). It is intended for advanced task chaining and sub-agent management.

## Agent Instruction (Queen)
If you are in the PLANNING state, you do not need to call this skill. 
Write your tasks directly into `agent_context/TASKS.md` without complex process chaining.


## Roadmap & Future Triggers
Implementation of the full Cascade-Logic Skill is scheduled for **Phase 3: Scalability & Parallelism**. 

Currently, in Phases 1 and 2, the workflow remains linear: Queen plans, Developer codes, Auditor verifies. You should consider transitioning from MOCK to a real implementation when the following triggers occur:

1. **Queen hits the 5step limit:** 
   When user requirements become too complex for a single 5-step batch, Cascade-Logic will allow the Queen to manage a "Master Plan" and distribute sub-tasks iteratively.

2. **Parallel Development (Git Worktrees):** 
   When the framework evolves into a "Swarm" model, this skill will act as a traffic controller, managing dependencies between multiple Developers working in parallel branches.

3. **Transition to Rust Optimization (`agent_native/`):** 
   When performance-critical parts of the orchestrator are rewritten in Rust, Cascade-Logic will provide the low-level state-handoff protocol between the Rust-based workers and the LLM controllers.
