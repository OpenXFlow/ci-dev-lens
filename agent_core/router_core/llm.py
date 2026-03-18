#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/llm.py (v 3.9.1)
LLM infrastructure with Instructor support, automated linting context injection,
and Dual-Source RAG Querying for Expert Knowledge and Token protection.
Surgical Patch: Systematic Rule Injection (Loads all .claude/rules/*.md).
Surgical Patch: Early Return for empty codebase to prevent "Ghost Files" hallucination.
Surgical Patch 3.7.1: Ruff compliance fixes (RUF005, S608, E501).
Milestone 5.0 (v3.8.0): Dynamic Mandatory Rule Injection.
Milestone 6.0 (v3.9.1): Token Telemetry extraction and Ruff compliance (ANN401, S608).
"""

import contextlib
import re
import sys
from typing import Any, TypeVar

import httpx
import instructor
import stamina  # type: ignore
from openai import OpenAI
from pydantic import BaseModel

from .models import AgentProfile, EnvConfig, OrchestratorConfigModel
from .utils import (
    DEFAULT_MOCK_RESPONSES,
    ROOT,
    count_tokens,
    load_linter_rules,
    load_orchestrator_config,
    log,
)

T = TypeVar("T", bound=BaseModel)

# SURGICAL PATCH: START - Module-level constants for RAG Heuristics
_STOP_WORDS: frozenset[str] = frozenset(
    {
        # Conjunctions and prepositions
        "this",
        "that",
        "with",
        "from",
        "into",
        "their",
        "there",
        "where",
        "which",
        "while",
        "before",
        "after",
        "above",
        "below",
        "through",
        "without",
        "within",
        "between",
        "against",
        # Auxiliary verbs
        "will",
        "must",
        "need",
        "have",
        "been",
        "when",
        "then",
        "than",
        "also",
        "should",
        # Overly generic action verbs
        "create",
        "implement",
        "update",
        "modify",
        "write",
        "include",
        "ensure",
        "make",
        "call",
        "check",
        "using",
        # Overly generic nouns
        "task",
        "goal",
        "simple",
        "file",
        "files",
        "code",
        "case",
        "cases",
        "stage",
        "pipeline",
        "state",
        "running",
        "current",
        "return",
        "returns",
        "pass",
        "fail",
        # Vague/ambiguous words
        "both",
        "each",
        "such",
        "able",
        "data",
        "input",
        "output",
        "result",
        "error",
        "string",
        "list",
        "dict",
        "bool",
        "none",
        "logic",
        "handle",
        "handler",
        "process",
        "system",
        "given",
        "based",
        "defined",
        # Retained from original list
        "function",
        "method",
        "package",
        "valid",
        "value",
        "verify",
        "agent",
        "module",
    }
)


_DOMAIN_CATEGORIES: list[str] = ["python", "general", "ab-testing", "architecture"]

AGENT_CATEGORY_MAP: dict[str, list[str]] = {
    "queen": ["orchestration", "architecture", "delivery", "quality", *_DOMAIN_CATEGORIES],
    "developer": ["implementation", "architecture", *_DOMAIN_CATEGORIES],
    "pedant": ["quality", *_DOMAIN_CATEGORIES],
    "auditor": ["quality", "delivery", "architecture", *_DOMAIN_CATEGORIES],
}
# SURGICAL PATCH: END


class TokenBudgetManager:
    """Manages context window usage and triggers compression."""

    def __init__(self, max_tokens: int, config: OrchestratorConfigModel) -> None:
        self.max_tokens = max_tokens
        self.config = config.memory_management
        self.yellow = int(max_tokens * self.config.yellow_zone_threshold.value)
        self.red = int(max_tokens * self.config.red_zone_threshold.value)

    def check(self, prompt: str) -> str:
        t = count_tokens(prompt)
        if t >= self.red:
            return "red"
        if t >= self.yellow:
            return "yellow"
        return "ok"


class APIClient:
    """Agnostic API client supporting text and structured outputs (via Instructor)."""

    def __init__(self, env: EnvConfig, mock: bool, config: OrchestratorConfigModel) -> None:
        self.env = env
        self.mock = mock
        self.config = config

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code == 429 or exc.response.status_code >= 500
        return isinstance(exc, httpx.RequestError)

    # SURGICAL PATCH: ANN401 Fix - Changed Any to object
    def _parse_usage(self, usage: object) -> dict[str, int]:
        """Robust extraction of token counts with provider fallbacks."""
        if not usage:
            return {"prompt": 0, "completion": 0, "total": 0}

        # OpenAI-compatible / Groq / Mistral
        p = getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0)
        c = getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0)
        t = getattr(usage, "total_tokens", 0)

        if t == 0:
            t = p + c

        return {"prompt": p, "completion": c, "total": t}

    def _try_provider(
        self,
        provider: str,
        profile: AgentProfile,
        prompt: str,
        keys_str: str,
        base_url: str | None,
        tid: str | None,
        response_model: type[T] | None = None,
    ) -> tuple[str | T, dict[str, int]]:
        keys = [k.strip() for k in keys_str.split(",")] if keys_str else []
        if not keys:
            raise ValueError(f"No API keys provided for {provider}")

        last_error: Exception | None = None
        for key in keys:
            try:
                return self._do_call(provider, profile, prompt, key, base_url, response_model)
            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(err_code in err_str for err_code in ("429", "401", "403")):
                    log(f"Key for {provider} failed ({err_str}). Rotating key...", "WARN", tid)
                    continue
                break

        if last_error:
            raise last_error
        raise RuntimeError(f"Unknown error occurred while trying keys for {provider}")

    def call(
        self,
        agent: str,
        profile: AgentProfile,
        prompt: str,
        tid: str | None = None,
        response_model: type[T] | None = None,
    ) -> tuple[str | T, dict[str, int]]:
        provider = profile.provider.upper()
        creds = self.env.credentials.get(provider)
        keys_str = creds.api_key if creds else None
        base_url = creds.base_url if creds else None

        if not keys_str and provider == "GITHUB":
            keys_str = self.env.GITHUB_TOKEN

        if self.mock or not keys_str or "_CHANGE_ME" in keys_str:
            log(f"Mock response for: {agent}", "WARN", tid=tid)
            mock_resp = DEFAULT_MOCK_RESPONSES.get(agent, f"Mock response for {agent}")
            return mock_resp, {"prompt": 0, "completion": 0, "total": 0}

        if keys_str is None:
            raise ValueError(f"Credentials for {provider} are not configured.")

        try:
            return self._try_provider(provider, profile, prompt, keys_str, base_url, tid, response_model)
        except Exception as e:
            resilience = self.config.resilience
            if resilience.smart_fallback.value and (fallback_info := resilience.fallback_matrix.get(provider)):
                fb_provider = fallback_info.fallback_provider.upper()
                log(f"Primary {provider} failed. FALLBACK -> {fb_provider}.", "WARN", tid)
                fb_creds = self.env.credentials.get(fb_provider)
                fb_keys_str = fb_creds.api_key if fb_creds else None
                fb_base_url = fb_creds.base_url if fb_creds else None
                if fb_keys_str is None:
                    raise RuntimeError(f"Fallback credentials for {fb_provider} missing.") from e
                fallback_profile = profile.model_copy()
                fallback_profile.provider = fb_provider.lower()
                fallback_profile.model = fallback_info.fallback_model
                try:
                    return self._try_provider(
                        fb_provider, fallback_profile, prompt, fb_keys_str, fb_base_url, tid, response_model
                    )
                except Exception as fb_e:
                    raise RuntimeError(f"Primary & Fallback failed. Error: {fb_e}") from fb_e
            else:
                raise RuntimeError(f"API Error ({provider}): {e}") from e

    def _do_call(
        self,
        provider: str,
        p: AgentProfile,
        prompt: str,
        key: str,
        base_url: str | None,
        response_model: type[T] | None = None,
    ) -> tuple[str | T, dict[str, int]]:
        if not base_url:
            raise ValueError(f"Missing {provider}_BASE_URL in your .env file.")
        timeout_cfg = httpx.Timeout(
            self.config.resilience.http_read_timeout.value, connect=self.config.resilience.http_connect_timeout.value
        )
        attempts = self.config.resilience.retry_attempts.value
        backoff = self.config.resilience.retry_backoff_factor.value
        for attempt in stamina.retry_context(
            on=self._should_retry, attempts=attempts, wait_initial=1.0, wait_max=30.0, wait_exp_base=backoff
        ):
            with attempt, httpx.Client(timeout=timeout_cfg) as http_client:
                raw_client = OpenAI(api_key=key, base_url=base_url, http_client=http_client)
                if response_model:
                    instructor_client = instructor.from_openai(raw_client)
                    # instructor returns the model but raw response is attached
                    resp_model = instructor_client.chat.completions.create(
                        model=p.model,
                        messages=[{"role": "user", "content": prompt}],
                        response_model=response_model,
                        temperature=p.temperature,
                        max_tokens=p.max_tokens,
                    )
                    # extract usage from attached raw response
                    raw_usage = getattr(resp_model, "_raw_response", None)
                    usage_data = self._parse_usage(raw_usage.usage if raw_usage else None)
                    return resp_model, usage_data

                text_resp = raw_client.chat.completions.create(
                    model=p.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=p.temperature,
                    max_tokens=p.max_tokens,
                )
                usage_data = self._parse_usage(text_resp.usage)
                return str(text_resp.choices[0].message.content), usage_data
        raise RuntimeError(f"LLM API Call to {provider} failed exhaustively.")


class PromptBuilder:
    """Constructs prompts for agents using bimetric context, Rules and Dual-Source RAG."""

    def _extract_keywords(self, task_desc: str) -> str:
        """Extracts prioritized, weighted keywords for FTS5 queries."""
        # 1. Backtick termíny (Najvyššia priorita, povolené aj kratšie slová >= 3)
        backtick_terms = re.findall(r"`([^`]+)`", task_desc)
        backtick_words = [
            w.lower()
            for term in backtick_terms
            for w in re.findall(r"\b[a-zA-Z_]+\b", term)
            if len(w) >= 3 and w.lower() not in _STOP_WORDS
        ]

        # 2. Všetky slová z textu (Váhovanie podľa pozície: koniec textu má prednosť)
        all_words = [
            w.lower() for w in re.findall(r"\b[a-zA-Z_]+\b", task_desc) if len(w) >= 4 and w.lower() not in _STOP_WORDS
        ]
        midpoint = len(all_words) // 2
        ordered_words = all_words[midpoint:] + all_words[:midpoint]

        # 3. Kombinácia a deduplikácia (Zanechá si poradie: Backticks -> Koniec -> Začiatok)
        combined = backtick_words + ordered_words
        keywords = list(dict.fromkeys(combined))[:10]

        return " OR ".join(f'"{kw}"' for kw in keywords) if keywords else ""

    def _get_system_rules(self) -> str:
        """Systematically loads all engineering rules from .claude/rules/."""
        rules_dir = ROOT / ".claude" / "rules"
        if not rules_dir.exists():
            return ""

        rule_texts = []
        for rule_file in sorted(rules_dir.glob("*.md")):
            content = rule_file.read_text(encoding="utf-8")
            rule_texts.append(f"--- RULE: {rule_file.name} ---\n{content}")

        return "\n\n".join(rule_texts)

    def _get_rag_codebase_map(self, task_desc: str) -> str:
        config = load_orchestrator_config()
        codebase_map = ""
        if config.memory_engine.enabled.value:
            try:
                try:
                    from agent_core.memory_engine import MemoryEngine
                except ImportError:
                    sys.path.insert(0, str(ROOT))
                    from agent_core.memory_engine import MemoryEngine
                with MemoryEngine() as engine, engine.get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM codebase_nodes")
                    count = cursor.fetchone()[0]

                    if count == 0:
                        return "[MEMORY ENGINE - RAG Context]\nCodebase is currently empty. Start a new module."

                    words = [w for w in re.findall(r"\b[a-zA-Z_]+\b", task_desc) if len(w) >= 4]
                    keywords = list(dict.fromkeys(words))[:5]
                    if keywords:
                        conditions = " OR ".join(["name LIKE ? OR docstring LIKE ?"] * len(keywords))
                        params: list[Any] = []
                        for kw in keywords:
                            params.extend([f"%{kw}%", f"%{kw}%"])
                        limit = config.memory_engine.fts_result_limit.value
                        params.append(limit)
                        query = (
                            f"SELECT DISTINCT name, signature, docstring FROM codebase_nodes WHERE {conditions} LIMIT ?"  # noqa: S608
                        )
                        cursor = conn.execute(query, params)
                        rows = cursor.fetchall()
                        if rows:
                            lines = ["[MEMORY ENGINE - RAG Context] (Targeted Signatures)"]
                            for r in rows:
                                doc = r["docstring"] or ""
                                lines.append(f"- {r['name']}{r['signature']} : {doc}")
                            codebase_map = "\n".join(lines)
            except Exception as e:
                log(f"Codebase RAG Query failed, falling back to markdown map: {e}", "WARN")

        if not codebase_map:
            agents_md_path = ROOT / ".claude/cache/AGENTS.md"
            if agents_md_path.exists():
                codebase_map = agents_md_path.read_text(encoding="utf-8")
            else:
                codebase_map = "[Codebase map is currently empty or unavailable]"
        return codebase_map

    def _get_dual_source_rag(self, agent: str, task_desc: str) -> str:
        """Queries RAG using advanced keyword extraction, category filtering, and separate limits."""
        config = load_orchestrator_config()
        if not config.memory_engine.enabled.value:
            return ""

        try:
            from agent_core.memory_engine import MemoryEngine
        except ImportError:
            sys.path.insert(0, str(ROOT))
            from agent_core.memory_engine import MemoryEngine

        safe_query = self._extract_keywords(task_desc)

        human_verified: list[str] = []
        ai_reflections: list[str] = []
        kb_ids: list[str] = []
        ref_ids: list[str] = []

        with MemoryEngine() as engine, engine.get_connection() as conn:
            agent_categories = AGENT_CATEGORY_MAP.get(agent, [])

            # 1. Fetch MANDATORY rules from Knowledge Bank
            #    (Bypasses FTS5 query entirely to guarantee inclusion)
            if agent_categories:
                placeholders = ",".join("?" * len(agent_categories))
                man_sql = f"""
                    SELECT id, category, type, content
                    FROM knowledge_bank
                    WHERE is_mandatory = 1
                      AND category IN ({placeholders})
                """  # noqa: S608 -- Safe placeholder construction
                man_cursor = conn.execute(man_sql, agent_categories)
                for r in man_cursor.fetchall():
                    kb_ids.append(str(r["id"]))
                    ctype = f" [{r['type'].upper()}]" if r["type"] else ""
                    human_verified.append(f"• {r['category'].upper()}{ctype} (MANDATORY): {r['content']}")

            # 2. Fetch Contextual Knowledge via FTS5
            if safe_query:
                if agent_categories:
                    placeholders = ",".join("?" * len(agent_categories))
                    kb_sql = f"""
                        SELECT coalesce(p.id, c.id) as id,
                               coalesce(p.category, c.category) as category,
                               coalesce(p.type, c.type) as type,
                               coalesce(p.content, c.content) as content
                        FROM knowledge_bank_fts f
                        JOIN knowledge_bank c ON f.rowid = c.id
                        LEFT JOIN knowledge_bank p ON c.parent_id = p.id
                        WHERE knowledge_bank_fts MATCH ?
                          AND c.category IN ({placeholders})
                        ORDER BY f.rank LIMIT 6
                    """  # noqa: S608 -- Safe placeholder construction
                    params = [safe_query, *agent_categories]
                    kb_cursor = conn.execute(kb_sql, params)
                    for r in kb_cursor.fetchall():
                        row_id = str(r["id"])
                        if row_id not in kb_ids:  # Avoid duplicate rules
                            kb_ids.append(row_id)
                            ctype = f" [{r['type'].upper()}]" if r["type"] else ""
                            human_verified.append(f"• {r['category'].upper()}{ctype}: {r['content']}")

                # 3. Fetch from System Reflections (no category filter)
                ref_sql = """
                    SELECT rowid as id, error_pattern, solution
                    FROM system_reflections_fts
                    WHERE system_reflections_fts MATCH ?
                    ORDER BY rank LIMIT 3
                """
                ref_cursor = conn.execute(ref_sql, (safe_query,))
                for r in ref_cursor.fetchall():
                    ref_ids.append(str(r["id"]))
                    ai_reflections.append(f"• AVOID: {r['error_pattern']}\n  SOLUTION: {r['solution']}")

        # Build final prompt section with explicit ordering
        sections: list[str] = []
        if human_verified:
            sections.append("[KNOWLEDGE - Human Verified]\n" + "\n".join(human_verified))
        if ai_reflections:
            sections.append("[MEMORY WARNING - Agent Reflection]\n" + "\n".join(ai_reflections))

        if sections:
            kb_ids_str = f" (IDs: {','.join(kb_ids)})" if kb_ids else ""
            ref_ids_str = f" (IDs: {','.join(ref_ids)})" if ref_ids else ""
            log(
                (
                    f"ACMI RAG: Injecting {len(human_verified)} rules{kb_ids_str} "
                    f"and {len(ai_reflections)} reflections{ref_ids_str}."
                ),
                "OK",
            )
        return "\n\n".join(sections) + "\n" if sections else ""

    def _get_execution_history(self, tid: str) -> str:
        config = load_orchestrator_config()
        if not config.memory_engine.enabled.value:
            return ""
        try:
            try:
                from agent_core.memory_engine import MemoryEngine
            except ImportError:
                sys.path.insert(0, str(ROOT))
                from agent_core.memory_engine import MemoryEngine
            with MemoryEngine() as engine, engine.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT stage, tool, result, duration_ms, attempt FROM execution_logs "
                    "WHERE task_id = ? ORDER BY timestamp ASC",
                    (tid,),
                )
                rows = cursor.fetchall()
                if rows:
                    lines = ["[SYSTEM DB - TASK HISTORY]"]
                    for r in rows:
                        duration = r["duration_ms"] or 0
                        lines.append(
                            f"Attempt {r['attempt']} | {str(r['stage']).ljust(9)} | "
                            f"{str(r['tool']).ljust(8)} | {str(r['result']).ljust(4)} | {duration}ms"
                        )
                    return "\n" + "\n".join(lines) + "\n"
        except Exception as e:
            log(f"Failed to fetch execution history: {e}", "WARN", tid)
        return ""

    def build(
        self, agent: str, _profile: AgentProfile, task: str, session: dict[str, str], state: str, tid: str | None = None
    ) -> str:
        persona_path = ROOT / f".agents/{agent}.md"
        persona = persona_path.read_text(encoding="utf-8") if persona_path.exists() else ""
        memory_path = ROOT / "agent_context" / "MEMORY.md"
        memory = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""

        system_rules = f"<engineering_standards>\n{self._get_system_rules()}\n</engineering_standards>\n"

        codebase_map = self._get_rag_codebase_map(task)
        tasks_md_path = ROOT / "agent_context" / "TASKS.md"
        tasks_md = tasks_md_path.read_text(encoding="utf-8") if tasks_md_path.exists() else ""

        linter_rules = ""
        if state in ["STRATEGY", "EXECUTING"]:
            linter_rules = f"<linting_rules_config>\n{load_linter_rules()}\n</linting_rules_config>\n"

        user_context = session.get("CONTEXT", "")
        system_feedback = session.get("FEEDBACK", "")
        action_log_full = session.get("ACTION_LOG", "")
        action_log_clean = (
            action_log_full.split("--- NEW ATTEMPT")[-1].strip()
            if "--- NEW ATTEMPT" in action_log_full
            else action_log_full.strip()
        )

        history_section = ""
        if agent == "auditor":
            tid_to_use = tid
            if not tid_to_use:
                with contextlib.suppress(Exception):
                    from .managers import TasksManager

                    active_tasks = TasksManager().get_active_tasks()
                    if active_tasks:
                        tid_to_use = str(active_tasks[0]["id"])
            if tid_to_use:
                history_section = self._get_execution_history(tid_to_use)

        expert_system_section = ""
        if state in ["STRATEGY", "EXECUTING"]:
            dual_rag = self._get_dual_source_rag(agent, task)
            if dual_rag:
                expert_system_section = f"\n<expert_system_rag>\n{dual_rag}</expert_system_rag>\n"

        feedback_section = ""
        rag_section = ""
        if any(keyword in system_feedback for keyword in ["LAST_ERROR", "FAILED", "REJECT", "VIOLATION"]):
            feedback_section = (
                "\n<CRITICAL_FEEDBACK>\n"
                "🛑 YOUR PREVIOUS ATTEMPT FAILED.\n"
                "Read the error log carefully and FIX the issue.\n"
                '⚠️ MANDATORY: Still use <file_write path="..."> tags. DO NOT use raw markdown.\n'
                "</CRITICAL_FEEDBACK>\n"
            )
            tb_path = ROOT / "agent_context" / "TROUBLESHOOTING.md"
            if tb_path.exists():
                tb_content = tb_path.read_text(encoding="utf-8")
                relevant_solutions = []
                for block in tb_content.split("### @"):
                    if not block.strip():
                        continue
                    keyword, _, advice = block.partition("\n")
                    keyword = keyword.strip()
                    if keyword and keyword in system_feedback:
                        relevant_solutions.append(f"-[{keyword}]: {advice.strip()}")
                if relevant_solutions:
                    rag_section = (
                        "\n========================================\n"
                        "🧠 KNOWLEDGE BASE HINTS FOR THIS ERROR:\n"
                        + "\n".join(relevant_solutions)
                        + "\n========================================\n"
                    )

        return (
            f"<system_persona>\n{persona}\n</system_persona>\n"
            f"{system_rules}"
            f"{linter_rules}"
            f"<project_memory>\n{memory}\n</project_memory>\n"
            f"{expert_system_section}"
            f"<codebase_map>\n{codebase_map}\n</codebase_map>\n"
            f"<current_tasks>\n{tasks_md}\n</current_tasks>\n"
            "<current_session_state>\n"
            f"WORKSPACE_FILES: {session.get('WORKSPACE')}\n"
            f"CURRENT_SYSTEM_STATE: {session.get('STATE')}\n"
            "</current_session_state>\n"
            f"<current_action_log>\n{action_log_clean}\n</current_action_log>\n"
            f"{history_section}"
            f"<user_input>\n"
            f"TASK: {task}\n"
            f"ADDITIONAL INSTRUCTIONS: {user_context}\n"
            f"SYSTEM FEEDBACK / ERRORS: {system_feedback}\n"
            f"</user_input>\n"
            f"{feedback_section}{rag_section}"
        )
