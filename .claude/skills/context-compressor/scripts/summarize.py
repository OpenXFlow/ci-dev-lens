#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
context-compressor/scripts/summarize.py
Komprimuje ACTION_LOG v SESSION.md a archivuje pôvodný obsah.

Použitie:
    uv run python .claude/skills/context-compressor/scripts/summarize.py
    uv run python .claude/skills/context-compressor/scripts/summarize.py --dry-run
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
SESSION_PATH = ROOT / "docs" / "SESSION.md"
ARCHIVE_DIR = ROOT / ".claude" / "cache"


# ==========================================
# PRAVIDLÁ: Čo je dôležitý fakt vs šum
# (definované v references/memory-map.md)
# ==========================================
NOISE_PATTERNS = [
    r"Agent \w+ dokončil\. Skilly: \d+",   # "Agent queen dokončil. Skilly: 0"
    r"Token budget: \d+/\d+",              # "Token budget: 1234/8000"
    r"Mock odpoveď pre agenta",             # Mock logy
    r"STATE → \w+",                        # Stavové prechody (redundantné)
]

IMPORTANT_PATTERNS = [
    r"HALT",                               # Akýkoľvek HALT záznam
    r"TASK-\w+.*dokončen",                 # Dokončené tasky
    r"TASK-\w+.*BLOCKED",                  # Zablokované tasky
    r"Mypy chyba",                         # Mypy chyby
    r"API chyba",                          # API chyby
    r"attempts.*[23]",                     # Vysoký počet pokusov
    r"Pipeline.*dokončen",                 # Pipeline výsledky
    r"RESULT:",                            # Výsledky skillov
]


def read_session() -> dict[str, str]:
    """Načíta SESSION.md a vráti sekcie."""
    if not SESSION_PATH.exists():
        print(f"❌ SESSION.md nenájdený: {SESSION_PATH}")
        sys.exit(1)

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


def write_session(sections: dict[str, str]) -> None:
    """Zapíše SESSION.md."""
    lines = ["# Aktuálna Pracovná Relácia", ""]
    for key in ["STATE", "CONTEXT", "WORKSPACE", "ACTION_LOG"]:
        lines.append(f"## [{key}]")
        lines.append(sections.get(key, ""))
        lines.append("")
    SESSION_PATH.write_text("\n".join(lines))


def is_noise(line: str) -> bool:
    """Vráti True ak je riadok šum."""
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def is_important(line: str) -> bool:
    """Vráti True ak je riadok dôležitý fakt."""
    for pattern in IMPORTANT_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def compress_action_log(action_log: str) -> tuple[str, dict]:
    """
    Komprimuje ACTION_LOG.
    Vráti (komprimovaný_log, štatistiky).
    """
    lines = [l for l in action_log.splitlines() if l.strip()]
    if not lines:
        return action_log, {"original": 0, "compressed": 0, "removed": 0}

    important_lines = []
    noise_count = 0

    for line in lines:
        if is_important(line):
            important_lines.append(line)
        elif is_noise(line):
            noise_count += 1
        else:
            # Neutrálne riadky — zachovaj posledných 5
            important_lines.append(line)

    # Zachovaj vždy posledný riadok (najnovšia akcia)
    if lines and (not important_lines or important_lines[-1] != lines[-1]):
        important_lines.append(lines[-1])

    # Deduplikácia
    seen = set()
    deduped = []
    for line in important_lines:
        key = re.sub(r"\[\d{2}:\d{2}\]", "", line).strip()
        if key not in seen:
            seen.add(key)
            deduped.append(line)

    timestamp = datetime.now().strftime("%H:%M")
    header = f"[{timestamp}] [KOMPRIMOVANÉ: {len(lines)} → {len(deduped)} riadkov, {noise_count} šum odstránený]"

    compressed = header + "\n" + "\n".join(deduped)

    return compressed, {
        "original": len(lines),
        "compressed": len(deduped),
        "removed": noise_count,
    }


def archive_log(action_log: str) -> Path:
    """Archivuje pôvodný ACTION_LOG."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = ARCHIVE_DIR / f"session-archive-{timestamp}.md"

    content = f"# Session Archive — {timestamp}\n\n"
    content += "## Pôvodný ACTION_LOG\n\n"
    content += action_log

    archive_path.write_text(content)
    return archive_path


def count_tokens(text: str) -> int:
    """Heuristický odhad tokenov."""
    return int(len(text.split()) * 1.5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Context-Compressor: SESSION.md zhrnutie")
    parser.add_argument("--dry-run", action="store_true",
                        help="Zobraz čo by sa stalo bez skutočnej zmeny")
    args = parser.parse_args()

    print("🗜️  Context-Compressor")
    print(f"   Session: {SESSION_PATH.relative_to(ROOT)}")

    sections = read_session()
    action_log = sections.get("ACTION_LOG", "")

    if not action_log.strip():
        print("   ℹ️  ACTION_LOG je prázdny — nič na komprimovanie")
        print("RESULT:COMPRESS_SKIP")
        sys.exit(0)

    tokens_before = count_tokens(action_log)
    compressed_log, stats = compress_action_log(action_log)
    tokens_after = count_tokens(compressed_log)
    saved = tokens_before - tokens_after

    print(f"\n📊 Analýza:")
    print(f"   Riadky:  {stats['original']} → {stats['compressed']}")
    print(f"   Šum:     {stats['removed']} riadkov odstránených")
    print(f"   Tokeny:  ~{tokens_before} → ~{tokens_after} (ušetrené: ~{saved})")

    if args.dry_run:
        print("\n[DRY RUN] Žiadne zmeny neboli vykonané")
        print("\nKomprimovaný log by bol:")
        print("-" * 40)
        print(compressed_log)
        print("RESULT:COMPRESS_DRY_RUN")
        sys.exit(0)

    # Archivuj pôvodný log
    archive_path = archive_log(action_log)
    print(f"\n📦 Archivované: {archive_path.relative_to(ROOT)}")

    # Zapíš komprimovanú verziu
    sections["ACTION_LOG"] = compressed_log
    write_session(sections)

    print(f"✅ SESSION.md aktualizovaný")
    print(f"RESULT:COMPRESS_OK:saved={saved}tokens")
    sys.exit(0)


if __name__ == "__main__":
    main()
