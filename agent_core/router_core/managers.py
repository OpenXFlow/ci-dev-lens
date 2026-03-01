#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/managers.py - State managers for agent_context (v 1.5)
"""

import re
from datetime import datetime
from typing import Any

from .utils import ROOT, log


class SessionManager:
    """Manages the persistent state and action log in agent_context/SESSION.md."""

    def __init__(self) -> None:
        self.path = ROOT / "agent_context" / "SESSION.md"
        self.user_section_cache: str = ""

    def read(self) -> dict[str, str]:
        """Reads session sections securely using forgiving regex parsing."""
        if not self.path.exists():
            return {}

        content = self.path.read_text(encoding="utf-8")
        sections: dict[str, str] = {}

        # 1. Parse User Section
        user_match = re.search(r"##\s*\[USER_SECTION\](.*?)---", content, re.DOTALL)
        self.user_section_cache = user_match.group(1).strip() if user_match else ""

        ctx_match = re.search(r"###\s*\[CONTEXT\]\n(.*?)(?=\n###|$)", self.user_section_cache, re.DOTALL)
        sections["CONTEXT"] = ctx_match.group(1).strip() if ctx_match else ""

        wrk_match = re.search(r"###\s*\[WORKSPACE\]\n(.*?)(?=\n###|$)", self.user_section_cache, re.DOTALL)
        sections["WORKSPACE"] = wrk_match.group(1).strip() if wrk_match else ""

        # 2. Parse Agent Section (robust fallback against missing headers)
        agent_match = re.search(r"##\s*\[AGENT_SECTION\](.*)", content, re.DOTALL)
        agent_part = agent_match.group(1) if agent_match else ""

        state_match = re.search(r"###\s*\[STATE\]\n(.*?)(?=\n###|$)", agent_part, re.DOTALL)
        sections["STATE"] = state_match.group(1).strip() if state_match else "IDLE"

        fb_match = re.search(r"###\s*\[FEEDBACK\]\n(.*?)(?=\n###|$)", agent_part, re.DOTALL)
        sections["FEEDBACK"] = fb_match.group(1).strip() if fb_match else ""

        log_match = re.search(r"###\s*\[ACTION_LOG\]\n(.*?)(?=\n###|$)", agent_part, re.DOTALL)
        sections["ACTION_LOG"] = log_match.group(1).strip() if log_match else ""

        return sections

    def _write_all(self, sections: dict[str, str]) -> None:
        """Atomically writes all sections back using idiomatic string formatting."""
        content = (
            "# Agent-CI-Lens SESSION\n\n"
            "## [USER_SECTION]\n"
            "### [CONTEXT]\n"
            f"{sections.get('CONTEXT', '')}\n\n"
            "### [WORKSPACE]\n"
            f"{sections.get('WORKSPACE', '')}\n\n"
            "---\n\n"
            "## [AGENT_SECTION]\n"
            "### [STATE]\n"
            f"{sections.get('STATE', 'IDLE')}\n\n"
            "### [FEEDBACK]\n"
            f"{sections.get('FEEDBACK', '')}\n\n"
            "### [ACTION_LOG]\n"
            f"{sections.get('ACTION_LOG', '')}\n"
        )
        self.path.write_text(content, encoding="utf-8")

    def write_state(self, state: str, tid: str | None = None) -> None:
        """Updates the system state and logs the transition."""
        s = self.read()
        s["STATE"] = state
        self._write_all(s)
        log(f"STATE → {state}", "STATE", tid=tid)

    def write_action_log(self, entry: str) -> None:
        """Appends an entry to the action log with a timestamp."""
        s = self.read()
        ts = datetime.now().strftime("%H:%M")

        current_log = s.get("ACTION_LOG", "")
        new_entry = f"[{ts}] {entry}"
        s["ACTION_LOG"] = f"{current_log}\n{new_entry}".strip()

        self._write_all(s)

    def write_context(self, ctx: str) -> None:
        """Updates the persistent context section."""
        s = self.read()
        s["CONTEXT"] = ctx
        self._write_all(s)

    def write_feedback(self, msg: str) -> None:
        """Updates the persistent system feedback section."""
        s = self.read()
        s["FEEDBACK"] = msg
        self._write_all(s)

    def add_workspace(self, path: str) -> None:
        """Appends a new file path to the workspace."""
        s = self.read()
        current_workspace = s.get("WORKSPACE", "")
        s["WORKSPACE"] = f"{current_workspace}\n- {path}".strip()
        self._write_all(s)


class TasksManager:
    """Manages technical tasks and goals in agent_context/TASKS.md."""

    def __init__(self) -> None:
        self.path = ROOT / "agent_context" / "TASKS.md"
        self.max_attempts = 3

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """Parses active tasks and synthetic goals from the tasks file."""
        if not self.path.exists():
            return []

        content = self.path.read_text(encoding="utf-8")

        # Robust extraction using partition
        _, _, agent_part = content.partition("## [AGENT_PROGRESS]")

        # PERF401: Idiomatic Python List Comprehension
        tasks = [
            {"id": m.group(1), "description": m.group(2).strip(), "attempts": int(m.group(3))}
            for line in agent_part.splitlines()
            if line.strip().startswith("- [ ]") and (m := re.search(r"TASK-(\w+): (.+?) \[attempts: (\d+)\]", line))
        ]

        if tasks:
            return tasks

        # Fallback to User Queue if no agent tasks are active (FIX: Added space)
        _, _, user_part = content.partition("## [USER_QUEUE]")
        user_queue, _, _ = user_part.partition("---")

        for line in user_queue.splitlines():
            if line.strip().startswith("- [ ]") and (m := re.search(r"GOAL-(\w+): (.+)", line)):
                return [
                    {
                        "id": f"GOAL-{m.group(1)}",
                        "description": m.group(2).strip(),
                        "attempts": 0,
                        "is_synthetic": True,
                    }
                ]

        return []

    def get_all_task_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        return set(re.findall(r"TASK-(\d+)", self.path.read_text(encoding="utf-8")))

    def mark_completed(self, tid: str) -> None:
        """Marks a technical task as completed [x] and saves to disk."""
        if not self.path.exists():
            return

        lines = self.path.read_text(encoding="utf-8").splitlines()

        for i, line in enumerate(lines):
            if f"TASK-{tid}:" in line or f"TASK-{str(tid).zfill(3)}:" in line:
                lines[i] = line.replace("- [ ]", "- [x]")

        self.path.write_text("\n".join(lines), encoding="utf-8")

    def mark_goal_completed(self, gid: str) -> None:
        """Marks a specific high-level goal as completed [x]."""
        if not self.path.exists():
            return

        lines = self.path.read_text(encoding="utf-8").splitlines()

        for i, line in enumerate(lines):
            if f"GOAL-{gid}:" in line:
                lines[i] = line.replace("- [ ]", "- [x]")

        self.path.write_text("\n".join(lines), encoding="utf-8")

    def increment_attempts(self, tid: str, error: str) -> int:
        """Increments attempt count for a task and blocks it if limit is reached."""
        if not self.path.exists():
            return 0

        lines = self.path.read_text(encoding="utf-8").splitlines()
        new_att = 0

        for i, line in enumerate(lines):
            if f"TASK-{tid}:" in line and (m := re.search(r"\[attempts: (\d+)\]", line)):
                new_att = int(m.group(1)) + 1
                new_line = re.sub(r"\[attempts: \d+\]", f"[attempts: {new_att}]", line)

                if new_att >= self.max_attempts:
                    new_line = new_line.replace("- [ ]", "- [BLOCKED]")
                    new_line = f"{new_line} -> Zlyhalo: {error}"

                lines[i] = new_line

        self.path.write_text("\n".join(lines), encoding="utf-8")
        return new_att


class HaltManager:
    """Handles the emergency HALT state by creating a flag file."""

    def __init__(self) -> None:
        self.flag_path = ROOT / ".claude/cache/HALT.flag"

    def is_halted(self) -> bool:
        """Checks if the system is in a HALT state."""
        return self.flag_path.exists()

    def halt(self, reason: str, tid: str | None = None) -> None:
        """Activates HALT state and logs the reason."""
        self.flag_path.parent.mkdir(parents=True, exist_ok=True)
        self.flag_path.write_text(f"[{datetime.now().isoformat()}] HALT: {reason}")
        log(f"HALT ACTIVATED: {reason}", "ERROR", tid=tid)
