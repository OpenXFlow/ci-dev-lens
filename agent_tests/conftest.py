#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/conftest.py - Shared pytest fixtures for Agent-CI-Lens kernel (v 1.4).
Updated for Model 5.3 file structure (Pydantic).
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Ensure the project root is in sys.path to allow imports from agent_core
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))


# ==========================================
# MAIN FIXTURE — complete project structure
# ==========================================
@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """
    Creates a complete temporary project structure using Model 5.3 naming conventions.
    Used by validator, indexer, router, and skill tests.
    """
    # System directories
    (tmp_path / ".claude" / "cache").mkdir(parents=True)
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / ".agents").mkdir(parents=True)

    # Model 5.2/5.3 directories
    (tmp_path / "agent_context").mkdir(parents=True)
    (tmp_path / "agent_core" / "router_core").mkdir(parents=True)
    (tmp_path / "agent_tests").mkdir(parents=True)
    (tmp_path / "agent_native").mkdir(parents=True)

    # Application directories
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / "tests").mkdir(parents=True)

    # Mock agent_registry.json (NEW NAME)
    agents_config = {
        "version": "1.0",
        "profiles": {
            "queen": {
                "role": "Orchestrator",
                "model": "mistral-large-latest",
                "provider": "mistral",
                "thinking": "required",
                "temperature": 0.2,
                "max_tokens": 8000,
                "allowed_skills": ["context-compressor"],
            },
            "developer": {
                "role": "Implementer",
                "model": "llama-3.3-70b-versatile",
                "provider": "groq",
                "thinking": "pre-skill",
                "temperature": 0.1,
                "max_tokens": 4000,
                "allowed_skills": ["testing-pro"],
            },
            "pedant": {
                "role": "Linter",
                "model": "llama-3.1-8b-instant",
                "provider": "groq",
                "thinking": "disabled",
                "temperature": 0.0,
                "max_tokens": 1000,
                "allowed_skills": ["quality-gate"],
            },
            "auditor": {
                "role": "Reviewer",
                "model": "codestral-latest",
                "provider": "mistral",
                "thinking": "disabled",
                "temperature": 0.0,
                "max_tokens": 2000,
                "allowed_skills": ["func-audit"],
            },
        },
    }
    (tmp_path / ".agents" / "agent_registry.json").write_text(json.dumps(agents_config), encoding="utf-8")

    # Mock SESSION.md in agent_context
    session_content = (
        "# Agent-CI-Lens SESSION\n\n"
        "## [USER_SECTION]\n"
        "### [CONTEXT]\nTest context for kernel verification.\n\n"
        "### [WORKSPACE]\n\n---\n\n"
        "## [AGENT_SECTION]\n"
        "### [STATE]\nIDLE\n\n"
        "### [FEEDBACK]\n\n"
        "### [ACTION_LOG]\n"
        "[10:00] Initial setup complete.\n"
        "[10:01] Agent queen finished. Skills: 0\n"
    )
    (tmp_path / "agent_context" / "SESSION.md").write_text(session_content, encoding="utf-8")

    # Mock TASKS.md in agent_context
    tasks_content = (
        "# Agent-CI-Lens TASKS\n\n"
        "## [USER_QUEUE]\n"
        "- [ ] GOAL-001: Unit test the new structure\n\n"
        "---\n\n"
        "## [AGENT_PROGRESS]\n"
        "- [ ] TASK-001: Verification of paths [attempts: 0]\n"
        "- [x] TASK-000: Initialization [attempts: 0]\n"
    )
    (tmp_path / "agent_context" / "TASKS.md").write_text(tasks_content, encoding="utf-8")

    # Mock MEMORY.md
    (tmp_path / "agent_context" / "MEMORY.md").write_text("# Long-Term Memory\nTest data.", encoding="utf-8")

    # Basic project files
    (tmp_path / "CLAUDE.md").touch()
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "agent_orchestrator.json").write_text("{}", encoding="utf-8")  # NEW NAME
    (tmp_path / ".python-version").write_text("3.12", encoding="utf-8")

    # Mock .env with agnostic keys
    env_content = (
        "GROQ_API_KEY=gsk_MOCK_KEY\n"
        "GROQ_BASE_URL=https://api.groq.com/openai/v1/chat/completions\n"
        "MISTRAL_API_KEY=MIST_MOCK_KEY\n"
        "MISTRAL_BASE_URL=https://api.mistral.ai/v1/chat/completions\n"
        "MOCK=true\n"
    )
    (tmp_path / ".env").write_text(env_content, encoding="utf-8")

    return tmp_path


# ==========================================
# FIXTURE — source files for indexer tests
# ==========================================
@pytest.fixture
def tmp_src(tmp_path: Path) -> Path:
    """
    Creates a temporary src/ directory with sample Python files for indexer tests.
    """
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "__init__.py").touch()

    # Sample calculator file
    calc_code = (
        "def add(a: int, b: int) -> int:\n"
        '    """Adds two numbers."""\n'
        "    return a + b\n\n"
        "class Calculator:\n"
        '    """Simple Calculator class."""\n'
        "    def multiply(self, a: int, b: int) -> int:\n"
        "        return a * b\n"
    )
    (src / "calculator.py").write_text(calc_code, encoding="utf-8")

    # Intentionally broken file for parser testing
    (src / "broken.py").write_text("def invalid_syntax(\n", encoding="utf-8")

    # Empty file
    (src / "empty.py").write_text("", encoding="utf-8")

    return tmp_path


# ==========================================
# FIXTURE — router factory helper
# ==========================================
@pytest.fixture
def make_router() -> Callable[..., Any]:
    """
    Factory fixture — returns a function to create a Router configured for the tmp project.

    Usage:
        def test_logic(make_router: Callable[..., Any], tmp_project: Path) -> None:
            router = make_router(tmp_project)
    """

    def _make_router(project_path: Path, mock: bool = True) -> Any:
        # We must import inside the fixture to reflect current sys.path
        from agent_core.router_core.engine import Router
        from agent_core.router_core.managers import (
            HaltManager,
            SessionManager,
            TasksManager,
        )

        # Initialize the router with mock mode
        router = Router(mock=mock)

        # Override manager paths to point to the temporary test project
        router.session = SessionManager()
        router.session.path = project_path / "agent_context" / "SESSION.md"

        router.tasks = TasksManager()
        router.tasks.path = project_path / "agent_context" / "TASKS.md"

        router.halt = HaltManager()
        router.halt.flag_path = project_path / ".claude" / "cache" / "HALT.flag"

        # Load the mock config from the tmp project (NEW NAME)
        router.agent_registry = json.loads(
            (project_path / ".agents" / "agent_registry.json").read_text(encoding="utf-8")
        )
        return router

    return _make_router
