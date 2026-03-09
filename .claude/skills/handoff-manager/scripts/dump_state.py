#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
handoff-manager/scripts/dump_state.py (v 1.2)
Saves the complete session state before termination.

Usage:
    uv run python .claude/skills/handoff-manager/scripts/dump_state.py
    uv run python .claude/skills/handoff-manager/scripts/dump_state.py --reason "HALT: max attempts"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
SESSION_PATH = ROOT / "agent_context" / "SESSION.md"
TASKS_PATH = ROOT / "agent_context" / "TASKS.md"
ARCHIVE_DIR = ROOT / ".claude" / "cache"
TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "template.md"


def read_session() -> dict[str, str]:
    if not SESSION_PATH.exists():
        return {}
    content = SESSION_PATH.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current_key = None
    current_lines: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^## \[(\w+)\]$", line)
        if match:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1)
            current_lines = []
        elif current_key:
            current_lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def read_tasks() -> dict[str, list[str]]:
    if not TASKS_PATH.exists():
        return {"active": [], "completed": [], "blocked": []}
    active, completed, blocked = [], [], []
    for line in TASKS_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [ ]"):
            active.append(line)
        elif line.startswith("- [x]"):
            completed.append(line)
        elif line.startswith("- [BLOCKED]"):
            blocked.append(line)
    return {"active": active, "completed": completed, "blocked": blocked}


def get_last_actions(action_log: str, n: int = 10) -> list[str]:
    # E741 Fix: Renamed ambiguous 'l' to 'line'
    lines = [line for line in action_log.splitlines() if line.strip()]
    return lines[-n:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Handoff-Manager: session state dump")
    parser.add_argument("--reason", default="Manual handoff", help="Reason for state saving")
    args = parser.parse_args()

    print("💾 Handoff-Manager: saving state...")

    session = read_session()
    tasks = read_tasks()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    handoff_path = ARCHIVE_DIR / f"handoff-{timestamp}.md"
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    last_actions = get_last_actions(session.get("ACTION_LOG", ""))

    lines = [
        f"# Handoff — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Reason:** {args.reason}",
        "",
        "## End-of-session state",
        f"- STATE: `{session.get('STATE', 'UNKNOWN')}`",
        "",
        "## Context",
        session.get("CONTEXT", "No context provided."),
        "",
        "## Workspace",
        session.get("WORKSPACE", "No files tracked."),
        "",
        "## Tasks",
        f"**Active ({len(tasks['active'])}):**",
    ]
    # PERF401 Fix: Use extend for list transformation
    lines.extend(f"  {t}" for t in tasks["active"])

    # PERF401 Fix: Optimized list extension
    lines.append(f"\n**Completed ({len(tasks['completed'])}):**")
    lines.extend(f"  {t}" for t in tasks["completed"])

    if tasks["blocked"]:
        lines.append(f"\n**Blocked ({len(tasks['blocked'])}):**")
        lines.extend(f"  {t}" for t in tasks["blocked"])

    lines += [
        "",
        "## Last actions (max 10)",
    ]
    # PERF401 Fix: Optimized list extension
    lines.extend(f"  {action}" for action in last_actions)

    lines += [
        "",
        "---",
        "## Instructions for new session",
        "1. Read this handoff file",
        "2. Check the active tasks listed above",
        "3. Run `make validate` and `make status`",
        "4. Continue from the last active task",
    ]

    handoff_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Handoff saved: {handoff_path.relative_to(ROOT)}")
    print(f"   Active tasks: {len(tasks['active'])}")
    print(f"   Completed: {len(tasks['completed'])}")
    print("RESULT:HANDOFF_OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
