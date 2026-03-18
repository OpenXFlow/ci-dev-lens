# 🧠 ACMI RAG System: Semantic Memory Architecture

**ACMI (Agent-CI Memory Intelligence)** is the persistent knowledge layer of the Agent-CI-Lens orchestrator. Unlike static prompts, ACMI allows the system to learn from its own failures and enforce engineering standards in real-time.

---

## I. Database Architecture (Schema V6)

The system utilizes SQLite with the **FTS5** (Full-Text Search) extension for high-performance keyword-based retrieval.

### 1. Table: `knowledge_bank` (Source of Truth)
Contains explicit engineering rules and best practices defined by the operator.
*   **Key Fields:** `category`, `content`, `is_mandatory`.
*   **Advantage:** Determinism. Rules flagged with `is_mandatory=1` (e.g., *No inline imports*) are injected into the prompt every time, preventing 90% of common LLM implementation errors.

### 2. Table: `execution_logs` (Telemetry & Black Box)
Records every attempt, LLM call, duration, and token consumption.
*   **Key Fields:** `stage`, `provider`, `tokens_used`, `output`, `result`.
*   **Advantage:** ROI analysis and data source for Post-Mortem reflections. The Auditor uses this table to "see" the Developer's attempt history.

### 3. Table: `system_reflections` (Organic Learning)
Stores semantic lessons learned that the Queen agent extracts from failed runs during the `REFLECTION` state.
*   **Key Fields:** `error_pattern`, `solution`, `tags`.
*   **Advantage:** Prevention of recursive errors. If the system fails once on a specific Mypy error, it receives a warning before it starts writing code in the next session.

### 4. Table: `codebase_nodes` (AST Map)
Indexes the code structure (functions, classes, docstrings) without needing to parse entire files.
*   **Advantage:** Context window optimization. Agents receive only relevant function signatures rather than thousands of lines of "noise."

---

## II. Current Search Logic (Heuristic FTS5)

We currently employ **Advanced FTS5 Heuristics** to simulate semantic understanding:
1.  **Backtick Prioritization:** Terms enclosed in backticks (e.g., \`pytest\`) are given the highest weight in the search query.
2.  **Stop-words Filtering:** Eliminates high-frequency noise (e.g., *create, implement, that*) that often causes false positives.
3.  **Positional Weighting:** Technical terms found at the end of a task description (implementation details) are prioritized over initial action verbs.

---

## III. Roadmap: Transition to Vector RAG (Vector Embeddings)

The goal is to transition from searching for *words* to searching for *meaning*.

### Phase 1: `sqlite-vec` Integration (Infra Preparation)
*   Install the SQLite vector extension in the Dev Container.
*   Activate the `vector BLOB` column in the `knowledge_bank` table.

### Phase 2: Embedding Pipeline
*   Introduce a local embedding model (e.g., `all-MiniLM-L6-v2`) via `sentence-transformers`.
*   **Process:** Every `make knowledge-add` call will automatically generate a 384-dimensional vector of the content and store it in the DB.

### Phase 3: Hybrid Search (The Ultimate RAG)
*   Implement a retrieval algorithm that combines:
    *   **Keyword score (FTS5):** Best for exact function names and error codes.
    *   **Semantic score (Cosine Similarity):** Best for understanding context and architectural concepts.
*   **Result:** The system will find the "Side-Effect Isolation" rule even if the operator only types "do not touch the disk in tests."

---

## IV. Knowledge Management (Operator Manual)

### Adding Knowledge
```bash
make knowledge-add CATEGORY="quality" CONTENT="..." MANDATORY=true