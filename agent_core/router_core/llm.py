#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/llm.py - LLM infrastructure (v 1.9 Pydantic + Httpx)."""

import httpx
import stamina

from .models import AgentProfile, EnvConfig, OrchestratorConfigModel
from .utils import DEFAULT_MOCK_RESPONSES, count_tokens, log


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
    """Agnostic API client supporting multiple providers and key rotation."""

    def __init__(self, env: EnvConfig, mock: bool, config: OrchestratorConfigModel) -> None:
        self.env = env
        self.mock = mock
        self.config = config

    def _should_retry(self, exc: Exception) -> bool:
        """Backoff hook: retry only on rate limits (429), server errors (50x), or network drops."""
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
    ) -> str:
        """Iterate through comma-separated keys before failing the provider."""
        keys = [k.strip() for k in keys_str.split(",")] if keys_str else []
        if not keys:
            raise ValueError(f"No API keys provided for {provider}")

        last_error: Exception | None = None
        for key in keys:
            try:
                return self._do_call(provider, profile, prompt, key, base_url)
            except Exception as e:
                last_error = e
                err_str = str(e)
                # Rotate key if rate-limited or unauthorized AFTER stamina gives up
                if "429" in err_str or "401" in err_str or "403" in err_str:
                    log(
                        f"Key for {provider} failed ({err_str}). Rotating to next key if available...",
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
    ) -> str:
        """Entry point for calling an LLM provider with fallback logic."""
        provider = profile.provider.upper()

        # Dynamic credential lookup via Pydantic model
        creds = self.env.credentials.get(provider)
        keys_str = creds.api_key if creds else None
        base_url = creds.base_url if creds else None

        # Special case for GitHub Token if not in dynamic credentials
        if not keys_str and provider == "GITHUB":
            keys_str = self.env.GITHUB_TOKEN

        if self.mock or not keys_str or "_CHANGE_ME" in keys_str:
            log(f"Mock response for: {agent}", "WARN", tid=tid)
            return DEFAULT_MOCK_RESPONSES.get(agent, f"Mock response for {agent}")

        try:
            return self._try_provider(provider, profile, prompt, keys_str, base_url, tid)
        except Exception as e:
            resilience = self.config.resilience
            use_fallback = resilience.smart_fallback.value
            fallback_matrix = resilience.fallback_matrix

            fallback_info = fallback_matrix.get(provider)

            if use_fallback and fallback_info:
                fb_provider = fallback_info.fallback_provider.upper()
                fb_model = fallback_info.fallback_model

                log(
                    f"All keys for {provider} failed. TRIGGERING FALLBACK -> {fb_provider}.",
                    "WARN",
                    tid,
                )

                # Fallback lookup
                fb_creds = self.env.credentials.get(fb_provider)
                fb_keys_str = fb_creds.api_key if fb_creds else None
                fb_base_url = fb_creds.base_url if fb_creds else None

                if not fb_keys_str and fb_provider == "GITHUB":
                    fb_keys_str = self.env.GITHUB_TOKEN

                if not fb_keys_str or "_CHANGE_ME" in fb_keys_str:
                    raise RuntimeError(f"Fallback key for {fb_provider} is missing from .env.") from e

                fallback_profile = profile.model_copy()
                fallback_profile.provider = fb_provider.lower()
                fallback_profile.model = fb_model

                try:
                    return self._try_provider(
                        fb_provider,
                        fallback_profile,
                        prompt,
                        fb_keys_str,
                        fb_base_url,
                        tid,
                    )
                except Exception as fb_e:
                    raise RuntimeError(f"Primary API & Fallback API both failed. Final error: {fb_e}") from fb_e
            else:
                raise RuntimeError(f"API Error ({provider}): {e}") from e

    def _do_call(
        self,
        provider: str,
        p: AgentProfile,
        prompt: str,
        key: str,
        base_url: str | None,
    ) -> str:
        """Universal execution using standard OpenAI schema with robust retries."""
        if not base_url:
            raise ValueError(f"Missing {provider}_BASE_URL in your .env file.")

        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"Security Error: Base URL for {provider} must start with http:// or https://")

        payload = {
            "model": p.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": p.max_tokens,
            "temperature": p.temperature,
        }

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Agent-CI-Lens/1.0",
        }

        timeout_cfg = httpx.Timeout(
            connect=self.config.resilience.http_connect_timeout.value,
            read=self.config.resilience.http_read_timeout.value,
            write=10.0,
            pool=10.0,
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
            # Opravené vnorenie (SIM117) do jedného riadku
            with attempt, httpx.Client(timeout=timeout_cfg) as client:
                resp = client.post(base_url, json=payload, headers=headers)
                resp.raise_for_status()

                response_payload = resp.json()
                return str(response_payload["choices"][0]["message"]["content"])

        # Opravený chýbajúci return (RET503) pre prípad, že cyklus skončí bez návratu
        raise RuntimeError(f"LLM API Call to {provider} failed exhaustively after {attempts} attempts.")


class PromptBuilder:
    """Constructs prompts for agents using bimetric context and RAG."""

    def build(self, agent: str, profile: AgentProfile, task: str, session: dict[str, str]) -> str:  # noqa: ARG002
        # Load assets from Model 5.3 structure
        from .utils import ROOT

        persona_path = ROOT / f".agents/{agent}.md"
        persona = persona_path.read_text(encoding="utf-8") if persona_path.exists() else ""

        memory_path = ROOT / "agent_context" / "MEMORY.md"
        memory = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""

        agents_md_path = ROOT / ".claude/cache/AGENTS.md"
        agents_md = agents_md_path.read_text(encoding="utf-8") if agents_md_path.exists() else ""

        tasks_md_path = ROOT / "agent_context" / "TASKS.md"
        tasks_md = tasks_md_path.read_text(encoding="utf-8") if tasks_md_path.exists() else ""

        user_context = session.get("CONTEXT", "")
        system_feedback = session.get("FEEDBACK", "")
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
                        relevant_solutions.append(f"- [{keyword}]: {advice.strip()}")

                if relevant_solutions:
                    rag_section = (
                        "\n========================================\n"
                        "🧠 KNOWLEDGE BASE HINTS FOR THIS ERROR:\n"
                        + "\n".join(relevant_solutions)
                        + "\n========================================\n"
                    )

        return (
            f"<system_persona>\n{persona}\n</system_persona>\n"
            f"<project_memory>\n{memory}\n</project_memory>\n"
            f"<codebase_map>\n{agents_md}\n</codebase_map>\n"
            f"<current_tasks>\n{tasks_md}\n</current_tasks>\n"
            f"<current_session_state>\n"
            f"WORKSPACE_FILES: {session.get('WORKSPACE')}\n"
            f"CURRENT_SYSTEM_STATE: {session.get('STATE')}\n"
            f"</current_session_state>\n"
            f"<user_input>\n"
            f"TASK: {task}\n"
            f"ADDITIONAL INSTRUCTIONS: {user_context}\n"
            f"SYSTEM FEEDBACK / ERRORS: {system_feedback}\n"
            f"</user_input>\n"
            f"{feedback_section}"
            f"{rag_section}"
        )
