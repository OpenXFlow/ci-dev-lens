#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/llm.py (v 1.22)
LLM infrastructure with Instructor support and automated linting context injection.
Added 'Pre-flight log cleaner' to mask old failures and provide ACTION_LOG to agents.
"""

from typing import TypeVar

import httpx
import instructor
import stamina  # type: ignore
from openai import OpenAI
from pydantic import BaseModel

from .models import AgentProfile, EnvConfig, OrchestratorConfigModel
from .utils import (
    DEFAULT_MOCK_RESPONSES,
    count_tokens,
    load_linter_rules,
    log,
)

# Generic type for Pydantic models used by Instructor
T = TypeVar("T", bound=BaseModel)


class TokenBudgetManager:
    """Manages context window usage and triggers compression."""

    def __init__(self, max_tokens: int, config: OrchestratorConfigModel) -> None:
        self.max_tokens = max_tokens
        self.config = config.memory_management
        self.yellow = int(max_tokens * self.config.yellow_zone_threshold.value)
        self.red = int(max_tokens * self.config.red_zone_threshold.value)

    def check(self, prompt: str) -> str:
        """Check if prompt size reached yellow or red safety zones."""
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
        """Backoff hook: retry only on rate limits, server errors, or network drops."""
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code == 429 or exc.response.status_code >= 500
        return isinstance(exc, httpx.RequestError)

    def _try_provider(
        self,
        provider: str,
        profile: AgentProfile,
        prompt: str,
        keys_str: str,
        base_url: str | None,
        tid: str | None,
        response_model: type[T] | None = None,
    ) -> str | T:
        """Iterate through comma-separated keys before failing the provider."""
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
                    log(
                        f"Key for {provider} failed ({err_str}). Rotating key...",
                        "WARN",
                        tid,
                    )
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
    ) -> str | T:
        """Entry point for calling an LLM provider. Supports structured output."""
        provider = profile.provider.upper()

        creds = self.env.credentials.get(provider)
        keys_str = creds.api_key if creds else None
        base_url = creds.base_url if creds else None

        if not keys_str and provider == "GITHUB":
            keys_str = self.env.GITHUB_TOKEN

        if self.mock or not keys_str or "_CHANGE_ME" in keys_str:
            log(f"Mock response for: {agent}", "WARN", tid=tid)
            return DEFAULT_MOCK_RESPONSES.get(agent, f"Mock response for {agent}")

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
    ) -> str | T:
        """Universal execution with robust retries and optional structured validation."""
        if not base_url:
            raise ValueError(f"Missing {provider}_BASE_URL in your .env file.")

        timeout_cfg = httpx.Timeout(
            self.config.resilience.http_read_timeout.value,
            connect=self.config.resilience.http_connect_timeout.value,
        )

        attempts = self.config.resilience.retry_attempts.value
        backoff = self.config.resilience.retry_backoff_factor.value

        for attempt in stamina.retry_context(
            on=self._should_retry,
            attempts=attempts,
            wait_initial=1.0,
            wait_max=30.0,
            wait_exp_base=backoff,
        ):
            with attempt, httpx.Client(timeout=timeout_cfg) as http_client:
                raw_client = OpenAI(api_key=key, base_url=base_url, http_client=http_client)

                if response_model:
                    instructor_client = instructor.from_openai(raw_client)
                    return instructor_client.chat.completions.create(
                        model=p.model,
                        messages=[{"role": "user", "content": prompt}],
                        response_model=response_model,
                        temperature=p.temperature,
                        max_tokens=p.max_tokens,
                    )

                text_resp = raw_client.chat.completions.create(
                    model=p.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=p.temperature,
                    max_tokens=p.max_tokens,
                )
                return str(text_resp.choices[0].message.content)

        raise RuntimeError(f"LLM API Call to {provider} failed exhaustively after {attempts} attempts.")


class PromptBuilder:
    """Constructs prompts for agents using bimetric context and RAG."""

    def build(self, agent: str, _profile: AgentProfile, task: str, session: dict[str, str], state: str) -> str:
        from .utils import ROOT

        persona_path = ROOT / f".agents/{agent}.md"
        persona = persona_path.read_text(encoding="utf-8") if persona_path.exists() else ""

        memory_path = ROOT / "agent_context" / "MEMORY.md"
        memory = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""

        agents_md_path = ROOT / ".claude/cache/AGENTS.md"
        agents_md = agents_md_path.read_text(encoding="utf-8") if agents_md_path.exists() else ""

        tasks_md_path = ROOT / "agent_context" / "TASKS.md"
        tasks_md = tasks_md_path.read_text(encoding="utf-8") if tasks_md_path.exists() else ""

        # Selective Linter Rule Injection
        linter_rules = ""
        if state in ["STRATEGY", "EXECUTING"]:
            linter_rules = f"<linting_rules>\n{load_linter_rules()}\n</linting_rules>\n"

        user_context = session.get("CONTEXT", "")
        system_feedback = session.get("FEEDBACK", "")

        # ARCHITECT FIX: Pre-flight Log Cleaner (View-Level Masking)
        # We slice the action log to only show the events after the last major rollback/failure.
        action_log_full = session.get("ACTION_LOG", "")
        if "--- NEW ATTEMPT" in action_log_full:
            action_log_clean = action_log_full.split("--- NEW ATTEMPT")[-1].strip()
        else:
            action_log_clean = action_log_full.strip()

        feedback_section = ""
        rag_section = ""

        if any(keyword in system_feedback for keyword in ["LAST_ERROR", "FAILED", "REJECT", "VIOLATION"]):
            feedback_section = (
                "\n<CRITICAL_FEEDBACK>\n"
                "🛑 YOUR PREVIOUS ATTEMPT FAILED.\n"
                "Read the error log in ADDITIONAL INSTRUCTIONS carefully and FIX the issue.\n"
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
            f"{linter_rules}"
            f"<project_memory>\n{memory}\n</project_memory>\n"
            f"<codebase_map>\n{agents_md}\n</codebase_map>\n"
            f"<current_tasks>\n{tasks_md}\n</current_tasks>\n"
            f"<current_session_state>\n"
            f"WORKSPACE_FILES: {session.get('WORKSPACE')}\n"
            f"CURRENT_SYSTEM_STATE: {session.get('STATE')}\n"
            f"</current_session_state>\n"
            f"<current_action_log>\n{action_log_clean}\n</current_action_log>\n"
            f"<user_input>\n"
            f"TASK: {task}\n"
            f"ADDITIONAL INSTRUCTIONS: {user_context}\n"
            f"SYSTEM FEEDBACK / ERRORS: {system_feedback}\n"
            f"</user_input>\n"
            f"{feedback_section}"
            f"{rag_section}"
        )
