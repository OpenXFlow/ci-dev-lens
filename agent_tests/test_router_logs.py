#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_router_logs.py (v 1.3)
Diagnostic test to verify and inspect the injected linter rules in AI prompts.
Fixed PromptBuilder.build signature call with state argument.
"""

from agent_core.router_core.llm import PromptBuilder
from agent_core.router_core.models import AgentProfile
from agent_core.router_core.utils import load_linter_rules


def test_prompt_contains_rules() -> None:
    """Verifies that linting rules are dynamically injected and prints them."""
    builder = PromptBuilder()
    profile = AgentProfile(
        role="developer",
        model="test-model",
        provider="test-provider",
        thinking="n",
        temperature=0.0,
        max_tokens=100,
    )

    # Trigger the rules extraction
    rules = load_linter_rules()

    # Generate prompt - Updated with current state argument
    prompt = builder.build("developer", profile, "task", {}, "EXECUTING")

    # Assertions
    assert "<linting_rules>" in prompt
    assert "RUFF_CONFIG" in prompt
    assert "MYPY_CONFIG" in prompt

    # Print the extracted rules to console (requires -s flag)
    # with capsys.disabled():
    #    print("\n--- EXTRACTED LINTER RULES (Injection Preview) ---")
    #    print(rules)
    #    print("--------------------------------------------------\n")
