#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
context-compressor/scripts/summarize.py (v 1.4)
Compresses ACTION_LOG in SESSION.md by removing noise and keeping essential facts.
Fixed recursive header spamming (Anti-Snowball Patch).
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Paths configuration
ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
SESSION_PATH = ROOT / "agent_context" / "SESSION.md"
ARCHIVE_DIR = ROOT / ".claude" / "cache"

# ==========================================
# RULES: Fact vs. Noise
# ==========================================
NOISE_PATTERNS = [
    r"Agent \w+ finished\. Skills: \d+",
    r"Token budget: \d+/\d+",
    r"Mock response for agent",
    r"STATE → \w+",
    r"\[COMPRESSED:.*?\]",  # ARCHITECT FIX: Delete old English headers
    r"\[KOMPRIMOVANÉ:.*?\]",  # ARCHITECT FIX: Delete old Slovak headers
]

IMPORTANT_PATTERNS = [
    r"HALT",
    r"TASK-\w+.*(completed|finished)",
    r"TASK-\w+.*BLOCKED",
    r"Mypy error",
    r"API error",
    r"attempts.*[23]",
    r"Pipeline.*(completed|finished)",
    r"RESULT:",
    r"STAGE_SUCCESS",
    r"STAGE_FAIL",
]


def read_session_data() -> dict[str, str]:
    """Extracts all sub-sections from SESSION.md using robust regex."""
    if not SESSION_PATH.exists():
        print(f"❌ SESSION.md not found: {SESSION_PATH}")
        sys.exit(1)

    content = SESSION_PATH.read_text(encoding="utf-8")
    sections: dict[str, str] = {}

    # Extract sub-sections using the same logic as SessionManager
    patterns = {
        "CONTEXT": r"###\s*\[?\s*CONTEXT\s*\]?\n(.*?)(?=\n###|$)",
        "WORKSPACE": r"###\s*\[?\s*WORKSPACE\s*\]?\n(.*?)(?=\n###|$)",
        "STATE": r"###\s*\[?\s*STATE\s*\]?\n(.*?)(?=\n###|$)",
        "FEEDBACK": r"###\s*\[?\s*FEEDBACK\s*\]?\n(.*?)(?=\n###|$)",
        "ACTION_LOG": r"###\s*\[?\s*ACTION_LOG\s*\]?\n(.*?)(?=\n###|$)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        sections[key] = match.group(1).strip() if match else ""

    return sections


def write_session_data(sections: dict[str, str]) -> None:
    """Rebuilds SESSION.md in canonical format with compressed logs."""
    content = (
        "# Agent-CI-Lens SESSION\n\n"
        "##[USER_SECTION]\n"
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
    SESSION_PATH.write_text(content, encoding="utf-8")


def compress_action_log(action_log: str) -> tuple[str, dict[str, int]]:
    """Filters noise and deduplicates records in the action log."""
    lines = [line for line in action_log.splitlines() if line.strip()]
    if not lines:
        return action_log, {"original": 0, "compressed": 0, "removed": 0}

    important_lines: list[str] = []
    noise_count = 0

    for line in lines:
        is_important = any(re.search(p, line, re.IGNORECASE) for p in IMPORTANT_PATTERNS)
        is_noise = any(re.search(p, line, re.IGNORECASE) for p in NOISE_PATTERNS)

        if is_noise:
            noise_count += 1
        elif is_important:
            important_lines.append(line)
        else:
            # Keep neutral lines (like skill output headers)
            important_lines.append(line)

    # Always preserve the very last activity
    if lines and (not important_lines or important_lines[-1] != lines[-1]):  # noqa: SIM102
        if not any(re.search(p, lines[-1], re.IGNORECASE) for p in NOISE_PATTERNS):
            important_lines.append(lines[-1])

    # Deduplication
    seen = set()
    deduped: list[str] = []
    for line in important_lines:
        # Normalize line by removing timestamp for comparison
        key = re.sub(r"\[\d{2}:\d{2}\]", "", line).strip()
        if key not in seen:
            seen.add(key)
            deduped.append(line)

    timestamp = datetime.now().strftime("%H:%M")
    header = f"[{timestamp}][COMPRESSED: {len(lines)} -> {len(deduped)} lines, {noise_count} noise records removed]"
    compressed = f"{header}\n" + "\n".join(deduped)

    return compressed, {
        "original": len(lines),
        "compressed": len(deduped),
        "removed": noise_count,
    }


def archive_log(action_log: str) -> Path:
    """Archives original log before compression."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = ARCHIVE_DIR / f"session-archive-{ts}.md"
    archive_path.write_text(f"# Log Archive {ts}\n\n{action_log}", encoding="utf-8")
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Context-Compressor: SESSION.md optimizer")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("🗜️  Context-Compressor (v1.4)")

    sections = read_session_data()
    action_log = sections.get("ACTION_LOG", "")

    if not action_log:
        print("   ℹ️  ACTION_LOG is empty or could not be parsed.")  # noqa: RUF001
        print("RESULT:COMPRESS_SKIP")
        sys.exit(0)

    print(f"   DEBUG: Processing {len(action_log.splitlines())} lines.")

    compressed_log, stats = compress_action_log(action_log)

    if not args.dry_run:
        archive_log(action_log)
        sections["ACTION_LOG"] = compressed_log
        write_session_data(sections)
        print(f"✅ SESSION.md updated. Removed {stats['removed']} lines.")
        print("RESULT:COMPRESS_OK")
    else:
        print(f"[DRY RUN] Would remove {stats['removed']} lines.")
        print("RESULT:COMPRESS_DRY_RUN")


if __name__ == "__main__":
    main()
