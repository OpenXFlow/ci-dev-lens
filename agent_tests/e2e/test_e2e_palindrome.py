#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/e2e/test_e2e_palindrome.py - E2E Verification of the Palindrome Flow (v 1.2)
"""

import json
import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
E2E_DIR = Path(__file__).parent
ROOT_DIR = E2E_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agent_core.router_core.engine import Router

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
        "- [x] TASK-000: System initialization [attempts: 0]\n",
        encoding="utf-8"
    )

    # 3. Inject Valid Orchestrator Config with Active Stages
    valid_config = {
        "version": "1.2",
        "workflow_global": {
            "ci_mode": {"value": "local"},
            "loop_mode": {"value": True},
            "loop_delay_seconds": {"value": 0},
            "max_task_attempts": {"value": 3},
            "max_continuous_tasks": {"value": 20}
        },
        "workflow_local": {
            "ANALYSE": {"active": {"value": True}, "max_retries": {"value": 3}, "pause_after": {"value": False}},
            "PLANNING": {"active": {"value": True}, "max_retries": {"value": 3}},
            "EXECUTING": {"active": {"value": True}, "max_retries": {"value": 3}},
            "LINTING": {"active": {"value": True}, "max_retries": {"value": 5}},
            "TESTING": {"active": {"value": True}, "max_retries": {"value": 3}},
            "VERIFYING": {"active": {"value": True}, "max_retries": {"value": 3}}
        },
        "resilience": {
            "smart_fallback": {"value": False},
            "fallback_matrix": {}
        },
        "memory_management": {
            "yellow_zone_threshold": {"value": 0.7},
            "red_zone_threshold": {"value": 0.9}
        },
        "logging": {
            "show_task_id": {"value": True},
            "verbosity": {"value": "INFO"}
        }
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
    
    # A. Goal status
    tasks_content = tasks_path.read_text(encoding="utf-8")
    assert "- [x] GOAL-001" in tasks_content, "Goal should be auto-closed"

    # B. File existence
    gen_src = tmp_project / "src" / "string_utils.py"
    gen_test = tmp_project / "tests" / "test_string_utils.py"
    
    assert gen_src.exists(), "Source file was not generated"
    assert gen_test.exists(), "Test file was not generated"

    # C. Logic Content Verification
    generated_logic = gen_src.read_text(encoding="utf-8")
    assert "def is_palindrome" in generated_logic
    assert "re.sub" in generated_logic or "char.isalnum" in generated_logic

    # D. Bimetric Shield Verification
    session_path = tmp_project / "agent_context" / "SESSION.md"
    session_content = session_path.read_text(encoding="utf-8")
    assert "## [USER_SECTION]" in session_content
    assert "## [AGENT_SECTION]" in session_content
    assert "### [FEEDBACK]" in session_content