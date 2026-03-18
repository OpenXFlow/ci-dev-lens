#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/models.py (v 1.13)
Pydantic schemas for orchestrator configuration and state validation.
Added ExecutionLogEntry and max_execution_logs (ACMI Blueprint v3.2).
Surgical Patch (v1.13): Added Token Telemetry fields to ExecutionLogEntry.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ==========================================
# 1. DYNAMIC ENV CONFIGURATION
# ==========================================
class ProviderCredentials(BaseModel):
    """Holds credentials for a specific provider."""

    api_key: str
    base_url: str | None = None


class EnvConfig(BaseModel):
    """Smart schema for environment variables including GitHub secrets."""

    CI_MODE: str = Field(default="local")
    MOCK: bool = Field(default=False)
    GHA_MOCK_RESULT: str = Field(default="success")

    # GitHub Environment Specifics
    GITHUB_REPOSITORY: str | None = None
    GITHUB_TOKEN: str | None = None

    credentials: dict[str, ProviderCredentials] = Field(default_factory=dict)
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def parse_dynamic_providers(cls, data: Any) -> Any:  # noqa: ANN401
        """Groups {NAME}_API_KEY patterns into credentials dict."""
        if not isinstance(data, dict):
            return data
        credentials = {}
        for key, value in data.items():
            if key.endswith("_API_KEY"):
                p_name = key.replace("_API_KEY", "").upper()
                credentials[p_name] = {
                    "api_key": value,
                    "base_url": data.get(f"{p_name}_BASE_URL"),
                }
        data["credentials"] = credentials
        return data


# ==========================================
# 2. AGENT REGISTRY MODELS
# ==========================================
class AgentProfile(BaseModel):
    """Individual AI agent configurations."""

    role: str
    model: str
    provider: str
    thinking: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)
    allowed_skills: list[str] = Field(default_factory=list)


class AgentsRegistryModel(BaseModel):
    """Full agent profile registry."""

    version: str
    profiles: dict[str, AgentProfile]


# ==========================================
# 3. SETTING VALUE WRAPPERS
# ==========================================
class SettingValueStr(BaseModel):
    """Container for string settings."""

    value: str


class SettingValueBool(BaseModel):
    """Container for boolean settings."""

    value: bool


class SettingValueInt(BaseModel):
    """Container for integer settings."""

    value: int


class SettingValueFloat(BaseModel):
    """Container for float settings."""

    value: float


# ==========================================
# 4. VCS CONTROL MODELS
# ==========================================
class GitHubConfig(BaseModel):
    """Specific settings for GitHub/Cloud flow."""

    auto_push: SettingValueBool
    auto_pr: SettingValueBool
    watch_gha: SettingValueBool
    gha_timeout_minutes: SettingValueInt


class LocalGitConfig(BaseModel):
    """Specific settings for local Git flow."""

    auto_commit: SettingValueBool
    branch_per_goal: SettingValueBool


class ActConfig(BaseModel):
    """Specific settings for 'act' (Local GHA Simulation)."""

    workflow_file: SettingValueStr
    platform: SettingValueStr


class VCSControlConfig(BaseModel):
    """Master VCS orchestration settings."""

    mode: SettingValueStr
    github_settings: GitHubConfig
    local_git_settings: LocalGitConfig
    local_act_settings: ActConfig


# ==========================================
# 5. MASTER CONFIGURATION SCHEMA
# ==========================================
class WorkflowGlobal(BaseModel):
    """Global workflow settings."""

    ci_mode: SettingValueStr
    loop_mode: SettingValueBool
    loop_delay_seconds: SettingValueInt
    max_task_attempts: SettingValueInt
    max_continuous_tasks: SettingValueInt


class StageConfig(BaseModel):
    """Configuration for individual workflow stages."""

    active: SettingValueBool
    max_retries: SettingValueInt
    requires_llm: SettingValueBool = Field(default_factory=lambda: SettingValueBool(value=True))
    pause_after: SettingValueBool | None = None


class FallbackMatrixEntry(BaseModel):
    """API Fallback strategy."""

    fallback_provider: str
    fallback_model: str
    description: str | None = None


class ResilienceConfig(BaseModel):
    """System resilience settings."""

    smart_fallback: SettingValueBool
    http_connect_timeout: SettingValueFloat
    http_read_timeout: SettingValueFloat
    retry_attempts: SettingValueInt
    retry_backoff_factor: SettingValueFloat
    fallback_matrix: dict[str, FallbackMatrixEntry]


class MemoryManagementConfig(BaseModel):
    """Context window management."""

    yellow_zone_threshold: SettingValueFloat
    red_zone_threshold: SettingValueFloat


class MemoryEngineConfig(BaseModel):
    """Settings for the SQLite Memory Engine and RAG."""

    enabled: SettingValueBool
    db_path: SettingValueStr
    max_reflections: SettingValueInt
    max_execution_logs: SettingValueInt
    fts_result_limit: SettingValueInt
    vacuum_on_purge: SettingValueBool


class LoggingConfig(BaseModel):
    """Logging verbosity settings."""

    show_task_id: SettingValueBool
    verbosity: SettingValueStr


class OrchestratorConfigModel(BaseModel):
    """The master schema for agent_orchestrator.json."""

    version: str
    workflow_global: WorkflowGlobal
    workflow_local: dict[str, StageConfig]
    vcs_control: VCSControlConfig
    resilience: ResilienceConfig
    memory_management: MemoryManagementConfig
    memory_engine: MemoryEngineConfig
    logging: LoggingConfig


# ==========================================
# 6. EXECUTION MODELS (Memory Engine)
# ==========================================
class ExecutionLogEntry(BaseModel):
    """Schema for validating skill execution logs before database insertion."""

    task_id: str = Field(description="The ID of the task being executed.")
    stage: str = Field(description="The current pipeline stage (e.g., LINTING, TESTING).")
    tool: str = Field(description="The name of the tool executed (e.g., ruff, pytest).")
    result: str = Field(description="The outcome of the execution (e.g., PASS, FAIL, ERROR).")
    output: str = Field(description="The raw standard output and error log.")
    duration_ms: int = Field(description="Execution time in milliseconds.")
    attempt: int = Field(description="The current retry attempt number for this stage.")
    provider: str = Field(default="", description="The LLM provider name (e.g., groq, mistral).")
    tokens_used: int = Field(default=0, description="Total tokens consumed by the call.")
    tokens_prompt: int = Field(default=0, description="Tokens used in the prompt.")
    tokens_completion: int = Field(default=0, description="Tokens used in the completion.")
