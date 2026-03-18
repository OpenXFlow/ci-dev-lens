#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/validator.py - Comprehensive System Integrity Shield (v 9.0 Pydantic).
Refactored to support ACMI (Memory Engine) validation and structure checks.
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

# Dynamic detection of project root
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
# 1. ENV VALIDATION
# ==========================================
def validate_env() -> None:
    """Check .env file using EnvConfig schema."""
    print("\n🔑 Checking .env keys (Pydantic)...")
    try:
        config = load_env()

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
# 2. CONFIG VALIDATION
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
# 3. ACMI ENGINE VALIDATION (Milestone 5 Integration)
# ==========================================
def validate_acmi() -> None:
    """Verifies the state and presence of the ACMI Memory Engine."""
    print("\n🧠 Checking ACMI Memory Engine...")
    try:
        config = load_orchestrator_config()
        engine_enabled = config.memory_engine.enabled.value
        db_rel_path = config.memory_engine.db_path.value
        db_path = ROOT / db_rel_path if db_rel_path != ":memory:" else None

        if engine_enabled:
            ok("Memory Engine is ENABLED in config")
            if db_path:
                if db_path.exists():
                    ok(f"Database file found: {db_rel_path}")
                    # Deep health check if file exists
                    try:
                        from agent_core.memory_engine import MemoryEngine

                        with MemoryEngine() as engine:
                            health = engine.health_check()
                            ok(f"Schema version: {health['schema_version']}")
                            if health["pending_migrations"] > 0:
                                warn(f"Database has {health['pending_migrations']} pending migrations.")
                    except Exception as e:
                        warn(f"Could not perform deep health check: {e}")
                else:
                    warn(f"Database file NOT FOUND at {db_rel_path}. System will create an empty one on start.")
            else:
                ok("Using in-memory database (:memory:)")
        else:
            warn("Memory Engine is DISABLED. Expert RAG features will be inactive.")

    except Exception as e:
        fail(f"ACMI validation failed: {e}")


# ==========================================
# 4. AGENTS VALIDATION
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
# 5. STRUCTURE VALIDATION
# ==========================================
def validate_structure() -> None:
    """Verify that all mandatory directories and files exist."""
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
        "agent_orchestrator.json",
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
# 6. SESSION & HALT VALIDATION
# ==========================================
def validate_session() -> None:
    """Ensure SESSION.md exists and follows bimetric schema."""
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
    flag_path = ROOT / ".claude/cache/HALT.flag"
    if flag_path.exists():
        warn(f"System is currently HALTED: {flag_path.read_text()}")
    else:
        ok("No HALT flag detected")


# ==========================================
# MAIN
# ==========================================
def main() -> None:
    """Execute all validation suites for the orchestrator."""
    print("🛡️  Agent-CI-Lens Validator v9.0")
    print(f"   Root: {ROOT}")

    validate_env()
    validate_config()
    validate_acmi()  # New ACMI check
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
