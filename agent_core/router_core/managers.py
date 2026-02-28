#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/managers.py - State managers for agent_context (v 1.2)
"""

import re
from datetime import datetime
from typing import Any

from .utils import ROOT, log


class SessionManager:
    """Manages the persistent state and action log in agent_context/SESSION.md."""
    def __init__(self) -> None:
        self.path = ROOT / "agent_context" / "SESSION.md"
        self.user_section_cache = ""

    def read(self) -> dict[str, str]:
        """Reads session sections and caches the user section."""
        if not self.path.exists():
            return {}
        content = self.path.read_text(encoding="utf-8")
        user_match = re.search(r"## \[USER_SECTION\](.*?)---", content, re.DOTALL)
        self.user_section_cache = user_match.group(1).strip() if user_match else ""

        sections: dict[str, str] = {}
        ctx_match = re.search(r"### \[CONTEXT\]\n(.*?)(?=\n###|$)", self.user_section_cache, re.DOTALL)
        sections["CONTEXT"] = ctx_match.group(1).strip() if ctx_match else ""
        wrk_match = re.search(r"### \[WORKSPACE\]\n(.*?)(?=\n###|$)", self.user_section_cache, re.DOTALL)
        sections["WORKSPACE"] = wrk_match.group(1).strip() if wrk_match else ""

        # OPRAVA: Pridaná medzera do splitu, aby sedela s conftest.py a _write_all
        parts = content.split("## [AGENT_SECTION]")
        agent_part = parts[-1] if len(parts) > 1 else ""

        state_match = re.search(r"### \[STATE\]\n(.*?)(?=\n###|$)", agent_part, re.DOTALL)
        sections["STATE"] = state_match.group(1).strip() if state_match else "IDLE"
        log_match = re.search(r"### \[ACTION_LOG\]\n(.*?)(?=\n###|$)", agent_part, re.DOTALL)
        sections["ACTION_LOG"] = log_match.group(1).strip() if log_match else ""
        return sections

    def _write_all(self, sections: dict[str, str]) -> None:
        """Atomically writes all sections back to the SESSION.md file."""
        lines = [
            "# Agent-CI-Lens SESSION",
            "",
            "## [USER_SECTION]",
            "### [CONTEXT]",
            sections.get("CONTEXT", ""),
            "",
            "### [WORKSPACE]",
            sections.get("WORKSPACE", ""),
            "",
            "---",
            "",
            "## [AGENT_SECTION]",
            # OPRAVA: Vrátené medzery do hlavičiek (### [STATE])
            "### [STATE]",
            sections.get("STATE", "IDLE"),
            "",
            "### [ACTION_LOG]",
            sections.get("ACTION_LOG", ""),
        ]
        self.path.write_text("\n".join(lines), encoding="utf-8")

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
        s["ACTION_LOG"] = (s.get("ACTION_LOG", "") + f"\n[{ts}] {entry}").strip()
        self._write_all(s)

    def write_context(self, ctx: str) -> None:
        """Updates the persistent context section."""
        s = self.read()
        s["CONTEXT"] = ctx
        self._write_all(s)

    def add_workspace(self, path: str) -> None:
        s = self.read()
        s["WORKSPACE"] = (s.get("WORKSPACE", "") + f"\n- {path}").strip()
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
        tasks, content = [], self.path.read_text(encoding="utf-8")
        agent_part = content.split("## [AGENT_PROGRESS]")[-1]
        for line in agent_part.splitlines():
            if line.strip().startswith("- [ ]"):
                m = re.search(r"TASK-(\w+): (.+?) \[attempts: (\d+)\]", line)
                if m:
                    tasks.append({"id": m.group(1), "description": m.group(2), "attempts": int(m.group(3))})

        if tasks:
            return tasks

        # Fallback to User Queue if no agent tasks are active
        try:
            user_part = content.split("## [USER_QUEUE]")[1].split("---")[0]
            for line in user_part.splitlines():
                if line.strip().startswith("- [ ]"):
                    m = re.search(r"GOAL-(\w+): (.+)", line)
                    if m:
                        return [
                            {
                                "id": f"GOAL-{m.group(1)}",
                                "description": m.group(2).strip(),
                                "attempts": 0,
                                "is_synthetic": True,
                            }
                        ]
        except IndexError:
            pass
        return []

    def get_all_task_ids(self) -> set[str]:
        return set(re.findall(r"TASK-(\d+)", self.path.read_text(encoding="utf-8"))) if self.path.exists() else set()

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
            if f"TASK-{tid}:" in line:
                m = re.search(r"\[attempts: (\d+)\]", line)
                new_att = (int(m.group(1)) if m else 0) + 1
                new_line = re.sub(r"\[attempts: \d+\]", f"[attempts: {new_att}]", line)
                if new_att >= self.max_attempts:
                    new_line = new_line.replace("- [ ]", "- [BLOCKED]")
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