#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_router.py - Full unit tests for Router Engine (v 1.20).
Fixed formatting assertions (added missing spaces in expected markdown strings).
"""

import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, create_autospec, patch

import httpx
import pytest
import stamina  # type: ignore

from agent_core.router_core.engine import Router
from agent_core.router_core.git_local import GitLocalManager
from agent_core.router_core.github_client import GitHubAPIClient
from agent_core.router_core.llm import APIClient, TokenBudgetManager
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
def fast_tests_no_sleep(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Globally disable time.sleep and stamina retries during tests."""
    monkeypatch.setattr(time, "sleep", lambda _x: None)
    # Force stamina to deactivate retries during tests to speed up execution
    stamina.set_active(False)
    yield
    stamina.set_active(True)


def create_mock_config() -> OrchestratorConfigModel:
    """Creates a v1.4 compliant mock configuration."""
    return OrchestratorConfigModel.model_validate(
        {
            "version": "1.4",
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
                "VCS_DELIVERY": {"active": {"value": True}, "max_retries": {"value": 1}},
            },
            "vcs_control": {
                "mode": {"value": "local_git"},
                "github_settings": {
                    "auto_push": {"value": True},
                    "auto_pr": {"value": True},
                    "watch_gha": {"value": True},
                    "gha_timeout_minutes": {"value": 10},
                },
                "local_git_settings": {"auto_commit": {"value": True}, "branch_per_goal": {"value": True}},
                "local_act_settings": {
                    "workflow_file": {"value": "ci.yml"},
                    "platform": {"value": "ubuntu-latest=catthehacker/ubuntu:act-22.04"},
                },
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
        assert count_tokens("") == 0

    def test_single_word(self) -> None:
        assert count_tokens("hello") >= 1

    def test_longer_text(self) -> None:
        assert count_tokens("hello world foo bar") > count_tokens("hello")


# ==========================================
# 2. SESSION MANAGER
# ==========================================
class TestSessionManager:
    def test_read_existing_session(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        data = sm.read()
        assert data["STATE"] == "IDLE"
        assert "Initial setup" in data["ACTION_LOG"]

    def test_write_state(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_state("EXECUTING")
        assert sm.read()["STATE"] == "EXECUTING"

    def test_write_context(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_context("New Context")
        assert sm.read()["CONTEXT"] == "New Context"

    def test_write_feedback(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_feedback("System Error")
        assert sm.read()["FEEDBACK"] == "System Error"

    def test_add_workspace(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.add_workspace("src/test.py")
        assert "src/test.py" in sm.read()["WORKSPACE"]

    def test_write_action_log(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_action_log("Log Entry")
        assert "Log Entry" in sm.read()["ACTION_LOG"]

    def test_schema_integrity(self, tmp_project: Path) -> None:
        sm = SessionManager()
        sm.path = tmp_project / "agent_context" / "SESSION.md"
        sm.write_state("PLANNING")
        content = sm.path.read_text(encoding="utf-8")
        # ARCHITECT FIX: Corrected assertions to expect a space after ## and ###
        assert "## [USER_SECTION]" in content
        assert "## [AGENT_SECTION]" in content
        assert "### [FEEDBACK]" in content


# ==========================================
# 3. TASKS MANAGER
# ==========================================
class TestTasksManager:
    def test_get_active_tasks(self, tmp_project: Path) -> None:
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tasks = tm.get_active_tasks()
        assert len(tasks) >= 1
        assert tasks[0]["id"] == "001"

    def test_increment_attempts(self, tmp_project: Path) -> None:
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        val = tm.increment_attempts("001", "Err")
        assert val == 1
        assert tm.get_active_tasks()[0]["attempts"] == 1

    def test_blocked_status(self, tmp_project: Path) -> None:
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tm.max_attempts = 1
        tm.increment_attempts("001", "Fatal")
        assert "[BLOCKED]" in tm.path.read_text()
        assert "Zlyhalo: Fatal" in tm.path.read_text()

    def test_mark_completed(self, tmp_project: Path) -> None:
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tm.mark_completed("001")
        # ARCHITECT FIX: Corrected assertion to expect a space after the dash
        assert "- [x] TASK-001" in tm.path.read_text()

    def test_mark_goal_completed(self, tmp_project: Path) -> None:
        tm = TasksManager()
        tm.path = tmp_project / "agent_context" / "TASKS.md"
        tm.mark_goal_completed("001")
        assert "- [x] GOAL-001" in tm.path.read_text()


# ==========================================
# 4. HALT MANAGER
# ==========================================
class TestHaltManager:
    def test_initial_state(self, tmp_project: Path) -> None:
        hm = HaltManager()
        hm.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        assert not hm.is_halted()

    def test_halt_activation(self, tmp_project: Path) -> None:
        hm = HaltManager()
        hm.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        hm.halt("Stop")
        assert hm.is_halted()
        assert "Stop" in hm.flag_path.read_text()


# ==========================================
# 5. TOKEN BUDGET MANAGER
# ==========================================
class TestTokenBudgetManager:
    def test_ok_zone(self) -> None:
        cfg = create_mock_config()
        tbm = TokenBudgetManager(1000, cfg)
        assert tbm.check("short") == "ok"

    def test_yellow_zone(self) -> None:
        cfg = create_mock_config()
        tbm = TokenBudgetManager(100, cfg)
        # 50 words * 1.5 = 75 tokens (>= 70 yellow, < 90 red)
        assert tbm.check("word " * 50) == "yellow"

    def test_red_zone(self) -> None:
        cfg = create_mock_config()
        tbm = TokenBudgetManager(50, cfg)
        # 40 words * 1.5 = 60 tokens (> 45 red)
        assert tbm.check("word " * 40) == "red"


# ==========================================
# 6. API CLIENT
# ==========================================
class TestAPIClient:
    def test_mock_response(self) -> None:
        env = EnvConfig(MOCK=True)
        client = APIClient(env, True, create_mock_config())
        profile = AgentProfile(role="r", model="m", provider="mistral", thinking="n", temperature=0, max_tokens=100)
        res = client.call("queen", profile, "p")
        assert "MOCK" in res

    def test_placeholder_key_fallback(self) -> None:
        env = EnvConfig(MOCK=False)
        client = APIClient(env, False, create_mock_config())
        profile = AgentProfile(role="r", model="m", provider="groq", thinking="n", temperature=0, max_tokens=10)
        res = client.call("developer", profile, "p")
        assert "MOCK" in res or "Mock response" in res


# ==========================================
# 7. GIT LOCAL MANAGER (Native)
# ==========================================
class TestGitLocal:
    @pytest.fixture
    def git(self, tmp_project: Path) -> GitLocalManager:
        (tmp_project / ".git").mkdir()
        return GitLocalManager(working_dir=tmp_project)

    def test_is_dirty_clean(self, git: GitLocalManager) -> None:
        with patch.object(git, "_run", return_value=""):
            assert git.is_dirty() is False

    def test_is_dirty_changed(self, git: GitLocalManager) -> None:
        with patch.object(git, "_run", return_value="M modified_file.py"):
            assert git.is_dirty() is True

    def test_ensure_branch_existing(self, git: GitLocalManager) -> None:
        with patch.object(git, "get_current_branch", return_value="main"), patch.object(git, "_run") as mock_run:
            git.ensure_branch("main")
            mock_run.assert_not_called()

    @patch("agent_core.router_core.git_local.subprocess.run")
    def test_ensure_branch_create(self, mock_sub: MagicMock, git: GitLocalManager) -> None:
        """Verifies branch creation occurs when subprocess signals branch does not exist."""
        with patch.object(git, "get_current_branch", return_value="main"), patch.object(git, "_run") as mock_run:
            # Simulate git show-ref returning non-zero (branch not found)
            mock_sub.return_value.returncode = 1
            git.ensure_branch("feat/new")

            # Verify it attempts to checkout and create (-b)
            mock_run.assert_called_once_with(["checkout", "-b", "feat/new"])


# ==========================================
# 8. GITHUB CLIENT (Cloud)
# ==========================================
class TestGitHubClient:
    @pytest.fixture
    def gh_client(self) -> GitHubAPIClient:
        # S106: Hardcoded password allowed in tests
        env = EnvConfig(GITHUB_TOKEN="tok", GITHUB_REPOSITORY="u/r")  # noqa: S106
        cfg = create_mock_config()
        return GitHubAPIClient(env, cfg)

    def test_should_retry_logic(self, gh_client: GitHubAPIClient) -> None:
        # Rate limit
        err_429 = httpx.HTTPStatusError("Limit", request=MagicMock(), response=MagicMock(status_code=429))
        assert gh_client._should_retry(err_429) is True

        # Server error
        err_503 = httpx.HTTPStatusError("Down", request=MagicMock(), response=MagicMock(status_code=503))
        assert gh_client._should_retry(err_503) is True

        # Auth error (should not retry)
        err_401 = httpx.HTTPStatusError("Auth", request=MagicMock(), response=MagicMock(status_code=401))
        assert gh_client._should_retry(err_401) is False

    def test_create_pr_payload(self, gh_client: GitHubAPIClient) -> None:
        with patch.object(gh_client, "_request") as mock_req:
            mock_req.side_effect = [
                {"default_branch": "main", "full_name": "u/r", "html_url": "http://repo"},  # get_repo_info
                {
                    "number": 1,
                    "html_url": "url",
                    "state": "open",
                    "title": "t",
                    "user": {"login": "u", "id": 1},
                },  # PR response
            ]
            gh_client.create_pull_request("feat/1", "Title", "Body")

            # Verify payload
            call_args = mock_req.call_args_list[1]
            payload = call_args[1]["json_data"]
            assert payload["head"] == "feat/1"
            assert payload["base"] == "main"


# ==========================================
# 9. ROUTER: RUN_AGENT
# ==========================================
class TestRouterRunAgent:
    @pytest.fixture
    def router(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> Router:
        monkeypatch.setattr("agent_core.router_core.engine.ROOT", tmp_project)
        monkeypatch.setattr("agent_core.router_core.utils.ROOT", tmp_project)
        from agent_core.router_core.git_local import GitLocalManager

        mock_git = create_autospec(GitLocalManager)
        monkeypatch.setattr("agent_core.router_core.engine.GitLocalManager", lambda: mock_git)
        (tmp_project / "agent_orchestrator.json").write_text(create_mock_config().model_dump_json())
        r = Router(mock=True)
        r.session.path = tmp_project / "agent_context" / "SESSION.md"
        r.tasks.path = tmp_project / "agent_context" / "TASKS.md"
        r.halt.flag_path = tmp_project / ".claude" / "cache" / "HALT.flag"
        return r

    def test_run_queen_structured(self, router: Router) -> None:
        res = router.run_agent("queen", "task", "PLANNING")
        assert res.get("status") == "OK"

    def test_run_developer_legacy(self, router: Router) -> None:
        # Developer is not in RESPONSE_MODELS yet, so it uses XML parsing
        with patch.object(router.api, "call", return_value='<file_write path="src/main.py">print()</file_write>'):
            res = router.run_agent("developer", "impl", "EXECUTING")
            assert res["status"] == "OK"

    def test_halted_error(self, router: Router) -> None:
        router.halt.halt("Locked")
        res = router.run_agent("queen", "task", "PLANNING")
        assert res["error"] == "HALTED"

    def test_file_write_security(self, router: Router, tmp_project: Path) -> None:
        with patch.object(router.api, "call", return_value='<file_write path="agent_core/hack.py">1</file_write>'):
            router.run_agent("developer", "task", "EXECUTING")
            assert not (tmp_project / "agent_core/hack.py").exists()

    def test_skill_execution(self, router: Router) -> None:
        with (
            patch.object(router, "_run_skill_process", return_value=("RESULT:PASS", "ok")),
            patch.object(router.api, "call", return_value="<<<SKILL:testing-pro>>>"),
        ):
            res = router.run_agent("developer", "task", "EXECUTING")
            assert res["status"] == "OK"

    def test_security_halt(self, router: Router) -> None:
        with (
            patch.object(router, "_run_skill_process", return_value=("RESULT:SECRET_FOUND", "bad")),
            patch.object(router.api, "call", return_value="<<<SKILL:security-guard>>>"),
        ):
            res = router.run_agent("auditor", "task", "VERIFYING")
            assert res.get("error") == "SECURITY_HALT"
            assert router.halt.is_halted()

    def test_parse_multiple_skills(self, router: Router) -> None:
        with (
            patch.object(router, "_run_skill_process", return_value=("RESULT:PASS", "ok")) as mock_run,
            patch.object(router.api, "call", return_value="<<<SKILL:a>>><<<SKILL:b>>>"),
        ):
            router.run_agent("developer", "task", "EXECUTING")
            assert mock_run.call_count == 2


# ==========================================
# 10. ROUTER RUN PIPELINE & VCS
# ==========================================
class TestRouterVCSFlow:
    @pytest.fixture
    def router(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> Router:
        monkeypatch.setattr("agent_core.router_core.engine.ROOT", tmp_project)
        monkeypatch.setattr("agent_core.router_core.utils.ROOT", tmp_project)
        from agent_core.router_core.git_local import GitLocalManager

        mock_git = create_autospec(GitLocalManager)
        monkeypatch.setattr("agent_core.router_core.engine.GitLocalManager", lambda: mock_git)
        (tmp_project / "agent_orchestrator.json").write_text(create_mock_config().model_dump_json())
        r = Router(mock=True)
        r.session.path = tmp_project / "agent_context" / "SESSION.md"
        r.tasks.path = tmp_project / "agent_context" / "TASKS.md"
        r.env.CI_MODE = "local"
        r.orch_config.workflow_global.loop_mode.value = False
        return r

    def test_pipeline_success(self, router: Router) -> None:
        def mock_agent(agent_name: str, task_desc: str, current_state: str, tid: str | None = None) -> dict:  # noqa: ARG001
            return {"status": "OK"}

        with (
            patch.object(router, "run_agent", side_effect=mock_agent),
            patch.object(router, "_run_vcs_delivery", return_value=True),
        ):
            router.run_pipeline()
            assert router.session.read()["STATE"] == "IDLE"

    def test_pipeline_halt_on_agent_error(self, router: Router) -> None:
        def mock_agent(agent_name: str, task_desc: str, current_state: str, tid: str | None = None) -> dict:  # noqa: ARG001
            if agent_name == "developer":
                return {"error": "API_SYSTEM_ERROR"}
            return {"status": "OK"}

        with patch.object(router, "run_agent", side_effect=mock_agent):
            router.run_pipeline()
            assert router.session.read()["STATE"] == "BLOCKED"

    def test_vcs_local_git_call(self, router: Router) -> None:
        router.orch_config.vcs_control.mode.value = "local_git"
        assert router._run_vcs_delivery("001") is True
        cast(Any, router.git).ensure_branch.assert_called()

    def test_vcs_github_mock_call(self, router: Router) -> None:
        router.orch_config.vcs_control.mode.value = "github"
        with patch("agent_core.router_core.engine.GitHubAPIClient") as mock_gh_cls:
            mock_gh = mock_gh_cls.return_value
            mock_gh.create_pull_request.return_value = MagicMock(html_url="http://pr")
            mock_gh.poll_workflow_status.return_value = MagicMock(conclusion="success")
            assert router._run_vcs_delivery("001") is True
