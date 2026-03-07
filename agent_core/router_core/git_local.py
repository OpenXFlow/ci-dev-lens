#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/git_local.py - Native Git Wrapper for Local Operations (v 1.2)."""

import shutil
import subprocess
from pathlib import Path

from .utils import ROOT, log

# Resolve the absolute path to the git executable to satisfy Ruff S607
GIT_PATH = shutil.which("git") or "git"


class GitLocalManager:
    """Manages local git operations using optimized subprocess calls."""

    def __init__(self, working_dir: Path = ROOT) -> None:
        self.cwd = working_dir
        if not (self.cwd / ".git").exists():
            log("Git repository not detected in the working directory.", "WARN")

    def _run(self, cmd: list[str], check: bool = True) -> str:
        """Executes a git command and returns the output."""
        try:
            result = subprocess.run(
                [GIT_PATH, *cmd],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() or str(e)
            log(f"Git command failed: git {' '.join(cmd)} - {err_msg}", "ERROR")
            raise RuntimeError(f"Git execution error: {err_msg}") from e

    def get_current_branch(self) -> str:
        """Returns the name of the active branch."""
        return self._run(["rev-parse", "--abbrev-ref", "HEAD"])

    def is_dirty(self) -> bool:
        """Checks if there are uncommitted changes in the repository."""
        # --porcelain provides machine-readable output, empty if clean
        status = self._run(["status", "--porcelain"])
        return len(status) > 0

    def ensure_branch(self, branch_name: str) -> None:
        """Checks out a branch, creating it if it doesn't exist."""
        current = self.get_current_branch()
        if current == branch_name:
            return

        log(f"🌿 Switching to branch: {branch_name}", "INFO")

        # Safely verify if branch exists without throwing exceptions
        check_exists = subprocess.run(
            [GIT_PATH, "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], cwd=self.cwd, check=False
        )

        if check_exists.returncode == 0:
            # Branch exists, just switch to it
            self._run(["checkout", branch_name])
        else:
            # Branch does not exist, create and switch
            self._run(["checkout", "-b", branch_name])

    def commit_all(self, message: str) -> bool:
        """Stages all changes and creates a commit."""
        if not self.is_dirty():
            log("No changes detected. Skipping commit.", "INFO")
            return False

        log(f"💾 Committing changes: {message}", "INFO")
        self._run(["add", "."])
        self._run(["commit", "-m", message])
        return True

    def push(self, remote: str = "origin") -> None:
        """Pushes the current branch to the remote repository."""
        branch = self.get_current_branch()
        log(f"📤 Pushing branch '{branch}' to {remote}...", "INFO")
        # -u sets the upstream for easier future calls
        self._run(["push", "-u", remote, branch])

    def merge_to_main(self, main_branch: str = "main") -> None:
        """Merges current work into the main branch (used in local_git mode)."""
        feature_branch = self.get_current_branch()
        if feature_branch == main_branch:
            return

        log(f"🔀 Merging {feature_branch} into {main_branch}...", "INFO")
        self._run(["checkout", main_branch])
        self._run(["merge", feature_branch])
        self._run(["branch", "-d", feature_branch])  # Cleanup local branch
