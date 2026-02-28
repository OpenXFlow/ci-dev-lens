#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
security-guard/scripts/scan.py
Skenuje kód pre secrets a nebezpečné vzory.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()

SECRET_PATTERNS = [
    (r'AIza[0-9A-Za-z\-_]{31,}', "Google API Key"),
    (r'gsk_[0-9A-Za-z]{32,}', "Groq API Key"),
    (r'github_pat_[0-9A-Za-z_]{36,}', "GitHub PAT"),
    (r'sk-[0-9A-Za-z]{32,}', "OpenAI API Key"),
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded password"),
    (r'(?i)(secret|token)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded secret/token"),
    (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----', "Private key"),
]

WARN_PATTERNS = [
    (r'\beval\s*\(', "eval() použitie"),
    (r'\bexec\s*\(', "exec() použitie"),
    (r'pickle\.loads?\s*\(', "pickle.load() - nebezpečná deserializácia"),
    (r'subprocess\.call\s*\(.+shell\s*=\s*True', "shell=True v subprocess"),
]

FORBIDDEN_FILES = [".env", "*.pem", "*.key", "id_rsa", "id_ed25519"]

def should_skip(path: Path) -> bool:
    skip_dirs = {".venv", "__pycache__", ".git", ".claude/cache"}
    for part in path.parts:
        if part in skip_dirs:
            return True
    return path.suffix in {".pyc", ".so", ".exe"}

def scan_file(path: Path) -> dict:
    secrets, warnings = [], []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"path": str(path), "secrets": [], "warnings": [], "error": True}

    for line_num, line in enumerate(content.splitlines(), 1):
        if "_CHANGE_ME" in line or "example" in line.lower():
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                secrets.append({"line": line_num, "label": label, "snippet": line.strip()[:80]})
        for pattern, label in WARN_PATTERNS:
            if re.search(pattern, line):
                warnings.append({"line": line_num, "label": label, "snippet": line.strip()[:80]})
    return {"path": str(path.relative_to(ROOT)), "secrets": secrets, "warnings": warnings, "error": False}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="src/")
    args = parser.parse_args()
    target = ROOT / args.target
    py_files = [f for f in target.rglob("*.py") if not should_skip(f)]
    
    all_secrets, all_warnings = [], []
    for f in py_files:
        res = scan_file(f)
        if res["secrets"]: all_secrets.append(res)
        if res["warnings"]: all_warnings.append(res)

    if all_secrets:
        print(f"❌ SECRETS NÁJDENÉ")
        print("RESULT:SECRET_FOUND")
        sys.exit(2)
    
    print("RESULT:PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()