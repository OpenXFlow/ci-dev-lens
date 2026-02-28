#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/validator.py - Comprehensive System Integrity Shield (v 8.0 Pydantic).
Refactored to rely on Pydantic schemas for deep validation.
"""

import sys
from pathlib import Path

from pydantic import ValidationError

# Correct import path from agent_core
try:
    from router_core.utils import load_agents_registry, load_env, load_orchestrator_config
except ImportError:
    # Fallback for direct execution
    sys.path.append(str(Path(__file__).parent.parent))
    from agent_core.router_core.utils import load_agents_registry, load_env, load_orchestrator_config

# Dynamic detection of project root (parent of agent_core)
ROOT = Path(__file__).parent.parent.resolve()

ERRORS: list[str] = []
WARNINGS: list[str] = []


def ok(msg: str) -> None:
    """Log a successful validation step."""
    print(f"  ✅ {msg}")


def warn(msg: str) -> None:
    """Log a warning that doesn't block execution."""
    print(f"  ⚠️  {msg}")
    WARNINGS.append(msg)


def fail(msg: str) -> None:
    """Log a critical error that blocks execution."""
    print(f"  ❌ {msg}")
    ERRORS.append(msg)


# ==========================================
# 1. ENV VALIDATION (via Pydantic)
# ==========================================
def validate_env() -> None:
    """Check .env file using EnvConfig schema."""
    print("\n🔑 Checking .env keys (Pydantic)...")
    try:
        config = load_env()

        # Check credentials
        if not config.credentials:
            warn("No API keys found (MOCK mode only).")
        else:
            for provider in config.credentials:
                ok(f"Credentials loaded for: {provider}")

        if config.GITHUB_TOKEN:
            ok("GITHUB_TOKEN is configured")
        else:
            warn("GITHUB_TOKEN is missing (needed for GHA v2)")

    except ValidationError as e:
        fail(f"Environment validation failed:\n{e}")
    except Exception as e:
        fail(f"Unexpected env error: {e}")


# ==========================================
# 2. CONFIG VALIDATION (via Pydantic)
# ==========================================
def validate_config() -> None:
    """Check agent_orchestrator.json using OrchestratorConfigModel."""
    print("\n⚙️  Checking agent_orchestrator.json...")
    try:
        load_orchestrator_config()
        ok("Orchestrator configuration is valid")
    except FileNotFoundError:
        fail("agent_orchestrator.json is missing")
    except ValidationError as e:
        fail(f"Config validation failed:\n{e}")
    except Exception as e:
        fail(f"Config error: {e}")


# ==========================================
# 3. AGENTS VALIDATION (via Pydantic)
# ==========================================
def validate_agents() -> None:
    """Check .agents/agent_registry.json using AgentsRegistryModel."""
    print("\n🤖 Checking agent_registry.json...")
    try:
        registry = load_agents_registry()
        count = len(registry.profiles)
        ok(f"Agent registry is valid ({count} profiles loaded)")

        required = ["queen", "developer", "pedant", "auditor"]
        for agent in required:
            if agent not in registry.profiles:
                fail(f"Mandatory agent '{agent}' is missing from registry")
    except FileNotFoundError:
        fail(".agents/agent_registry.json is missing")
    except ValidationError as e:
        fail(f"Registry validation failed:\n{e}")
    except Exception as e:
        fail(f"Registry error: {e}")


# ==========================================
# 4. STRUCTURE VALIDATION (Model 5.3)
# ==========================================
def validate_structure() -> None:
    """Verify that all Model 5.3 directories and files exist."""
    print("\n📁 Checking Model 5.3 directory structure...")

    required_dirs = [
        ".agents",
        "agent_core",
        "agent_core/router_core",
        "agent_context",
        "agent_tests",
        "src",
        "tests",
    ]

    required_files = [
        "CLAUDE.md",
        "pyproject.toml",
        "agent_orchestrator.json",  # NEW NAME
        ".python-version",
        "agent_context/TASKS.md",
        "agent_context/SESSION.md",
        "agent_context/MEMORY.md",
        "agent_core/router.py",
        "agent_core/indexer.py",
        "agent_core/validator.py",
    ]

    for d in required_dirs:
        if not (ROOT / d).exists():
            fail(f"Mandatory directory '{d}' is missing")
        else:
            ok(f"Directory '{d}'")

    for f in required_files:
        if not (ROOT / f).exists():
            fail(f"Mandatory file '{f}' is missing")
        else:
            ok(f"File '{f}'")


# ==========================================
# 5. SESSION & HALT VALIDATION
# ==========================================
def validate_session() -> None:
    """Ensure SESSION.md exists in agent_context and follows bimetric schema."""
    print("\n📋 Checking SESSION.md schema...")
    session_path = ROOT / "agent_context" / "SESSION.md"
    if not session_path.exists():
        fail("SESSION.md missing in agent_context")
        return

    content = session_path.read_text(encoding="utf-8")
    for section in ["## [USER_SECTION]", "## [AGENT_SECTION]"]:
        if section not in content:
            fail(f"SESSION.md is missing mandatory section '{section}'")
        else:
            ok(f"Section '{section}'")


def validate_halt() -> None:
    """Report if the system is currently blocked by a HALT flag."""
    print("\n🚦 Checking HALT status...")
    flag_path = ROOT / ".claude" / "cache" / "HALT.flag"
    if flag_path.exists():
        warn(f"System is currently HALTED: {flag_path.read_text()}")
    else:
        ok("No HALT flag detected")


# ==========================================
# MAIN
# ==========================================
def main() -> None:
    """Execute all validation suites for the orchestrator."""
    print("🛡️  Agent-CI-Lens Validator v8.0")
    print(f"   Root: {ROOT}")

    validate_env()
    validate_config()
    validate_agents()
    validate_structure()
    validate_session()
    validate_halt()

    print("\n" + "=" * 50)

    if ERRORS:
        print(f"\n❌ Validation FAILED ({len(ERRORS)} errors)")
        sys.exit(1)

    if WARNINGS:
        print(f"⚠️  Validation passed with {len(WARNINGS)} warnings.")
    else:
        print("✅ Validation successful.")
    sys.exit(0)


if __name__ == "__main__":
    main()
