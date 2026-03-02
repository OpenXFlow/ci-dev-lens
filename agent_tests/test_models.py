#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_models.py - Unit tests for Pydantic configuration schemas (v 1.2)
"""

from agent_core.router_core.models import AgentsRegistryModel, EnvConfig, OrchestratorConfigModel


class TestEnvConfig:
    def test_default_values(self) -> None:
        """Verify that default values are assigned when keys are missing."""
        config = EnvConfig.model_validate({})
        assert config.CI_MODE == "local"
        assert config.MOCK is False
        assert config.GHA_MOCK_RESULT == "success"

    def test_dynamic_provider_parsing(self) -> None:
        """Verify that any *_API_KEY is parsed into the credentials dict."""
        raw_env = {
            "GROQ_API_KEY": "gsk_123",
            "GROQ_BASE_URL": "https://api.groq.com",
            "CUSTOM_API_KEY": "secret_abc",
            # CUSTOM_BASE_URL is missing, should be None
            "MOCK": "true",
        }
        config = EnvConfig.model_validate(raw_env)

        # Check System flags
        assert config.MOCK is True

        # Check Dynamic Credentials
        assert "GROQ" in config.credentials
        assert config.credentials["GROQ"].api_key == "gsk_123"
        assert config.credentials["GROQ"].base_url == "https://api.groq.com"

        assert "CUSTOM" in config.credentials
        assert config.credentials["CUSTOM"].api_key == "secret_abc"
        assert config.credentials["CUSTOM"].base_url is None


class TestAgentsRegistry:
    def test_valid_registry_parsing(self) -> None:
        """Verify valid agent registry JSON parsing."""
        data = {
            "version": "1.0",
            "profiles": {
                "queen": {
                    "role": "Orchestrator",
                    "model": "mistral-large",
                    "provider": "mistral",
                    "thinking": "required",
                    "temperature": 0.2,
                    "max_tokens": 8000,
                    "allowed_skills": ["cascade-logic"],
                }
            },
        }
        registry = AgentsRegistryModel.model_validate(data)
        assert registry.version == "1.0"
        assert "queen" in registry.profiles
        assert registry.profiles["queen"].temperature == 0.2


class TestOrchestratorConfig:
    def test_valid_config_parsing(self) -> None:
        """Verify that the complex nested config parses correctly."""
        data = {
            "version": "1.3",
            "workflow_global": {
                "ci_mode": {"value": "local"},
                "loop_mode": {"value": True},
                "loop_delay_seconds": {"value": 15},
                "max_task_attempts": {"value": 3},
                "max_continuous_tasks": {"value": 10},
            },
            "workflow_local": {"ANALYSE": {"active": {"value": True}, "max_retries": {"value": 3}}},
            "resilience": {
                "smart_fallback": {"value": True},
                "http_connect_timeout": {"value": 10.0},
                "http_read_timeout": {"value": 60.0},
                "retry_attempts": {"value": 5},
                "retry_backoff_factor": {"value": 2.0},
                "fallback_matrix": {"GROQ": {"fallback_provider": "MISTRAL", "fallback_model": "mistral-large"}},
            },
            "memory_management": {"yellow_zone_threshold": {"value": 0.7}, "red_zone_threshold": {"value": 0.9}},
            "logging": {"show_task_id": {"value": True}, "verbosity": {"value": "INFO"}},
        }
        config = OrchestratorConfigModel.model_validate(data)
        assert config.workflow_global.loop_delay_seconds.value == 15
        assert config.resilience.fallback_matrix["GROQ"].fallback_provider == "MISTRAL"
        assert config.resilience.retry_attempts.value == 5
