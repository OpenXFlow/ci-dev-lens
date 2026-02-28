# ENGINEERING IRON LAWS
These rules are ABSOLUTE. Violating them results in an immediate HALT.

## 1. ZERO THEATER
Never assume that code works. 
- ❌ "I fixed the bug; it should work now." (No proof)
- ✅ "I ran the test. Output shows PASS. The code is functional." (With proof)
You MUST always see and verify the actual terminal output.

## 2. EVIDENCE BEFORE ACTION
Do not modify a file until you have read it.
Do not execute a command until you have verified your current working directory.

## 3. TEST DRIVEN DEVELOPMENT (TDD)
No production code shall exist without a corresponding test.
1. Write the test (Red).
2. Run the test (confirm failure).
3. Implement the logic (Green).
4. Run the test (confirm success).

## 4. IMMUTABLE ARCHITECTURE
Never modify files in `agent_core/` or `.claude/` unless you receive an explicit "ARCHITECTURAL CHANGE" command. These files constitute your Kernel.