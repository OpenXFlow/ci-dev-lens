#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/models.py - Pydantic schemas for orchestrator configuration (v 1.3)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ==========================================
# 1. DYNAMIC ENV CONFIGURATION (Smart Parser)
# ==========================================
class ProviderCredentials(BaseModel):
    """Holds credentials for a specific provider (dynamic)."""

    api_key: str
    base_url: str | None = None


class EnvConfig(BaseModel):
    """Smart schema for environment variables.

    Static fields: System control flags.
    Dynamic fields: Any {NAME}_API_KEY is parsed into the credentials dictionary.
    """

    # Static System Controls
    CI_MODE: str = Field(default="local")
    MOCK: bool = Field(default=False)
    GHA_MOCK_RESULT: str = Field(default="success")

    # Dynamic Credential Storage
    # Structure: {"GROQ": {"api_key": "...", "base_url": "..."}, "OLLAMA": ...}  # noqa: ERA001
    credentials: dict[str, ProviderCredentials] = Field(default_factory=dict)

    # Standard Optional token for GitHub Actions
    GITHUB_TOKEN: str | None = None

    # Pydantic V2 Configuration: Ignore extra env vars we don't explicitly define
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def parse_dynamic_providers(cls, data: Any) -> Any:  # noqa: ANN401
        """Scans input data (dict from .env) for patterns ending in _API_KEY.

        Groups them into the 'credentials' dictionary.
        """
        if not isinstance(data, dict):
            return data

        credentials = {}

        # Iterate over a copy of keys to avoid modification issues
        for key, value in data.items():
            if key.endswith("_API_KEY"):
                provider_name = key.replace("_API_KEY", "").upper()
                base_url_key = f"{provider_name}_BASE_URL"

                # Create credential entry
                credentials[provider_name] = {
                    "api_key": value,
                    "base_url": data.get(base_url_key),
                }

        # Inject parsed credentials into the model data
        data["credentials"] = credentials
        return data


# ==========================================
# 2. AGENT REGISTRY SCHEMA (.agents/agent_registry.json)
# ==========================================
class AgentProfile(BaseModel):
    """Schema for individual AI agent configurations."""

    role: str
    model: str
    provider: str
    thinking: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)
    allowed_skills: list[str] = Field(default_factory=list)


class AgentsRegistryModel(BaseModel):
    """Schema for the entire agent registry file."""

    version: str
    profiles: dict[str, AgentProfile]


# ==========================================
# 3. ORCHESTRATOR CONFIG SCHEMA (agent_orchestrator.json)
# ==========================================
# Generic wrapper for the {"value": X, "description": "..."} pattern
class SettingValueStr(BaseModel):
    """Configuration wrapper for string values."""

    value: str


class SettingValueBool(BaseModel):
    """Configuration wrapper for boolean values."""

    value: bool


class SettingValueInt(BaseModel):
    """Configuration wrapper for integer values."""

    value: int


class SettingValueFloat(BaseModel):
    """Configuration wrapper for float values."""

    value: float


class WorkflowGlobal(BaseModel):
    """Global workflow settings."""

    ci_mode: SettingValueStr
    loop_mode: SettingValueBool
    loop_delay_seconds: SettingValueInt
    max_task_attempts: SettingValueInt
    max_continuous_tasks: SettingValueInt


class StageConfig(BaseModel):
    """Configuration for individual workflow stages (e.g., ANALYSE, PLANNING)."""

    active: SettingValueBool
    max_retries: SettingValueInt
    pause_after: SettingValueBool | None = None


class FallbackMatrixEntry(BaseModel):
    """Fallback strategy for API failures."""

    fallback_provider: str
    fallback_model: str
    description: str | None = None


class ResilienceConfig(BaseModel):
    """System resilience settings."""

    smart_fallback: SettingValueBool
    fallback_matrix: dict[str, FallbackMatrixEntry]


class MemoryManagementConfig(BaseModel):
    """Context window memory management."""

    yellow_zone_threshold: SettingValueFloat
    red_zone_threshold: SettingValueFloat


class LoggingConfig(BaseModel):
    """Logging verbosity settings."""

    show_task_id: SettingValueBool
    verbosity: SettingValueStr


class OrchestratorConfigModel(BaseModel):
    """Master schema for the agent_orchestrator.json file."""

    version: str
    workflow_global: WorkflowGlobal
    workflow_local: dict[str, StageConfig]
    resilience: ResilienceConfig
    memory_management: MemoryManagementConfig
    logging: LoggingConfig
