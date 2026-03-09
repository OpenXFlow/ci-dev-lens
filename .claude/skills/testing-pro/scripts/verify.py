#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
testing-pro/scripts/verify.py (v 1.2)
Pytest runner for the Agent-CI-Lens pipeline.

Usage:
    uv run python .claude/skills/testing-pro/scripts/verify.py
    uv run python .claude/skills/testing-pro/scripts/verify.py --target tests/unit/
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()

# S607 Fix: Resolve absolute path for the 'uv' executable
UV_PATH = shutil.which("uv") or "uv"


def run_tests(target: str) -> dict[str, Any]:
    """Runs pytest and returns a structured result."""
    cmd = [
        UV_PATH,
        "run",
        "pytest",
        target,
        "--tb=short",  # Short traceback
        "--no-header",
        "-q",  # Quiet mode — less verbose
        "--json-report",  # JSON output
        "--json-report-file=.claude/cache/pytest-report.json",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "TIMEOUT: Tests ran longer than 120 seconds",
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"ERROR: '{UV_PATH}' or 'pytest' is not installed",
        }
    else:
        # TRY300 Fix: Moved return statement to the else block
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


def parse_report() -> dict[str, Any]:
    """Loads the JSON report from pytest-json-report."""
    report_path = ROOT / ".claude" / "cache" / "pytest-report.json"
    if not report_path.exists():
        return {}
    try:
        # SURGICAL PATCH: Cast return type to satisfy Mypy
        return cast(dict[str, Any], json.loads(report_path.read_text()))
    except json.JSONDecodeError:
        return {}


def summarize(result: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Builds a summary of the test results."""
    passed = report.get("summary", {}).get("passed", 0)
    failed = report.get("summary", {}).get("failed", 0)
    errors = report.get("summary", {}).get("error", 0)
    total = report.get("summary", {}).get("total", 0)

    # PERF401 Fix: Used list comprehension instead of manual loop
    failed_tests = [
        {
            "name": test.get("nodeid", "unknown"),
            "message": test.get("call", {}).get("longrepr", "")[:300],
        }
        for test in report.get("tests", [])
        if test.get("outcome") in ("failed", "error")
    ]

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
    parser.add_argument("--target", default="tests/", help="Target directory for pytest")
    args = parser.parse_args()

    print(f"🧪 Running tests: {args.target}")

    # S607 Fix: Use UV_PATH instead of raw string
    check = subprocess.run(
        [UV_PATH, "run", "python", "-c", "import pytest_jsonreport"], cwd=ROOT, capture_output=True, check=False
    )

    if check.returncode != 0:
        # Fallback without JSON report
        print("⚠️  pytest-json-report not found, using basic output")
        # S607 Fix: Use UV_PATH instead of raw string
        fallback_proc = subprocess.run(
            [UV_PATH, "run", "pytest", args.target, "--tb=short", "-q"], cwd=ROOT, check=False
        )
        if fallback_proc.returncode == 0:
            print("RESULT:PASS")
        else:
            print("RESULT:TEST_FAIL")
        sys.exit(fallback_proc.returncode)

    result = run_tests(args.target)
    report = parse_report()
    summary = summarize(result, report)

    print("\n📊 Results:")
    print(f"   Passed:  {summary['passed']}/{summary['total']}")
    print(f"   Failed:  {summary['failed']}")
    print(f"   Errors:  {summary['errors']}")

    if summary["failed_tests"]:
        print("\n❌ Failed tests:")
        for t in summary["failed_tests"][:5]:  # Max 5 for context window
            print(f"   • {t['name']}")
            if t["message"]:
                # First line of the error message
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
