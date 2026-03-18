#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/e2e/test_e2e_palindrome.py - E2E Verification of the Palindrome Flow (v 1.10)
Updated to support max_execution_logs config parameter.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is in sys.path before internal imports
E2E_DIR = Path(__file__).parent
ROOT_DIR = E2E_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agent_core.router_core.engine import Router  # noqa: E402


def test_palindrome_e2e_flow(tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Validates the complete autonomous cycle using reference files.
    """
    # 1. Setup paths
    tasks_path = tmp_project / "agent_context" / "TASKS.md"
    config_path = tmp_project / "agent_orchestrator.json"

    # 2. Inject Initial Requirement
    tasks_path.write_text(
        "# Agent-CI-Lens TASKS\n\n"
        "## [USER_QUEUE]\n"
        "- [ ] GOAL-001: Create a Palindrome checker.\n\n"
        "---\n\n"
        "## [AGENT_PROGRESS]\n"
        "- [x] TASK-000: System initialization[attempts: 0]\n",
        encoding="utf-8",
    )

    # 3. Inject Valid Orchestrator Config
    valid_config = {
        "version": "1.6",
        "workflow_global": {
            "ci_mode": {"value": "local"},
            "loop_mode": {"value": True},
            "loop_delay_seconds": {"value": 0},
            "max_task_attempts": {"value": 3},
            "max_continuous_tasks": {"value": 20},
        },
        "workflow_local": {
            "STRATEGY": {"active": {"value": True}, "max_retries": {"value": 1}, "requires_llm": {"value": True}},
            "EXECUTING": {"active": {"value": True}, "max_retries": {"value": 1}, "requires_llm": {"value": True}},
            "LINTING": {"active": {"value": True}, "max_retries": {"value": 1}, "requires_llm": {"value": False}},
            "TESTING": {"active": {"value": True}, "max_retries": {"value": 1}, "requires_llm": {"value": False}},
            "VERIFYING": {"active": {"value": True}, "max_retries": {"value": 1}, "requires_llm": {"value": True}},
            "VCS_DELIVERY": {"active": {"value": False}, "max_retries": {"value": 1}, "requires_llm": {"value": False}},
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
            "enabled": {"value": True},
            "db_path": {"value": ":memory:"},
            "max_reflections": {"value": 100},
            "max_execution_logs": {"value": 2000},
            "fts_result_limit": {"value": 10},
            "vacuum_on_purge": {"value": False},
        },
        "logging": {"show_task_id": {"value": True}, "verbosity": {"value": "INFO"}},
    }
    config_path.write_text(json.dumps(valid_config), encoding="utf-8")

    # 4. Mock Kernel Environment
    import agent_core.router_core.engine as engine_mod
    import agent_core.router_core.managers as managers_mod
    import agent_core.router_core.utils as utils_mod

    monkeypatch.setattr(engine_mod, "ROOT", tmp_project)
    monkeypatch.setattr(managers_mod, "ROOT", tmp_project)
    monkeypatch.setattr(utils_mod, "ROOT", tmp_project)

    # 5. Execute Pipeline (Simulation Mode)
    router = Router(mock=True)
    router.run_pipeline()

    # 6. Verification
    tasks_content = tasks_path.read_text(encoding="utf-8")
    assert "- [x] GOAL-001" in tasks_content
