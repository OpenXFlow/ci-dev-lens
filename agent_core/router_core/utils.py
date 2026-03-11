#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/utils.py (v 1.10)
Shared utilities and system configuration loaders.
Fixed: linter rule loading now logs errors if pyproject.toml is missing/empty.
"""

import json
import logging
import shutil
import tomllib  # Standard library in Python 3.12
from pathlib import Path
from typing import cast

import structlog

from .models import AgentsRegistryModel, EnvConfig, OrchestratorConfigModel

# Relative to agent_core/router_core/utils.py, root is 3 levels up
ROOT = Path(__file__).parent.parent.parent.resolve()

# Dynamic detection of 'uv'
UV_PATH = shutil.which("uv") or "uv"

# Updated MOCK Responses
DEFAULT_MOCK_RESPONSES = {
    "queen": (
        "MOCK: Queen planning complete.\n"
        '<file_write path="agent_context/TASKS.md">\n'
        "# Agent-CI-Lens TASKS\n\n"
        "## [USER_QUEUE]\n"
        "- [ ] GOAL-001: Create a Palindrome checker.\n\n"
        "---\n\n"
        "## [AGENT_PROGRESS]\n"
        "- [x] TASK-000: System initialization [attempts: 0]\n"
        "- [ ] TASK-001: Implement Palindrome logic and tests[attempts: 0]\n"
        "</file_write>"
    ),
    "developer": (
        "MOCK: Developer logic generated.\n"
        '<file_write path="src/string_utils.py">\n'
        '"""\nThis module contains string utility functions.\n"""\n\nimport re\n\n'
        'def is_palindrome(text: str) -> bool:\n    """\n    Checks if a given string is a palindrome.\n    """\n'
        "    cleaned_text = re.sub(r'\\W+', '', text).lower()\n"
        "    return cleaned_text == cleaned_text[::-1]\n"
        "</file_write>\n"
        '<file_write path="tests/test_string_utils.py">\n'
        "import pytest\nfrom src.string_utils import is_palindrome\n\n"
        'def test_is_palindrome_simple():\n    assert is_palindrome("madam") is True\n'
        "</file_write>"
    ),
    "pedant": "RESULT:PASS",
    "auditor": "VERIFICATION SUCCESSFUL",
    "git-manager": "RESULT:PUSH_OK",
}


_logger_configured = False


def _setup_logger() -> structlog.BoundLogger:
    """Configures Structlog globally with dual renderers based on CI_MODE."""
    global _logger_configured

    if not _logger_configured:
        env = load_env()

        if env.CI_MODE == "github":
            processors = [
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ]
        else:
            processors = [
                structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
                structlog.processors.add_log_level,
                lambda _, __, ed: {k: v for k, v in ed.items() if k not in ("tid", "internal_level")},
                structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.plain_traceback),
            ]

        structlog.configure(
            processors=processors,  # type: ignore[arg-type]
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        _logger_configured = True

    return cast(structlog.BoundLogger, structlog.get_logger())


def log(msg: str, level: str = "INFO", tid: str | None = None) -> None:
    """Format and print logs to the terminal using structured logging."""
    logger = _setup_logger()
    env = load_env()

    icons = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERROR": "❌", "STATE": "🔄", "PIPELINE": "🚀"}  # noqa: RUF001

    formatted_msg = msg
    if env.CI_MODE != "github":
        task_prefix = ""
        if tid:
            str_tid = str(tid)
            if str_tid.startswith("TASK-") or str_tid.startswith("GOAL-") or str_tid == "START":
                task_prefix = f"[{str_tid}] "
            else:
                task_prefix = f"[TASK-{str_tid}] "

        icon = icons.get(level, "  ")
        formatted_msg = f"{task_prefix}{icon} {msg}"

    bound_logger = logger.bind(tid=str(tid) if tid else None, internal_level=level)

    if level == "ERROR":
        bound_logger.error(formatted_msg)
    elif level == "WARN":
        bound_logger.warning(formatted_msg)
    else:
        bound_logger.info(formatted_msg)


def load_env() -> EnvConfig:
    """Load and parse variables from the .env file."""
    env_path = ROOT / ".env"
    env_dict = {}

    if env_path.exists():
        with env_path.open(encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, _, value = line.partition("=")
                    env_dict[key.strip()] = value.strip()

    return EnvConfig.model_validate(env_dict)


def load_orchestrator_config() -> OrchestratorConfigModel:
    """Load settings from agent_orchestrator.json."""
    config_path = ROOT / "agent_orchestrator.json"

    if not config_path.exists():
        raise FileNotFoundError("Critical: agent_orchestrator.json not found.")

    with config_path.open(encoding="utf-8") as f:
        data = json.load(f)
        return OrchestratorConfigModel.model_validate(data)


def load_agents_registry() -> AgentsRegistryModel:
    """Load agents from .agents/agent_registry.json."""
    registry_path = ROOT / ".agents" / "agent_registry.json"

    if not registry_path.exists():
        raise FileNotFoundError("Critical: .agents/agent_registry.json not found.")

    with registry_path.open(encoding="utf-8") as f:
        data = json.load(f)
        return AgentsRegistryModel.model_validate(data)


def load_linter_rules() -> str:
    """Extracts Ruff and Mypy rules from pyproject.toml for AI context."""
    toml_path = ROOT / "pyproject.toml"
    if not toml_path.exists():
        log("pyproject.toml not found!", "ERROR")
        return "ERROR: pyproject.toml missing."

    with toml_path.open("rb") as f:
        config = tomllib.load(f)

    tool_config = config.get("tool", {})
    ruff = tool_config.get("ruff", {})
    mypy = tool_config.get("mypy", {})

    if not ruff and not mypy:
        log("No linting rules found in pyproject.toml!", "WARN")
        return "WARNING: Linting configuration empty."

    return f"RUFF_CONFIG: {json.dumps(ruff, indent=2)}\nMYPY_CONFIG: {json.dumps(mypy, indent=2)}"


def count_tokens(text: str) -> int:
    """Heuristic token counter."""
    return int(len(text.split()) * 1.5)
