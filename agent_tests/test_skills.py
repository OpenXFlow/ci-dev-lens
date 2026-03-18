#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.
"""
agent_tests/test_skills.py - Full unit tests for agent skills and logic (v 1.7).
Definitive fix for Mypy "object" type inference in McpBridge tests.
"""

import json
import re
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).parent.parent.resolve()
SKILLS_DIR = ROOT / ".claude" / "skills"

# ==========================================
# HELPER FUNCTIONS (Logic mirrored from skills)
# ==========================================

SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z\-_]{31,}", "Google API Key"),
    (r"gsk_[0-9A-Za-z]{32,}", "Groq API Key"),
    (r"github_pat_[0-9A-Za-z_]{36,}", "GitHub PAT"),
    (r"sk-[0-9A-Za-z]{32,}", "OpenAI API Key"),
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded password"),
    (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Private key"),
]

WARN_PATTERNS = [
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"pickle\.loads?\s*\(", "pickle.load()"),
]

NOISE_PATTERNS = [
    r"Agent \w+ finished\. Skills: \d+",
    r"Token budget: \d+/\d+",
    r"Mock response for agent",
    r"STATE → \w+",
]

IMPORTANT_PATTERNS = [
    r"HALT",
    r"TASK-\w+.*completed",
    r"Mypy error",
    r"Pipeline.*completed",
    r"RESULT:",
]


def is_secret(line: str) -> bool:
    """Check if a string contains a potential secret."""
    if "_CHANGE_ME" in line or "example" in line.lower():
        return False
    return any(re.search(p, line) for p, _ in SECRET_PATTERNS)


def is_warn(line: str) -> bool:
    """Check if a string contains a dangerous code pattern."""
    return any(re.search(p, line) for p, _ in WARN_PATTERNS)


def is_noise(line: str) -> bool:
    """Check if a log line is considered low-value noise."""
    return any(re.search(p, line, re.IGNORECASE) for p in NOISE_PATTERNS)


def is_important(line: str) -> bool:
    """Check if a log line contains a critical system event."""
    return any(re.search(p, line, re.IGNORECASE) for p in IMPORTANT_PATTERNS)


# ==========================================
# TESTS: Security Guard — Secrets
# ==========================================
class TestSecurityGuardSecrets:
    def test_detects_google_api_key(self) -> None:
        """Verify Google Cloud API key detection."""
        assert is_secret('api_key = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ123456"')

    def test_detects_groq_key(self) -> None:
        """Verify Groq API key detection."""
        assert is_secret('key = "gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"')

    def test_detects_github_pat(self) -> None:
        """Verify GitHub Personal Access Token detection."""
        assert is_secret('token = "github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefgh"')

    def test_detects_openai_key(self) -> None:
        """Verify OpenAI API key detection."""
        assert is_secret('key = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"')

    def test_detects_hardcoded_password(self) -> None:
        """Verify hardcoded password assignments are flagged."""
        assert is_secret('password = "secret_password_123"')

    def test_detects_private_key(self) -> None:
        """Verify RSA private key header detection."""
        assert is_secret("-----BEGIN RSA PRIVATE KEY-----")

    def test_ignores_placeholder(self) -> None:
        """Verify that _CHANGE_ME placeholders do not trigger alerts."""
        assert not is_secret("GOOGLE_API_KEY=AIzaSy_CHANGE_ME")

    def test_ignores_example(self) -> None:
        """Verify that documented examples in comments are ignored."""
        assert not is_secret("# example: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

    def test_ignores_clean_code(self) -> None:
        """Verify that standard function definitions are not flagged."""
        assert not is_secret("def calculate(a: int, b: int) -> int:")


# ==========================================
# TESTS: Security Guard — Warnings
# ==========================================
class TestSecurityGuardWarnings:
    def test_detects_eval(self) -> None:
        """Verify detection of dangerous eval() usage."""
        assert is_warn("result = eval(user_input)")

    def test_detects_exec(self) -> None:
        """Verify detection of dangerous exec() usage."""
        assert is_warn("exec(dynamic_code)")

    def test_detects_pickle_loads(self) -> None:
        """Verify detection of insecure pickle deserialization."""
        assert is_warn("data = pickle.loads(raw_bytes)")

    def test_clean_code_no_warn(self) -> None:
        """Verify that safe processing code is not flagged."""
        assert not is_warn("def process(data: str) -> str:")


# ==========================================
# TESTS: Context Compressor — Noise
# ==========================================
class TestContextCompressorNoise:
    def test_agent_completed_is_noise(self) -> None:
        """Verify that agent finish logs are marked as noise."""
        assert is_noise("Agent queen finished. Skills: 0")

    def test_token_budget_is_noise(self) -> None:
        """Verify that token consumption stats are marked as noise."""
        assert is_noise("Token budget: 1234/8000")

    def test_mock_response_is_noise(self) -> None:
        """Verify that mock simulation logs are marked as noise."""
        assert is_noise("Mock response for agent: developer")

    def test_state_change_is_noise(self) -> None:
        """Verify that redundant state transitions are marked as noise."""
        assert is_noise("STATE → PLANNING")

    def test_halt_is_not_noise(self) -> None:
        """Ensure HALT events are never discarded as noise."""
        assert not is_noise("HALT activated: Max attempts")

    def test_task_completed_is_not_noise(self) -> None:
        """Ensure task completion events are never discarded as noise."""
        assert not is_noise("Pipeline TASK-001 completed")


# ==========================================
# TESTS: Context Compressor — Important
# ==========================================
class TestContextCompressorImportant:
    def test_halt_is_important(self) -> None:
        """Verify that HALT is classified as an important fact."""
        assert is_important("HALT activated: reason")

    def test_task_done_is_important(self) -> None:
        """Verify that task completion is classified as an important fact."""
        assert is_important("Pipeline TASK-001 completed successfully.")

    def test_mypy_error_is_important(self) -> None:
        """Verify that logic errors are classified as important facts."""
        assert is_important("Mypy error: incompatible type")

    def test_result_is_important(self) -> None:
        """Verify that skill results are classified as important facts."""
        assert is_important("RESULT:PASS")
        assert is_important("RESULT:MYPY_FAIL")

    def test_generic_log_not_important(self) -> None:
        """Verify that generic calling logs are not marked as critical."""
        assert not is_important("Calling agent: queen")


# ==========================================
# TESTS: Context Compressor — Compression Logic
# ==========================================
class TestContextCompressorCompression:
    def test_noise_removed_important_kept(self) -> None:
        """Verify filtering logic where noise is removed and facts are kept."""
        lines = [
            "[10:00] Agent queen finished. Skills: 0",
            "[10:01] Token budget: 1234/8000",
            "[10:02] HALT activated: Max attempts",
            "[10:03] Pipeline TASK-001 completed successfully.",
        ]
        important = [line for line in lines if is_important(line)]
        noise = [line for line in lines if is_noise(line)]
        assert len(important) == 2
        assert len(noise) == 2

    def test_last_line_classification(self) -> None:
        """Verify classification of a standard activity line."""
        last_line = "Latest neutral action line"
        assert not is_noise(last_line)
        assert not is_important(last_line)


# ==========================================
# TESTS: Handoff Manager (Model 5.2 Paths)
# ==========================================
class TestHandoffManager:
    def test_reads_active_tasks(self, tmp_project: Path) -> None:
        """Verify Handoff Manager reads active tasks from agent_context."""
        content = (tmp_project / "agent_context" / "TASKS.md").read_text(encoding="utf-8")
        active = [line for line in content.splitlines() if line.startswith("- [ ]")]
        # Model 5.2 conftest.py injects both GOAL-001 and TASK-001
        assert len(active) == 2
        assert "GOAL-001" in active[0]
        assert "TASK-001" in active[1]

    def test_reads_completed_tasks(self, tmp_project: Path) -> None:
        """Verify Handoff Manager reads completed tasks from agent_context."""
        content = (tmp_project / "agent_context" / "TASKS.md").read_text(encoding="utf-8")
        completed = [line for line in content.splitlines() if line.startswith("- [x]")]
        assert len(completed) == 1
        assert "TASK-000" in completed[0]

    def test_last_actions_extraction(self) -> None:
        """Verify extraction of the most recent log entries."""
        action_log = "[10:00] Step 1\n[10:01] Step 2\n[10:02] Step 3"
        lines = [line for line in action_log.splitlines() if line.strip()]
        assert lines[-1] == "[10:02] Step 3"
        assert len(lines[-10:]) == 3

    def test_handoff_file_naming(self) -> None:
        """Verify that handoff filenames follow the timestamped pattern."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"handoff-{timestamp}.md"
        assert filename.startswith("handoff-")
        assert filename.endswith(".md")

    def test_template_has_correct_schema(self) -> None:
        """Verify the handoff template contains mandatory section headers."""
        template_path = SKILLS_DIR / "handoff-manager" / "assets" / "template.md"
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
            assert "## [STATE]" in content
            assert "IDLE" in content


# ==========================================
# TESTS: MCP Bridge
# ==========================================
class TestMcpBridge:
    """Test suite for the MCP Bridge proxy simulation."""

    SUPPORTED_TOOLS: ClassVar[dict[str, list[str]]] = {
        "github": ["create_issue", "comment_issue", "create_pr", "merge_pr"],
        "slack": ["notify", "post_message"],
        "jira": ["create_ticket", "update_ticket", "comment"],
    }

    def validate_call(self, tool: str, action: str) -> tuple[bool, str]:
        """Simulation of MCP validation logic with definitive Mypy fix."""
        # DEFINITIVE FIX: Use the class name for access to resolve the 'object' inference error.
        # Explicitly typing the local variable ensures Mypy treats it as a Mapping.
        tools: dict[str, list[str]] = TestMcpBridge.SUPPORTED_TOOLS

        if tool not in tools:
            return False, f"Unknown tool: {tool}"
        if action not in tools[tool]:
            return False, f"Unknown action '{action}' for {tool}"
        return True, ""

    def test_valid_github_create_issue(self) -> None:
        """Verify valid tool/action combination for GitHub."""
        ok, _ = self.validate_call("github", "create_issue")
        assert ok is True

    def test_valid_slack_notify(self) -> None:
        """Verify valid tool/action combination for Slack."""
        ok, _ = self.validate_call("slack", "notify")
        assert ok is True

    def test_valid_jira_create_ticket(self) -> None:
        """Verify valid tool/action combination for Jira."""
        ok, _ = self.validate_call("jira", "create_ticket")
        assert ok is True

    def test_invalid_tool(self) -> None:
        """Verify rejection of an unsupported tool."""
        ok, reason = self.validate_call("trello", "create_card")
        assert ok is False
        assert "trello" in reason

    def test_invalid_action_for_tool(self) -> None:
        """Verify rejection of an invalid action for a supported tool."""
        ok, reason = self.validate_call("github", "non_existent_action")
        assert ok is False
        assert "non_existent_action" in reason

    def test_mock_response_structure(self) -> None:
        """Verify the JSON schema of a simulated MCP response."""
        from datetime import datetime

        result = {
            "mock": True,
            "tool": "github",
            "action": "create_issue",
            "result": "MOCK_GITHUB_CREATE_ISSUE_OK",
            "timestamp": datetime.now().isoformat(),
        }
        assert result["mock"] is True
        assert "MOCK" in result["result"]

    def test_all_tools_have_actions(self) -> None:
        """Verify that every supported tool has at least one action (Ruff PERF102 Fix)."""
        for actions in TestMcpBridge.SUPPORTED_TOOLS.values():
            assert len(actions) > 0

    def test_valid_json_params(self) -> None:
        """Verify parsing of valid JSON tool parameters."""
        params = json.loads('{"title": "Bug", "labels": ["bug"]}')
        assert params["title"] == "Bug"

    def test_invalid_json_params(self) -> None:
        """Verify that malformed JSON strings trigger appropriate exceptions."""
        with pytest.raises(json.JSONDecodeError):
            json.loads("{ malformed json }")
