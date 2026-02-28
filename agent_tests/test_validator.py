#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_validator.py - Unit tests for the System Validator (v 1.6 Pydantic).
Fixtures are defined in conftest.py
"""

import json
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

import agent_core.validator as val


@pytest.fixture(autouse=True)
def setup_validator(monkeypatch: pytest.MonkeyPatch, tmp_project: Path) -> Generator[None, None, None]:
    """Prepare fresh state and redirect root to temporary project."""
    monkeypatch.setattr(val, "ROOT", tmp_project)

    # Dynamically mock ROOT in the exact module where utils were loaded from
    # (resolves dual-import issues due to validator's try/except import block)
    utils_module_name = val.load_agents_registry.__module__
    monkeypatch.setattr(sys.modules[utils_module_name], "ROOT", tmp_project)

    val.ERRORS.clear()
    val.WARNINGS.clear()
    yield
    val.ERRORS.clear()
    val.WARNINGS.clear()


# ==========================================
# TESTS: Config Validation Logic
# ==========================================
class TestConfigValidation:
    def test_missing_config_file(self, tmp_project: Path) -> None:
        """Verify that missing config file creates a hard error."""
        # Ensure the correct file is missing
        (tmp_project / "agent_orchestrator.json").unlink(missing_ok=True)
        val.validate_config()
        assert len(val.ERRORS) == 1
        assert "missing" in val.ERRORS[0]

    def test_missing_required_section(self, tmp_project: Path) -> None:
        """Verify that missing top-level section fails Pydantic validation."""
        incomplete_data = {"version": "1.0"}  # Missing workflow_global etc.
        (tmp_project / "agent_orchestrator.json").write_text(json.dumps(incomplete_data), encoding="utf-8")
        val.validate_config()
        assert len(val.ERRORS) > 0
        assert "validation failed" in val.ERRORS[0].lower()


# ==========================================
# TESTS: agents.json Validation
# ==========================================
class TestAgentsValidation:
    def test_valid_agents_registry(self, tmp_project: Path) -> None:
        """Verify that valid registry passes."""
        # Note: tmp_project in conftest creates .agents/agent_registry.json (old name)
        # We need to ensure .agents/agent_registry.json exists for this test
        registry_path = tmp_project / ".agents" / "agent_registry.json"

        # Creating a valid registry file
        data = {
            "version": "1.0",
            "profiles": {
                "queen": {
                    "role": "Orchestrator",
                    "model": "m",
                    "provider": "p",
                    "thinking": "req",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
                "developer": {
                    "role": "Dev",
                    "model": "m",
                    "provider": "p",
                    "thinking": "req",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
                "pedant": {
                    "role": "Linter",
                    "model": "m",
                    "provider": "p",
                    "thinking": "req",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
                "auditor": {
                    "role": "Review",
                    "model": "m",
                    "provider": "p",
                    "thinking": "req",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
            },
        }
        registry_path.write_text(json.dumps(data), encoding="utf-8")

        val.validate_agents()
        assert len(val.ERRORS) == 0

    def test_invalid_json_detected(self, tmp_project: Path) -> None:
        """Verify that corrupted JSON files trigger a decode error."""
        (tmp_project / ".agents" / "agent_registry.json").write_text("{ invalid json }", encoding="utf-8")

        # Validator traps exceptions and logs to ERRORS
        val.validate_agents()
        assert len(val.ERRORS) > 0
        assert "Registry error" in val.ERRORS[0]


# ==========================================
# TESTS: Directory Structure
# ==========================================
class TestStructureValidation:
    def test_required_files_exist(self, tmp_project: Path) -> None:
        """Verify that core system files (including new names) are present."""
        # Create the missing required files in tmp_project for the validator
        (tmp_project / "agent_orchestrator.json").touch()
        (tmp_project / "agent_core" / "router.py").touch()
        (tmp_project / "agent_core" / "indexer.py").touch()
        (tmp_project / "agent_core" / "validator.py").touch()

        # Mocking existence check is implicitly handled by tmp_project fixture
        # but we need to ensure the list in validator matches Model 5.3
        val.validate_structure()

        # If any file is missing, ERRORS will be populated
        if val.ERRORS:
            pytest.fail(f"Structure validation failed: {val.ERRORS}")
