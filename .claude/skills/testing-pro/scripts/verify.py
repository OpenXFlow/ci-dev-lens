#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
testing-pro/scripts/verify.py
Spúšťač pytest pre Agent-CI-Lens pipeline.

Použitie:
    uv run python .claude/skills/testing-pro/scripts/verify.py
    uv run python .claude/skills/testing-pro/scripts/verify.py --target tests/unit/
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()


def run_tests(target: str) -> dict:
    """Spustí pytest a vráti štruktúrovaný výsledok."""
    cmd = [
        "uv",
        "run",
        "pytest",
        target,
        "--tb=short",  # Krátky traceback
        "--no-header",
        "-q",  # Quiet mode — menej šumu
        "--json-report",  # JSON výstup
        "--json-report-file=.claude/cache/pytest-report.json",
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
            "stderr": "TIMEOUT: Testy bežali dlhšie ako 120 sekúnd",
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "ERROR: uv alebo pytest nie je nainštalovaný",
        }


def parse_report() -> dict:
    """Načíta JSON report z pytest-json-report."""
    report_path = ROOT / ".claude" / "cache" / "pytest-report.json"
    if not report_path.exists():
        return {}
    try:
        return json.loads(report_path.read_text())
    except json.JSONDecodeError:
        return {}


def summarize(result: dict, report: dict) -> dict:
    """Zostaví prehľad výsledkov."""
    passed = report.get("summary", {}).get("passed", 0)
    failed = report.get("summary", {}).get("failed", 0)
    errors = report.get("summary", {}).get("error", 0)
    total = report.get("summary", {}).get("total", 0)

    # Zber zlyhaných testov
    failed_tests = []
    for test in report.get("tests", []):
        if test.get("outcome") in ("failed", "error"):
            failed_tests.append(
                {
                    "name": test.get("nodeid", "unknown"),
                    "message": test.get("call", {}).get("longrepr", "")[:300],
                }
            )

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": total,
        "failed_tests": failed_tests,
        "success": result["exit_code"] == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Testing-Pro: pytest wrapper")
    parser.add_argument("--target", default="tests/", help="Cieľový adresár pre pytest")
    args = parser.parse_args()

    print(f"🧪 Spúšťam testy: {args.target}")

    # Kontrola či pytest-json-report je nainštalovaný
    check = subprocess.run(["uv", "run", "python", "-c", "import pytest_jsonreport"], cwd=ROOT, capture_output=True)
    if check.returncode != 0:
        # Fallback bez JSON reportu
        print("⚠️  pytest-json-report nie je nainštalovaný, používam základný výstup")
        result = subprocess.run(["uv", "run", "pytest", args.target, "--tb=short", "-q"], cwd=ROOT)
        if result.returncode == 0:
            print("RESULT:PASS")
        else:
            print("RESULT:TEST_FAIL")
        sys.exit(result.returncode)

    result = run_tests(args.target)
    report = parse_report()
    summary = summarize(result, report)

    print("\n📊 Results:")
    print(f"   Passed:  {summary['passed']}/{summary['total']}")
    print(f"   Failed:  {summary['failed']}")
    print(f"   Errors:  {summary['errors']}")

    if summary["failed_tests"]:
        print("\n❌ Failed tests:")
        for t in summary["failed_tests"][:5]:  # Max 5 pre kontextové okno
            print(f"   • {t['name']}")
            if t["message"]:
                # Prvý riadok chybovej správy
                first_line = t["message"].splitlines()[0] if t["message"] else ""
                print(f"     {first_line}")

    print()
    if summary["success"]:
        print("RESULT:PASS")
        sys.exit(0)
    else:
        print("RESULT:TEST_FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
