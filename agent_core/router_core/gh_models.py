#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/gh_models.py - Pydantic models for GitHub API (v 1.0)."""

from pydantic import BaseModel, Field


class GHUser(BaseModel):
    """Simple GitHub user representation."""

    login: str
    id: int


class GHPullRequest(BaseModel):
    """Model representing a GitHub Pull Request response."""

    number: int = Field(description="The PR number on GitHub.")
    html_url: str = Field(description="Web URL of the Pull Request.")
    state: str = Field(description="Current state: 'open' or 'closed'.")
    title: str = Field(description="The title of the PR.")
    user: GHUser = Field(description="The author of the PR.")
    merged: bool | None = Field(default=False, description="Whether the PR has been merged.")


class GHWorkflowRun(BaseModel):
    """Model representing a GitHub Actions workflow run."""

    id: int = Field(description="Unique ID of the workflow run.")
    status: str = Field(description="Status: 'queued', 'in_progress', or 'completed'.")
    conclusion: str | None = Field(
        default=None,
        description="Conclusion: 'success', 'failure', 'neutral', 'cancelled', 'timed_out'.",
    )
    html_url: str = Field(description="Web URL to view the run progress/logs.")


class GHCheckSuite(BaseModel):
    """Model representing a GitHub Check Suite (collection of runs)."""

    id: int
    status: str
    conclusion: str | None = None
    head_sha: str = Field(description="The SHA of the commit being checked.")


class GHRepoInfo(BaseModel):
    """Model for repository metadata."""

    full_name: str = Field(description="Format: 'owner/repo'.")
    default_branch: str = Field(default="main")
    html_url: str
