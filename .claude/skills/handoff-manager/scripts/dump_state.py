#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
handoff-manager/scripts/dump_state.py
Uloží kompletný stav session pred ukončením.

Použitie:
    uv run python .claude/skills/handoff-manager/scripts/dump_state.py
    uv run python .claude/skills/handoff-manager/scripts/dump_state.py --reason "HALT: max attempts"
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
SESSION_PATH = ROOT / "docs" / "SESSION.md"
TASKS_PATH = ROOT / "docs" / "TASKS.md"
ARCHIVE_DIR = ROOT / ".claude" / "cache"
TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "template.md"


def read_session() -> dict[str, str]:
    if not SESSION_PATH.exists():
        return {}
    content = SESSION_PATH.read_text()
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
    for line in TASKS_PATH.read_text().splitlines():
        if line.startswith("- [ ]"):
            active.append(line)
        elif line.startswith("- [x]"):
            completed.append(line)
        elif line.startswith("- [BLOCKED]"):
            blocked.append(line)
    return {"active": active, "completed": completed, "blocked": blocked}


def get_last_actions(action_log: str, n: int = 10) -> list[str]:
    lines = [l for l in action_log.splitlines() if l.strip()]
    return lines[-n:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Handoff-Manager: dump stavu session")
    parser.add_argument("--reason", default="Manuálny handoff", help="Dôvod uloženia")
    args = parser.parse_args()

    print("💾 Handoff-Manager: ukladám stav...")

    session = read_session()
    tasks = read_tasks()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    handoff_path = ARCHIVE_DIR / f"handoff-{timestamp}.md"
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    last_actions = get_last_actions(session.get("ACTION_LOG", ""))

    lines = [
        f"# Handoff — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Dôvod:** {args.reason}",
        "",
        "## Stav pri ukončení",
        f"- STATE: `{session.get('STATE', 'UNKNOWN')}`",
        "",
        "## Kontext",
        session.get("CONTEXT", "Žiadny kontext."),
        "",
        "## Workspace",
        session.get("WORKSPACE", "Žiadne súbory."),
        "",
        "## Tasky",
        f"**Aktívne ({len(tasks['active'])}):**",
    ]
    for t in tasks["active"]:
        lines.append(f"  {t}")

    lines += [
        f"\n**Dokončené ({len(tasks['completed'])}):**",
    ]
    for t in tasks["completed"]:
        lines.append(f"  {t}")

    if tasks["blocked"]:
        lines += [f"\n**Zablokované ({len(tasks['blocked'])}):**"]
        for t in tasks["blocked"]:
            lines.append(f"  {t}")

    lines += [
        "",
        "## Posledné akcie (max 10)",
    ]
    for action in last_actions:
        lines.append(f"  {action}")

    lines += [
        "",
        "---",
        "## Inštrukcie pre novú session",
        "1. Prečítaj tento súbor",
        "2. Skontroluj aktívne tasky vyššie",
        "3. Spusti `make validate` a `make status`",
        "4. Pokračuj od posledného aktívneho tasku",
    ]

    handoff_path.write_text("\n".join(lines))
    print(f"✅ Handoff uložený: {handoff_path.relative_to(ROOT)}")
    print(f"   Aktívne tasky: {len(tasks['active'])}")
    print(f"   Dokončené: {len(tasks['completed'])}")
    print("RESULT:HANDOFF_OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
