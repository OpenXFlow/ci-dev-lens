#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/spec_gen.py - The Specification Generator (v 1.1.1).
Now handles tuple returns from APIClient (v3.9.1 compatibility).
"""

import argparse
import sys
from pathlib import Path

# Fix path to allow importing from router_core
ROOT = Path(__file__).parent.parent.resolve()
sys.path.append(str(ROOT))

try:
    from agent_core.router_core.llm import APIClient
    from agent_core.router_core.models import AgentProfile
    from agent_core.router_core.utils import load_env, load_orchestrator_config
except ImportError as e:
    print(f"Error: Could not load core components. {e}")
    sys.exit(1)


def generate_specification(raw_task: str) -> str:
    """Reads Architect persona and calls LLM to format the goal."""
    env = load_env()
    config = load_orchestrator_config()
    client = APIClient(env, env.MOCK, config)

    # 1. Load the prompt from our new standard location
    persona_path = ROOT / ".agents" / "architect.md"
    if not persona_path.exists():
        return f"Error: Architect persona missing at {persona_path}"

    architect_instruction = persona_path.read_text(encoding="utf-8")

    # 2. Use high-quality model for architecture
    profile = AgentProfile(
        role="Architect",
        model="mistral-large-latest",
        provider="mistral",
        thinking="required",
        temperature=0.1,  # Lower temperature for strict formatting
        max_tokens=2000,
    )

    final_prompt = f"{architect_instruction}\n\nUSER INPUT IDEA:\n'{raw_task}'"

    try:
        # SURGICAL PATCH: Unpack response and ignore usage metadata for spec generation
        response, _usage = client.call(agent="architect", profile=profile, prompt=final_prompt, tid="SPEC-GEN")
        return str(response).strip()
    except Exception as e:
        return f"Error generating specification: {e}"


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent-CI-Lens Goal Specification Generator")
    parser.add_argument("--task", required=True, help="Your informal task description")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("🧠 ARCHITECT is refining your goal...")
    print("=" * 50 + "\n")

    spec = generate_specification(args.task)
    print(spec)
    print("\n" + "=" * 50)
    print("👉 Paste this into agent_context/TASKS.md")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
