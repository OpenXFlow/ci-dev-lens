#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/utils.py - Shared utilities and loaders (v 1.3 Pydantic)."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from .models import AgentsRegistryModel, EnvConfig, OrchestratorConfigModel

# Relative to agent_core/router_core/utils.py, root is 3 levels up
ROOT = Path(__file__).parent.parent.parent.resolve()

# Dynamic detection of 'uv'
UV_PATH = shutil.which("uv") or "uv"

DEFAULT_MOCK_RESPONSES = {
    "queen": "MOCK: Queen plan generated.",
    "developer": "MOCK: Developer code written.",
    "pedant": "RESULT:PASS",
    "auditor": "VERIFICATION SUCCESSFUL",
    "git-manager": "RESULT:PUSH_OK",
}


def log(msg: str, level: str = "INFO", tid: str | None = None) -> None:
    """Format and print logs to the terminal."""
    timestamp = datetime.now().strftime("%H:%M:%S")

    icons = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERROR": "❌", "STATE": "🔄", "PIPELINE": "🚀"}  # noqa: RUF001

    task_prefix = ""
    if tid:
        str_tid = str(tid)
        if str_tid.startswith("TASK-") or str_tid.startswith("GOAL-") or str_tid == "START":
            task_prefix = f"[{str_tid}] "
        else:
            task_prefix = f"[TASK-{str_tid}] "

    print(f"[{timestamp}] {task_prefix}{icons.get(level, '  ')} {msg}")


def load_env() -> EnvConfig:
    """Load and parse variables from the .env file using Pydantic.

    Returns:
        EnvConfig object with dynamic credential parsing.
    """
    env_path = ROOT / ".env"
    env_dict = {}

    if env_path.exists():
        with env_path.open(encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, _, value = line.partition("=")
                    env_dict[key.strip()] = value.strip()

    # Pydantic handles validation, defaults, and credential parsing
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


def count_tokens(text: str) -> int:
    """Heuristic token counter."""
    return int(len(text.split()) * 1.5)
