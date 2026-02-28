#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
testing-pro/scripts/coverage.py
Kontrola coverage pre Agent-CI-Lens pipeline.

Použitie:
    uv run python .claude/skills/testing-pro/scripts/coverage.py
    uv run python .claude/skills/testing-pro/scripts/coverage.py --min 80
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
MIN_COVERAGE = 80


def run_coverage(target: str, min_coverage: int) -> dict:
    """Spustí pytest s coverage a vráti výsledok."""
    cmd = [
        "uv", "run", "pytest",
        f"--cov={target}",
        "--cov-report=term-missing",
        f"--cov-fail-under={min_coverage}",
        "-q",
        "--no-header",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "TIMEOUT: Coverage check prekročil 120 sekúnd",
        }


def parse_coverage_output(stdout: str) -> list[dict]:
    """Extrahuje coverage percentá z výstupu."""
    modules = []
    in_coverage_section = False

    for line in stdout.splitlines():
        if "Name" in line and "Stmts" in line and "Cover" in line:
            in_coverage_section = True
            continue

        if in_coverage_section and line.startswith("---"):
            continue

        if in_coverage_section and line.strip() and not line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    pct_str = parts[-1].replace("%", "")
                    pct = int(pct_str)
                    modules.append({
                        "name": parts[0],
                        "coverage": pct,
                        "low": pct < MIN_COVERAGE,
                    })
                except ValueError:
                    pass

        if line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    pct_str = parts[-1].replace("%", "")
                    total_pct = int(pct_str)
                    return modules, total_pct
                except ValueError:
                    pass

    return modules, 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Testing-Pro: coverage checker")
    parser.add_argument("--target", default="src/", help="Cieľový modul pre coverage")
    parser.add_argument("--min", type=int, default=MIN_COVERAGE,
                        help=f"Minimálna coverage (default: {MIN_COVERAGE}%)")
    args = parser.parse_args()

    print(f"📊 Coverage check: {args.target} (min: {args.min}%)")

    # Kontrola pytest-cov
    check = subprocess.run(
        ["uv", "run", "python", "-c", "import pytest_cov"],
        cwd=ROOT, capture_output=True
    )
    if check.returncode != 0:
        print("⚠️  pytest-cov nie je nainštalovaný")
        print("   Pridaj do pyproject.toml: pytest-cov")
        print("RESULT:COVERAGE_SKIP")
        sys.exit(0)

    result = run_coverage(args.target, args.min)
    modules, total = parse_coverage_output(result["stdout"])

    print(f"\n📈 Coverage prehľad:")
    for mod in modules:
        icon = "✅" if not mod["low"] else "❌"
        print(f"   {icon} {mod['name']}: {mod['coverage']}%")

    print(f"\n   TOTAL: {total}%")

    low_modules = [m for m in modules if m["low"]]
    if low_modules:
        print(f"\n⚠️  Moduly s nízkym pokrytím (< {args.min}%):")
        for mod in low_modules:
            print(f"   • {mod['name']}: {mod['coverage']}%")

    print()
    if result["exit_code"] == 0:
        print(f"RESULT:COVERAGE_PASS:{total}%")
        sys.exit(0)
    else:
        print(f"RESULT:COVERAGE_FAIL:{total}%")
        sys.exit(1)


if __name__ == "__main__":
    main()
