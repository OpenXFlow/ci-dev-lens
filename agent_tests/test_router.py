#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_router.py - Full unit tests for Router Engine and Logic (v 1.7 Pydantic).
Fixtures are defined in conftest.py
"""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_core.router_core.engine import Router
from agent_core.router_core.llm import APIClient, PromptBuilder, TokenBudgetManager
from agent_core.router_core.managers import HaltManager, SessionManager, TasksManager
from agent_core.router_core.models import (
    AgentProfile,
    EnvConfig,
    OrchestratorConfigModel,
)
from agent_core.router_core.utils import count_tokens


# ==========================================
# GLOBAL TEST FIXTURES
# ==========================================
@pytest.fixture(autouse=True)
def fast_tests_no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Globally disable time.sleep during tests to prevent rate-limit delays."""
    monkeypatch.setattr(time, "sleep", lambda _x: None)


# Helper to create a valid OrchestratorConfigModel for tests
def create_mock_config() -> OrchestratorConfigModel:
    return OrchestratorConfigModel.model_validate(
        {
            "version": "1.3",
            "workflow_global": {
                "ci_mode": {"value": "local"},
                "loop_mode": {"value": True},
                "loop_delay_seconds": {"value": 0},
                "max_task_attempts": {"value": 3},
                "max_continuous_tasks": {"value": 10},
            },
            "workflow_local": {
                "ANALYSE": {"active": {"value": True}, "max_retries": {"value": 1}},
                "PLANNING": {"active": {"value": True}, "max_retries": {"value": 1}},
                "EXECUTING": {"active": {"value": True}, "max_retries": {"value": 1}},
                "LINTING": {"active": {"value": True}, "max_retries": {"value": 1}},
                "TESTING": {"active": {"value": True}, "max_retries": {"value": 1}},
                "VERIFYING": {"active": {"value": True}, "max_retries": {"value": 1}},
            },
            "resilience": {
                "smart_fallback": {"value": False},
                "http_connect_timeout": {"value": 10.0},
                "http_read_timeout": {"value": 30.0},
                "retry_attempts": {"value": 3},
                "retry_backoff_factor": {"value": 1.5},
                "fallback_matrix": {},
            },
            "memory_management": {
                "yellow_zone_threshold": {"value": 0.7},
                "red_zone_threshold": {"value": 0.9},
            },
            "logging": {"show_task_id": {"value": True}, "verbosity": {"value": "INFO"}},
        }
    )


# ==========================================
# 1. CORE UTILITIES
# ==========================================
class TestCountTokens:
    def test_empty_string(self) -> None:
        """Verify that an empty string returns 0 tokens."""
        assert count_tokens("") == 0

    def test_single_word(self) -> None:
        """Verify that a single word is counted as at least one token."""
        assert count_tokens("hello") >= 1

    def test_longer_text_has_more_tokens(self) -> None:
        """Verify that longer strings result in a higher token count."""
        assert count_tokens("hello world foo bar baz") > count_tokens("hello")


# ==========================================
# 2. SESSION MANAGER
# ==========================================
class TestSessionManager:
    def test_read_existing_session(self, tmp_project: Path) -> None:
        """Verify reading a session file from agent_context."""
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        assert sm.read()["STATE"] == "IDLE"

    def test_write_state(self, tmp_project: Path) -> None:
        """Verify updating the system state in agent_context."""
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_state("EXECUTING")
        assert sm.read()["STATE"] == "EXECUTING"

    def test_write_context(self, tmp_project: Path) -> None:
        """Verify updating the persistent context in agent_context."""
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_context("New test context")
        assert sm.read()["CONTEXT"] == "New test context"

    def test_add_workspace(self, tmp_project: Path) -> None:
        """Verify adding files to the workspace listing."""
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.add_workspace("src/auth.py")
        assert "src/auth.py" in sm.read()["WORKSPACE"]

    def test_write_action_log(self, tmp_project: Path) -> None:
        """Verify appending entries to the action log."""
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_action_log("Test entry")
        assert "Test entry" in sm.read()["ACTION_LOG"]

    def test_schema_preserved_after_multiple_writes(self, tmp_project: Path) -> None:
        """Verify that bimetric section headers remain intact after updates."""
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_state("PLANNING")
        sm.write_context("Data")
        sm.add_workspace("src/logic.py")
        content = sm.path.read_text(encoding="utf-8")
        for section in ["## [USER_SECTION]", "## [AGENT_SECTION]"]:
            assert section in content


# ==========================================
# 3. TASKS MANAGER
# ==========================================
class TestTasksManager:
    def test_get_active_tasks(self, tmp_project: Path) -> None:
        """Verify parsing of pending tasks from agent_context."""
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tasks = tm.get_active_tasks()
        assert len(tasks) >= 1
        assert tasks[0]["id"] == "001"

    def test_increment_attempts(self, tmp_project: Path) -> None:
        """Verify attempt counter increments for a specific task."""
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        new_val = tm.increment_attempts("001", "ErrorMsg")
        assert new_val == 1
        assert tm.get_active_tasks()[0]["attempts"] == 1

    def test_blocked_after_max_attempts(self, tmp_project: Path) -> None:
        """Verify task blocking logic after 3 failures."""
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tm.max_attempts = 3
        for i in range(3):
            tm.increment_attempts("001", f"Error {i}")
        assert "[BLOCKED]" in tm.path.read_text(encoding="utf-8")

    def test_no_active_tasks_after_block(self, tmp_project: Path) -> None:
        """Ensure blocked tasks trigger fallback to GOAL from USER_QUEUE."""
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tm.max_attempts = 1
        tm.increment_attempts("001", "Fatal")

        # Expecting synthetic goal fallback
        tasks = tm.get_active_tasks()
        assert len(tasks) == 1
        assert tasks[0].get("is_synthetic") is True

    def test_mark_completed(self, tmp_project: Path) -> None:
        """Verify that [ ] is correctly replaced by [x] in agent_context."""
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tm.mark_completed("001")
        assert "- [x] TASK-001" in tm.path.read_text(encoding="utf-8")


# ==========================================
# 4. HALT MANAGER
# ==========================================
class TestHaltManager:
    def test_not_halted_initially(self, tmp_project: Path) -> None:
        """Verify system is operational without flag file."""
        hm = HaltManager()
        hm.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        assert not hm.is_halted()

    def test_halt_creates_flag(self, tmp_project: Path) -> None:
        """Verify activation of HALT state creates a physical file."""
        hm = HaltManager()
        hm.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        hm.halt("Safety stop")
        assert hm.is_halted()
        assert "Safety stop" in hm.flag_path.read_text(encoding="utf-8")


# ==========================================
# 5. TOKEN BUDGET MANAGER
# ==========================================
class TestTokenBudgetManager:
    def test_ok_zone(self) -> None:
        """Verify status when context usage is low."""
        config = create_mock_config()
        assert TokenBudgetManager(max_tokens=1000, config=config).check("short") == "ok"

    def test_yellow_zone(self) -> None:
        """Verify triggering of the yellow safety zone."""
        config = create_mock_config()
        text = " ".join(["word"] * 50)
        assert TokenBudgetManager(max_tokens=100, config=config).check(text) == "yellow"

    def test_red_zone(self) -> None:
        """Verify triggering of the red critical zone."""
        config = create_mock_config()
        text = " ".join(["word"] * 100)
        assert TokenBudgetManager(max_tokens=10, config=config).check(text) == "red"


# ==========================================
# 6. API CLIENT
# ==========================================
class TestAPIClient:
    def test_mock_returns_response(self) -> None:
        """Verify that simulation mode returns predefined mock responses."""
        env = EnvConfig(MOCK=True)
        client = APIClient(env=env, mock=True, config=create_mock_config())
        profile = AgentProfile(
            role="Tester",
            model="gpt",
            provider="mistral",
            thinking="no",
            temperature=0.2,
            max_tokens=100,
        )
        response = client.call("queen", profile, "test")
        assert len(response) > 0

    def test_placeholder_key_uses_mock(self) -> None:
        """Verify that placeholder keys automatically trigger simulation mode."""
        env = EnvConfig(MOCK=False)
        # Manually inject a placeholder cred to simulate invalid state if needed,
        # but APIClient logic handles "mock if key missing".
        client = APIClient(env=env, mock=False, config=create_mock_config())

        # Force mock behavior by not providing real keys in env
        profile = AgentProfile(
            role="Dev",
            model="llama",
            provider="groq",
            thinking="no",
            temperature=0.2,
            max_tokens=100,
        )
        response = client.call("developer", profile, "test")
        assert "Mock response" in response or len(response) > 0


# ==========================================
# 7. ROUTER: RUN_AGENT (Parsing & Execution)
# ==========================================
class TestRouterRunAgent:
    @pytest.fixture
    def router(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> Router:
        """Configured Router instance for core logic testing."""
        # Fix: Mock ROOT in engine and utils properly
        monkeypatch.setattr("agent_core.router_core.engine.ROOT", tmp_project)
        # Import ROOT inside utils is dynamic now, but we mock where it's used
        monkeypatch.setattr("agent_core.router_core.utils.ROOT", tmp_project)

        # Prepare valid config files in tmp_project
        (tmp_project / "agent_orchestrator.json").write_text(create_mock_config().model_dump_json(), encoding="utf-8")

        r = Router(mock=True)
        r.session.path = tmp_project / "agent_context" / "SESSION.md"
        r.tasks.path = tmp_project / "agent_context" / "TASKS.md"
        r.halt.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        return r

    def test_run_queen(self, router: Router) -> None:
        """Verify high-level architect execution."""
        res = router.run_agent("queen", "strategic task", "ANALYSE")
        assert res.get("error") is None

    def test_halted_returns_error(self, router: Router) -> None:
        """Ensure agent execution is blocked when system is halted."""
        router.halt.halt("Global lock")
        res = router.run_agent("queen", "task", "PLANNING")
        assert res["error"] == "HALTED"

    def test_file_write_authorized(self, router: Router, tmp_project: Path) -> None:
        """Verify that authorized file writes are persisted to disk."""
        with patch.object(
            router.api,
            "call",
            return_value='<file_write path="src/new.py">1</file_write>',
        ):
            router.run_agent("developer", "task", "EXECUTING")
            assert (tmp_project / "src/new.py").exists()

    def test_file_write_forbidden(self, router: Router, tmp_project: Path) -> None:
        """Verify that writes to protected system directories are blocked."""
        with patch.object(
            router.api,
            "call",
            return_value='<file_write path="agent_core/evil.py">1</file_write>',
        ):
            router.run_agent("developer", "task", "EXECUTING")
            assert not (tmp_project / "agent_core/evil.py").exists()

    def test_parse_skill_call(self, router: Router) -> None:
        """Verify that skill calls are correctly parsed from agent responses."""
        with (
            patch.object(router, "_execute_skill", return_value=("RESULT:PASS", "")) as mock_exec,
            patch.object(router.api, "call", return_value="<<<SKILL:testing-pro|target:src/>>>"),
        ):
            router.run_agent("developer", "task", "TESTING")
            mock_exec.assert_called_with("testing-pro", {"target": "src/"}, tid=None)

    def test_parse_multiple_skills(self, router: Router) -> None:
        """Verify parsing of multiple skill calls in a single response."""
        with (
            patch.object(router, "_execute_skill", return_value=("RESULT:PASS", "")) as mock_exec,
            patch.object(router.api, "call", return_value="<<<SKILL:a>>><<<SKILL:b>>>"),
        ):
            router.run_agent("developer", "task", "TESTING")
            assert mock_exec.call_count == 2

    def test_parse_session_update(self, router: Router) -> None:
        """Verify parsing of session management commands."""
        with patch.object(router.api, "call", return_value="<<<SESSION:update_context|new ctx>>>"):
            router.run_agent("queen", "task", "ANALYSE")
            assert "AGENT_SUGGESTION: new ctx" in router.session.read()["ACTION_LOG"]

    def test_security_halt_trigger(self, router: Router) -> None:
        """Verify that detected secrets trigger a system-wide HALT."""
        with (
            patch.object(router, "_execute_skill", return_value=("RESULT:SECRET_FOUND", "")),
            patch.object(router.api, "call", return_value="<<<SKILL:security-guard>>>"),
        ):
            res = router.run_agent("auditor", "audit task", "VERIFYING")
            assert res["error"] == "SECURITY_HALT"
            assert router.halt.is_halted()

    def test_skill_error_propagation(self, router: Router) -> None:
        """Verify that skill failures are correctly reported to the state machine."""
        with (
            patch.object(router, "_execute_skill", return_value=("RESULT:ERROR:Crash", "")),
            patch.object(router.api, "call", return_value="<<<SKILL:testing-pro>>>"),
        ):
            res = router.run_agent("developer", "task", "TESTING")
            assert "error" in res


# ==========================================
# 8. ROUTER: RUN_PIPELINE (V1 Local + Edge Cases)
# ==========================================
class TestRouterRunPipeline:
    @pytest.fixture
    def router(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> Router:
        """Configured Router instance for pipeline testing."""
        monkeypatch.setattr("agent_core.router_core.engine.ROOT", tmp_project)
        monkeypatch.setattr("agent_core.router_core.utils.ROOT", tmp_project)

        # Prepare valid config files
        (tmp_project / "agent_orchestrator.json").write_text(create_mock_config().model_dump_json(), encoding="utf-8")

        r = Router(mock=True)
        r.session.path = tmp_project / "agent_context" / "SESSION.md"
        r.tasks.path = tmp_project / "agent_context" / "TASKS.md"
        r.halt.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        r.env.CI_MODE = "local"

        # Disable loop mode for single run test
        r.orch_config.workflow_global.loop_mode.value = False
        return r

    def test_pipeline_success(self, router: Router) -> None:
        """Verify end-to-end success of a local task processing."""

        def mock_agent(agent_name: str, task_desc: str, current_state: str, tid: str | None = None) -> dict:  # noqa: ARG001
            return {"status": "OK"}

        with patch.object(router, "run_agent", side_effect=mock_agent):
            router.run_pipeline()
            assert router.session.read()["STATE"] == "IDLE"
            assert "- [x] TASK-001" in router.tasks.path.read_text(encoding="utf-8")

    def test_pipeline_no_active_tasks(self, router: Router) -> None:
        """Verify pipeline behavior when the task list is empty."""
        router.tasks.path.write_text("# Empty list\n", encoding="utf-8")
        router.run_pipeline()
        assert router.session.read()["STATE"] == "IDLE"

    def test_pipeline_halted_returns_error(self, router: Router) -> None:
        """Verify that pipeline stops immediately if pre-existing HALT is detected."""
        router.halt.halt("Static lock")
        router.run_pipeline()
        assert router.session.read()["STATE"] != "PLANNING"

    def test_pipeline_halt_on_agent_error(self, router: Router) -> None:
        """Verify transition to BLOCKED state upon critical agent failure."""

        def mock_agent(agent_name: str, task_desc: str, current_state: str, tid: str | None = None) -> dict:  # noqa: ARG001
            if agent_name == "developer":
                return {"error": "API_SYSTEM_ERROR"}
            return {"status": "OK"}

        with patch.object(router, "run_agent", side_effect=mock_agent):
            router.run_pipeline()
            assert router.session.read()["STATE"] == "BLOCKED"


# ==========================================
# 9. ROUTER: GHA V2
# ==========================================
class TestRouterGHA:
    @pytest.fixture
    def gha_router(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> Router:
        """Router configured for GitHub Actions cloud stage testing."""
        monkeypatch.setattr("agent_core.router_core.engine.ROOT", tmp_project)
        monkeypatch.setattr("agent_core.router_core.utils.ROOT", tmp_project)

        (tmp_project / "agent_orchestrator.json").write_text(create_mock_config().model_dump_json(), encoding="utf-8")

        r = Router(mock=True)
        r.session.path = tmp_project / "agent_context" / "SESSION.md"
        r.tasks.path = tmp_project / "agent_context" / "TASKS.md"
        r.env.CI_MODE = "github"
        return r

    def test_ci_mode_github_calls_cloud_stage(self, gha_router: Router) -> None:
        """Verify that GHA mode triggers the cloud stage logic."""
        with (
            patch.object(gha_router, "_run_cloud_stage", return_value=True) as mock_cloud,
            patch.object(gha_router, "run_agent", return_value={"status": "OK"}),
        ):
            gha_router.run_pipeline()
            mock_cloud.assert_called_once()

    def test_ci_mode_local_skips_cloud_stage(self, gha_router: Router) -> None:
        """Verify that local mode strictly avoids cloud interaction."""
        gha_router.env.CI_MODE = "local"
        with (
            patch.object(gha_router, "_run_cloud_stage") as mock_cloud,
            patch.object(gha_router, "run_agent", return_value={"status": "OK"}),
        ):
            gha_router.run_pipeline()
            mock_cloud.assert_not_called()

    def test_cloud_stage_success(self, gha_router: Router) -> None:
        """Verify successful cloud push simulation."""
        with (
            patch.object(gha_router, "run_agent", return_value={"status": "OK"}),
            patch.object(gha_router, "_execute_skill", return_value=("RESULT:GHA_PASS", "")),
        ):
            assert gha_router._run_cloud_stage({"id": "001", "description": "test"}) is True

    def test_cloud_stage_failure(self, gha_router: Router) -> None:
        """Verify failure handling in cloud push simulation."""
        with (
            patch.object(gha_router, "run_agent", return_value={"status": "OK"}),
            patch.object(gha_router, "_execute_skill", return_value=("RESULT:GHA_FAIL", "")),
        ):
            assert gha_router._run_cloud_stage({"id": "001", "description": "test"}) is False


# ==========================================
# 10. GLOBAL SYSTEM INTEGRITY TESTS
# ==========================================
def test_uv_path_detection() -> None:
    """Verify that the system can locate the 'uv' binary."""
    from agent_core.router_core.utils import UV_PATH

    assert UV_PATH is not None
    assert "uv" in UV_PATH.lower()


def test_api_client_agnostic_routing() -> None:
    """Verify that the APIClient uses dynamic BASE_URL from environment."""
    env = EnvConfig.model_validate(
        {
            "MISTRAL_API_KEY": "m_key",
            "MISTRAL_BASE_URL": "http://mock.api",
            "MOCK": False,
        }
    )
    config = create_mock_config()

    client = APIClient(env=env, mock=False, config=config)
    profile = AgentProfile(
        role="Tester",
        model="test",
        provider="mistral",
        thinking="no",
        temperature=0.2,
        max_tokens=100,
    )

    with patch.object(client, "_do_call", return_value="agnostic_resp") as mock_call:
        res = client.call("auditor", profile, "prompt")
        assert res == "agnostic_resp"
        # base_url from env config must be passed
        args, _ = mock_call.call_args
        assert args[4] == "http://mock.api"


def test_prompt_builder_full_injection(tmp_project: Path) -> None:
    """Verify that PromptBuilder correctly injects project context from agent_context."""
    builder = PromptBuilder()
    (tmp_project / "agent_context" / "MEMORY.md").write_text("Fact 1", encoding="utf-8")
    (tmp_project / ".claude" / "cache" / "AGENTS.md").write_text("Code Map", encoding="utf-8")

    # We only need to patch ROOT inside utils because PromptBuilder imports it from there
    with patch("agent_core.router_core.utils.ROOT", tmp_project):
        profile = AgentProfile(
            role="Tester",
            model="test",
            provider="test",
            thinking="no",
            temperature=0.2,
            max_tokens=100,
        )
        prompt = builder.build("developer", profile, "task", {"STATE": "IDLE"})
        assert "<project_memory>\nFact 1\n</project_memory>" in prompt
        assert "<codebase_map>\nCode Map\n</codebase_map>" in prompt
        assert "TASK: task" in prompt
