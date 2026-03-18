#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/agent_actions.py - Structured schemas for AI responses (v 1.1)."""

from pydantic import BaseModel, Field

# ==========================================
# 1. ATOMIC ACTIONS (Common building blocks)
# ==========================================


class FileWrite(BaseModel):
    """Schema for writing or updating a file on disk."""

    path: str = Field(description="Relative path to the file from project root.")
    content: str = Field(description="Full content of the file. No snippets allowed.")


class SkillCall(BaseModel):
    """Schema for calling an internal framework skill."""

    name: str = Field(description="Name of the skill (e.g., 'testing-pro', 'quality-gate').")
    arguments: dict[str, str] = Field(default_factory=dict, description="Key-value arguments for the skill script.")


# ==========================================
# 2. AGENT SPECIFIC RESPONSES
# ==========================================


class AtomicTask(BaseModel):
    """Represents a single atomic unit of work (Test + Implementation) enforcing the TDD contract."""

    id: str = Field(description="3-digit ID, e.g., '001'.")
    title: str = Field(description="Short summary of the feature.")
    source_file: str = Field(description="Path to the src/ file being created or modified.")
    test_file: str = Field(description="Path to the tests/ file being created or modified.")
    description: str = Field(description="Detailed technical instruction for the logic and test cases.")
    status: str = Field(default="pending", description="Status: 'pending', 'completed', or 'blocked'.")
    attempts: int = Field(default=0, description="Current attempt count.")


class QueenResponse(BaseModel):
    """Structured response for the Architect (Queen)."""

    thought: str = Field(description="Internal reasoning and strategic analysis.")
    updated_tasks: list[AtomicTask] = Field(description="The complete list of technical tasks for [AGENT_PROGRESS].")


class DeveloperResponse(BaseModel):
    """Structured response for the Implementer (Developer)."""

    thought: str = Field(description="Brief explanation of the implementation approach.")
    files: list[FileWrite] = Field(default_factory=list, description="List of files to be created or modified.")
    skills: list[SkillCall] = Field(
        default_factory=list, description="List of skills to be executed after writing files."
    )


class AuditorResponse(BaseModel):
    """Structured response for the Reviewer (Auditor)."""

    thought: str = Field(description="Security and quality audit reasoning.")
    is_verified: bool = Field(description="True if the code meets all standards.")
    commit_message: str | None = Field(default=None, description="Standardized commit message if verification passed.")
    feedback_for_dev: str | None = Field(
        default=None, description="Detailed error message for the developer if verification failed."
    )
