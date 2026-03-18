#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/managers.py
State managers for agent_context (v 1.11.4 Goal-Based Branching & Multi-line GOAL Parser).
Surgical Patch: Definitive Mypy type fix for multi-line parser using cast.
"""

import re
from datetime import datetime
from typing import Any, cast

from .utils import ROOT, log

# Sémantický Parser pre Tasky (Toleruje chýbajúce medzery, rôzne zátvorky a stavy)
TASK_PATTERN = re.compile(
    r"^\s*-\s*\[\s*([^\]]*)\s*\]\s*(GOAL|TASK)-([\w\-]+):\s*(.+)$",
    re.IGNORECASE,
)


class SessionManager:
    """Manages the persistent state and action log in agent_context/SESSION.md."""

    def __init__(self) -> None:
        self.path = ROOT / "agent_context" / "SESSION.md"
        self.user_section_cache: str = ""

    def read(self) -> dict[str, str]:
        """Reads session sections using robust regex parsing (Header Tolerance)."""
        if not self.path.exists():
            return {}

        content = self.path.read_text(encoding="utf-8")
        sections: dict[str, str] = {}

        user_match = re.search(r"##\s*\[?\s*USER_SECTION\s*\]?(.*?)---", content, re.DOTALL | re.IGNORECASE)
        self.user_section_cache = user_match.group(1).strip() if user_match else ""

        ctx_match = re.search(
            r"###\s*\[?\s*CONTEXT\s*\]?\n(.*?)(?=\n###|$)",
            self.user_section_cache,
            re.DOTALL | re.IGNORECASE,
        )
        sections["CONTEXT"] = ctx_match.group(1).strip() if ctx_match else ""

        wrk_match = re.search(
            r"###\s*\[?\s*WORKSPACE\s*\]?\n(.*?)(?=\n###|$)",
            self.user_section_cache,
            re.DOTALL | re.IGNORECASE,
        )
        sections["WORKSPACE"] = wrk_match.group(1).strip() if wrk_match else ""

        agent_match = re.search(r"##\s*\[?\s*AGENT_SECTION\s*\]?(.*)", content, re.DOTALL | re.IGNORECASE)
        agent_part = agent_match.group(1) if agent_match else ""

        state_match = re.search(
            r"###\s*\[?\s*STATE\s*\]?\n(.*?)(?=\n###|$)",
            agent_part,
            re.DOTALL | re.IGNORECASE,
        )
        sections["STATE"] = state_match.group(1).strip() if state_match else "IDLE"

        fb_match = re.search(
            r"###\s*\[?\s*FEEDBACK\s*\]?\n(.*?)(?=\n###|$)",
            agent_part,
            re.DOTALL | re.IGNORECASE,
        )
        sections["FEEDBACK"] = fb_match.group(1).strip() if fb_match else ""

        log_match = re.search(
            r"###\s*\[?\s*ACTION_LOG\s*\]?\n(.*?)(?=\n###|$)",
            agent_part,
            re.DOTALL | re.IGNORECASE,
        )
        sections["ACTION_LOG"] = log_match.group(1).strip() if log_match else ""

        return sections

    def _write_all(self, sections: dict[str, str]) -> None:
        """Atomically writes all sections back using CANONICAL formatting."""
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
    """Manages technical tasks and goals using a robust Semantic Parser."""

    def __init__(self) -> None:
        self.path = ROOT / "agent_context" / "TASKS.md"
        self.max_attempts = 3

    def _split_sections(self, content: str) -> tuple[str, str]:
        """Robustly splits content into User and Agent sections."""
        parts = re.split(
            r"^##\s*\[?\s*AGENT_PROGRESS\s*\]?",
            content,
            maxsplit=1,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        agent_part = parts[1] if len(parts) > 1 else ""
        user_part_raw = parts[0]

        q_parts = re.split(
            r"^##\s*\[?\s*USER_QUEUE\s*\]?",
            user_part_raw,
            maxsplit=1,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        user_queue = q_parts[1] if len(q_parts) > 1 else user_part_raw

        return user_queue, agent_part

    def get_current_goal_id(self) -> str | None:
        """Returns the ID of the first pending GOAL from USER_QUEUE."""
        if not self.path.exists():
            return None

        content = self.path.read_text(encoding="utf-8")
        user_queue, _ = self._split_sections(content)
        user_queue_clean = re.split(r"^---", user_queue, flags=re.MULTILINE)[0]

        for line in user_queue_clean.splitlines():
            if match := TASK_PATTERN.match(line):
                status = match.group(1).strip().lower()
                t_type = match.group(2).upper()
                t_id = match.group(3)

                if t_type == "GOAL" and status == "":
                    return t_id

        return None

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """Extracts the first pending task or goal using tolerant regex & block parsing."""
        if not self.path.exists():
            return []

        content = self.path.read_text(encoding="utf-8")
        user_queue, agent_part = self._split_sections(content)

        # 1. Search in AGENT_PROGRESS (Strict Single-Line Rules)
        tasks: list[dict[str, Any]] = []
        for line in agent_part.splitlines():
            if match := TASK_PATTERN.match(line):
                status = match.group(1).strip().lower()
                t_type = match.group(2).upper()
                t_id = match.group(3)
                raw_desc = match.group(4)

                if t_type == "TASK" and status == "":
                    att_match = re.search(r"\[attempts:\s*(\d+)\]", raw_desc)
                    attempts = int(att_match.group(1)) if att_match else 0
                    clean_desc = re.sub(r"\s*\[attempts:\s*\d+\]", "", raw_desc).strip()

                    tasks.append(
                        {
                            "id": t_id,
                            "description": clean_desc,
                            "attempts": attempts,
                            "is_synthetic": False,
                        }
                    )

        if tasks:
            return tasks

        # 2. Fallback to USER_QUEUE (Multi-Line Block Parsing for Constraints & Metrics)
        user_queue_clean = re.split(r"^---", user_queue, flags=re.MULTILINE)[0]
        current_goal = None

        for line in user_queue_clean.splitlines():
            if match := TASK_PATTERN.match(line):
                if current_goal:
                    break

                status = match.group(1).strip().lower()
                t_type = match.group(2).upper()
                t_id = match.group(3)
                raw_desc = match.group(4)

                if t_type == "GOAL" and status == "":
                    current_goal = {
                        "id": f"GOAL-{t_id}",
                        "description": raw_desc.strip(),
                        "attempts": 0,
                        "is_synthetic": True,
                    }
            elif current_goal and line.strip():
                # SURGICAL PATCH: Explicitly cast to str to satisfy Mypy.
                current_goal["description"] = cast(str, current_goal["description"]) + f"\n{line}"

        if current_goal:
            return [current_goal]

        return []

    def get_all_task_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        # BIMETRIC SHIELD FIX: Protect both GOAL and TASK IDs from deletion
        return set(re.findall(r"(?:TASK|GOAL)-([\w\-]+)", self.path.read_text(encoding="utf-8")))

    def are_all_tasks_completed(self) -> bool:
        """Sémanticky overí, či sú všetky vygenerované úlohy uzavreté."""
        if not self.path.exists():
            return False

        content = self.path.read_text(encoding="utf-8")
        _, agent_part = self._split_sections(content)

        tasks_found = 0
        for line in agent_part.splitlines():
            if match := TASK_PATTERN.match(line):
                t_type = match.group(2).upper()
                if t_type == "TASK":
                    tasks_found += 1
                    status = match.group(1).strip().lower()
                    if status not in {"x", "blocked", "!"}:
                        return False

        return tasks_found > 0

    def _update_status(self, target_type: str, target_id: str, new_status: str) -> None:
        """Univerzálna metóda pre tichú opravu (Canonical Formatting) a zmenu stavu."""
        if not self.path.exists():
            return

        lines = self.path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if match := TASK_PATTERN.match(line):
                t_type = match.group(2).upper()
                t_id = match.group(3)
                raw_desc = match.group(4)

                if t_type == target_type and (t_id == target_id or t_id == str(target_id).zfill(3)):
                    lines[i] = f"- [{new_status}] {t_type}-{t_id}: {raw_desc}"

        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def mark_completed(self, tid: str) -> None:
        self._update_status("TASK", tid, "x")

    def mark_goal_completed(self, gid: str) -> None:
        self._update_status("GOAL", gid, "x")

    def increment_attempts(self, tid: str, error: str) -> int:
        """Inkrementuje pokusy a v prípade presiahnutia limitu označí task ako BLOCKED."""
        if not self.path.exists():
            return 0

        lines = self.path.read_text(encoding="utf-8").splitlines()
        new_att = 0

        for i, line in enumerate(lines):
            if match := TASK_PATTERN.match(line):
                status = match.group(1).strip()
                t_type = match.group(2).upper()
                t_id = match.group(3)
                raw_desc = match.group(4)

                if t_type == "TASK" and (t_id == tid or t_id == str(tid).zfill(3)):
                    if att_match := re.search(r"\[attempts:\s*(\d+)\]", raw_desc):
                        current_att = int(att_match.group(1))
                        new_att = current_att + 1
                        attempts_str = f"[attempts: {new_att}]"
                        raw_desc = f"{raw_desc[: att_match.start()]}{attempts_str}{raw_desc[att_match.end() :]}"
                    else:
                        new_att = 1
                        raw_desc = f"{raw_desc}[attempts: {new_att}]"

                    new_status = status if status else " "
                    if new_att >= self.max_attempts:
                        new_status = "BLOCKED"
                        raw_desc = f"{raw_desc} -> Failed: {error}"

                    lines[i] = f"-[{new_status}] {t_type}-{t_id}: {raw_desc}"
                    break

        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
