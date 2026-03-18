#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_vcs_flow.py - Unit tests for VCS integration & Engine Delivery logic.
(v 1.26) Added max_execution_logs to mock config.
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
from agent_core.router_core.models import EnvConfig, OrchestratorConfigModel


@pytest.fixture(autouse=True)
def fast_tests_no_sleep(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Globally disable time.sleep and stamina retries during tests."""
    monkeypatch.setattr(time, "sleep", lambda _x: None)
    stamina.set_active(False)
    yield
    stamina.set_active(True)


def create_mock_config() -> OrchestratorConfigModel:
    """Creates a v1.6 compliant mock configuration."""
    return OrchestratorConfigModel.model_validate(
        {
            "version": "1.6",
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
            "memory_engine": {
                "enabled": {"value": False},
                "db_path": {"value": ":memory:"},
                "max_reflections": {"value": 100},
                "max_execution_logs": {"value": 2000},
                "fts_result_limit": {"value": 10},
                "vacuum_on_purge": {"value": False},
            },
            "logging": {"show_task_id": {"value": True}, "verbosity": {"value": "INFO"}},
        }
    )


class TestGitHubClient:
    @pytest.fixture
    def gh_client(self) -> GitHubAPIClient:
        env = EnvConfig(GITHUB_TOKEN="tok", GITHUB_REPOSITORY="u/r")  # noqa: S106
        cfg = create_mock_config()
        return GitHubAPIClient(env, cfg)

    def test_should_retry_logic(self, gh_client: GitHubAPIClient) -> None:
        err_429 = httpx.HTTPStatusError("Limit", request=MagicMock(), response=MagicMock(status_code=429))
        assert gh_client._should_retry(err_429) is True

        err_503 = httpx.HTTPStatusError("Down", request=MagicMock(), response=MagicMock(status_code=503))
        assert gh_client._should_retry(err_503) is True

        err_401 = httpx.HTTPStatusError("Auth", request=MagicMock(), response=MagicMock(status_code=401))
        assert gh_client._should_retry(err_401) is False

    def test_create_pr_payload(self, gh_client: GitHubAPIClient) -> None:
        with patch.object(gh_client, "_request") as mock_req:
            mock_req.side_effect = [
                {"default_branch": "main", "full_name": "u/r", "html_url": "http://repo"},
                {
                    "number": 1,
                    "html_url": "url",
                    "state": "open",
                    "title": "t",
                    "user": {"login": "u", "id": 1},
                },
            ]
            gh_client.create_pull_request("feat/1", "Title", "Body")

            call_args = mock_req.call_args_list[1]
            payload = call_args[1]["json_data"]
            assert payload["head"] == "feat/1"
            assert payload["base"] == "main"


class TestRouterVCSFlow:
    @pytest.fixture
    def router(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> Router:
        monkeypatch.setattr("agent_core.router_core.engine.ROOT", tmp_project)
        monkeypatch.setattr("agent_core.router_core.utils.ROOT", tmp_project)

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
        def mock_agent(
            _agent_name: str, _task_desc: str, _current_state: str, _tid: str | None = None, **_kwargs: Any
        ) -> dict[str, str]:
            return {"status": "OK"}

        with (
            patch.object(router, "run_agent", side_effect=mock_agent),
            patch.object(router, "_run_vcs_delivery", return_value=True),
        ):
            router.run_pipeline()
            assert router.session.read()["STATE"] == "IDLE"

    def test_pipeline_halt_on_agent_error(self, router: Router) -> None:
        def mock_agent(
            _agent_name: str, _task_desc: str, _current_state: str, _tid: str | None = None, **_kwargs: Any
        ) -> dict[str, str]:
            if _agent_name == "developer":
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

    def test_master_kill_switch_active_false(self, router: Router) -> None:
        """Verify that turning off VCS_DELIVERY completely disables Git actions in sync."""
        router.orch_config.workflow_local["VCS_DELIVERY"].active.value = False
        router.git.is_dirty = MagicMock(return_value=True)
        router.git.commit_all = MagicMock()

        router._sync_vcs_state("001")

        router.git.commit_all.assert_not_called()

    def test_eager_branching_goal_based(self, router: Router) -> None:
        """Verify that branch is created based on active GOAL, not active TASK."""
        router.tasks.get_active_tasks = MagicMock(
            return_value=[{"id": "002", "description": "task 2", "is_synthetic": False}]
        )
        router.tasks.get_current_goal_id = MagicMock(return_value="001")

        def mock_agent(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            return {"status": "OK"}

        with patch.object(router, "run_agent", side_effect=mock_agent):
            router._run_vcs_delivery = MagicMock(return_value=True)
            router.git.ensure_branch = MagicMock()
            router.run_pipeline()
            router.git.ensure_branch.assert_called_with("feat/001")

    def test_vcs_pr_already_exists_422(self, router: Router) -> None:
        """Verify that 422 error during PR creation doesn't crash the pipeline."""
        router.orch_config.vcs_control.mode.value = "github"
        router.tasks.get_current_goal_id = MagicMock(return_value="001")

        with patch("agent_core.router_core.engine.GitHubAPIClient") as mock_gh_cls:
            mock_gh = mock_gh_cls.return_value
            mock_gh.create_pull_request.side_effect = Exception("422 Unprocessable Entity")
            mock_gh.poll_workflow_status.return_value = MagicMock(conclusion="success")

            result = router._run_vcs_delivery("001")
            assert result is True

    def test_sync_vcs_state_no_push_on_local(self, router: Router) -> None:
        """Verify that local_git mode commits but does NOT push."""
        router.orch_config.vcs_control.mode.value = "local_git"
        router.orch_config.workflow_local["VCS_DELIVERY"].active.value = True
        router.git.is_dirty = MagicMock(return_value=True)
        router.git.commit_all = MagicMock()
        router.git.push = MagicMock()

        router._sync_vcs_state("001")
        router.git.commit_all.assert_called_once()
        router.git.push.assert_not_called()

    def test_gha_failure_rollback(self, router: Router) -> None:
        """Verify that GHA failure reverts the EXECUTING success flag."""
        router.tasks.get_active_tasks = MagicMock(
            return_value=[{"id": "001", "description": "task", "is_synthetic": False}]
        )

        def mock_agent(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            return {"status": "OK"}

        with patch.object(router, "run_agent", side_effect=mock_agent):
            router._run_vcs_delivery = MagicMock(return_value=False)

            for stage in ["ANALYSE", "PLANNING", "LINTING", "TESTING", "VERIFYING"]:
                if stage in router.orch_config.workflow_local:
                    router.orch_config.workflow_local[stage].active.value = False
            router.orch_config.workflow_local["EXECUTING"].active.value = True
            router.orch_config.workflow_local["VCS_DELIVERY"].active.value = True

            router.orch_config.workflow_local["VCS_DELIVERY"].max_retries.value = 2

            s = router.session.read()
            s["ACTION_LOG"] = "STAGE_SUCCESS:EXECUTING:001"
            router.session._write_all(s)

            router.run_pipeline()

            log_content = router.session.read()["ACTION_LOG"]
            assert "REVERTED:EXECUTING:001" in log_content
            assert "STAGE_FAIL:VCS_DELIVERY:001" in log_content
