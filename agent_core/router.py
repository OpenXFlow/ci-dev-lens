#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router.py - Agent-CI-Lens CLI Entrypoint (v 8.0)
"""

import argparse

# Safely import the engine from our new core module
from router_core.engine import Router

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent-CI-Lens Orchestrator")
    parser.add_argument("--pipeline", action="store_true", help="Start the execution pipeline")
    parser.add_argument("--mock", action="store_true", help="Run with API mocking enabled")
    args = parser.parse_args()

    if args.pipeline:
        Router(mock=args.mock).run_pipeline()
