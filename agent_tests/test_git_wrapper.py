#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_git_wrapper.py - Unit tests for GitLocalManager.
Isolated module for testing underlying git subprocess calls.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_core.router_core.git_local import GitLocalManager


class TestGitLocal:
    @pytest.fixture
    def git(self, tmp_project: Path) -> GitLocalManager:
        (tmp_project / ".git").mkdir()
        return GitLocalManager(working_dir=tmp_project)

    def test_is_dirty_clean(self, git: GitLocalManager) -> None:
        with patch.object(git, "_run", return_value=""):
            assert git.is_dirty() is False

    def test_is_dirty_changed(self, git: GitLocalManager) -> None:
        with patch.object(git, "_run", return_value="M modified_file.py"):
            assert git.is_dirty() is True

    def test_ensure_branch_existing(self, git: GitLocalManager) -> None:
        with patch.object(git, "get_current_branch", return_value="main"), patch.object(git, "_run") as mock_run:
            git.ensure_branch("main")
            mock_run.assert_not_called()

    @patch("agent_core.router_core.git_local.subprocess.run")
    def test_ensure_branch_create(self, mock_sub: MagicMock, git: GitLocalManager) -> None:
        """Verifies branch creation occurs when subprocess signals branch does not exist."""
        with patch.object(git, "get_current_branch", return_value="main"), patch.object(git, "_run") as mock_run:
            # Simulate git show-ref returning non-zero (branch not found)
            mock_sub.return_value.returncode = 1
            git.ensure_branch("feat/new")

            # Verify it attempts to checkout and create (-b)
            mock_run.assert_called_once_with(["checkout", "-b", "feat/new"])
