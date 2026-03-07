#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/github_client.py - Native GitHub REST API Client (v 1.2)."""

import time
from typing import Any, cast

import httpx
import stamina

from .gh_models import GHPullRequest, GHRepoInfo, GHWorkflowRun
from .models import EnvConfig, OrchestratorConfigModel
from .utils import log


class GitHubAPIClient:
    """Enterprise-grade client for GitHub API interaction using httpx and stamina."""

    def __init__(self, env: EnvConfig, config: OrchestratorConfigModel) -> None:
        self.env = env
        self.config = config
        self.base_url = "https://api.github.com"

        if not self.env.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN is missing in environment.")
        if not self.env.GITHUB_REPOSITORY:
            raise ValueError("GITHUB_REPOSITORY (owner/repo) is missing in environment.")

        self.headers = {
            "Authorization": f"Bearer {self.env.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Agent-CI-Lens/1.0",
        }

    def _should_retry(self, exc: Exception) -> bool:
        """Retry logic tailored for GitHub API (includes 403 for rate limiting)."""
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in (403, 429) or exc.response.status_code >= 500
        return isinstance(exc, httpx.RequestError)

    def _request(self, method: str, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Universal request wrapper with stamina retries and type casting."""
        url = f"{self.base_url}/repos/{self.env.GITHUB_REPOSITORY}{path}"

        # ARCHITECT FIX: Provide default value as first argument
        timeout_cfg = httpx.Timeout(
            self.config.resilience.http_read_timeout.value,
            connect=self.config.resilience.http_connect_timeout.value,
        )

        for attempt in stamina.retry_context(
            on=self._should_retry,
            attempts=self.config.resilience.retry_attempts.value,
            wait_initial=2.0,
            wait_max=10.0,
        ):
            with attempt, httpx.Client(timeout=timeout_cfg, headers=self.headers) as client:
                resp = client.request(method, url, json=json_data)
                resp.raise_for_status()
                return cast(dict[str, Any], resp.json())

        raise RuntimeError(f"GitHub API request to {path} failed after retries.")

    def get_repo_info(self) -> GHRepoInfo:
        """Fetches repository metadata."""
        data = self._request("GET", "")
        return GHRepoInfo.model_validate(data)

    def create_pull_request(self, head: str, title: str, body: str) -> GHPullRequest:
        """Creates a new Pull Request against the default branch."""
        repo = self.get_repo_info()
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": repo.default_branch,
        }
        log(f"🎋 Creating Pull Request for branch: {head}", "INFO")
        data = self._request("POST", "/pulls", json_data=payload)
        return GHPullRequest.model_validate(data)

    def get_latest_workflow_run(self, branch: str) -> GHWorkflowRun | None:
        """Retrieves the most recent workflow run for a specific branch."""
        path = f"/actions/runs?branch={branch}&per_page=1"
        data = self._request("GET", path)
        runs = data.get("workflow_runs", [])
        if not runs:
            return None
        return GHWorkflowRun.model_validate(runs[0])

    def poll_workflow_status(self, branch: str) -> GHWorkflowRun:
        """Wait for GHA workflow completion using smart polling."""
        timeout_minutes = self.config.vcs_control.github_settings.gha_timeout_minutes.value
        start_time = time.time()

        log(f"⏳ Waiting for GHA workflow on branch: {branch}...", "INFO")

        while (time.time() - start_time) < (timeout_minutes * 60):
            run = self.get_latest_workflow_run(branch)

            if run:
                if run.status == "completed":
                    log(f"🚀 GHA Run completed with conclusion: {run.conclusion}", "OK")
                    return run

                log(f"   Current status: {run.status}...", "INFO")
            else:
                log(f"   Waiting for GHA to trigger on {branch}...", "INFO")

            time.sleep(30)

        raise TimeoutError(f"GHA polling timed out after {timeout_minutes} minutes.")
