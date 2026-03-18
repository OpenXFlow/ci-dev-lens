#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.
"""
agent_tests/test_indexer.py - Full unit tests for the Semantic Dual-Output Indexer (v 2.4).
Fixed namespace monkeypatching for Milestone 4.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is in path before importing agent_core
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from agent_core.indexer import (  # noqa: E402
    generate_db_index,
    generate_json,
    generate_markdown,
    parse_python_file,
    scan_project,
)


# --- TESTS: parse_python_file ---
class TestParsePythonFile:
    def test_parse_functions(self, tmp_src: Path) -> None:
        """Verify that top-level functions are correctly extracted into nodes."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        func_names = [n["name"] for n in result.get("nodes", []) if n["type"] == "function"]
        assert "add" in func_names

    def test_parse_class(self, tmp_src: Path) -> None:
        """Verify that classes are correctly identified as structural nodes."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        class_names = [n["name"] for n in result.get("nodes", []) if n["type"] == "class"]
        assert "Calculator" in class_names

    def test_parse_docstring(self, tmp_src: Path) -> None:
        """Verify that the first line of the docstring is captured correctly."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        add_func = next(n for n in result.get("nodes", []) if n["name"] == "add")
        assert "Adds two numbers" in add_func["docstring"]

    def test_parse_line_count(self, tmp_src: Path) -> None:
        """Verify that the parser correctly counts lines of code."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        assert result["lines"] > 0

    def test_parse_syntax_error(self, tmp_src: Path) -> None:
        """Verify that files with syntax errors return an error message."""
        result = parse_python_file(tmp_src / "src" / "broken.py", root_override=tmp_src)
        assert "error" in result
        assert result.get("nodes") == []

    def test_parse_empty_file(self, tmp_src: Path) -> None:
        """Verify that empty files return zero counts."""
        result = parse_python_file(tmp_src / "src" / "empty.py", root_override=tmp_src)
        assert result.get("nodes") == []
        assert result["lines"] == 0

    def test_relative_path_in_result(self, tmp_src: Path) -> None:
        """Verify that the reported path is relative to the project root."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        assert "src/calculator.py" in result["path"]

    def test_class_methods_listed(self, tmp_src: Path) -> None:
        """Verify that class methods are correctly extracted with dot notation."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        method_names = [n["name"] for n in result.get("nodes", []) if n["type"] == "method"]
        assert "Calculator.multiply" in method_names

    def test_parse_imports_and_calls(self, tmp_src: Path) -> None:
        """Verify that local imports and function calls are captured for RAG mapping."""
        dep_file = tmp_src / "src" / "deps.py"
        dep_file.write_text(
            "from src.config import settings\n\ndef run():\n    print('hello')\n    settings.get()\n", encoding="utf-8"
        )
        result = parse_python_file(dep_file, root_override=tmp_src)

        assert "src.config" in result.get("imports", [])

        run_node = next(n for n in result.get("nodes", []) if n["name"] == "run")
        assert "print" in run_node["calls"]


# --- TESTS: scan_project ---
class TestScanProject:
    def test_scan_finds_files(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that indexer finds Python files in the source directory."""
        import agent_core.indexer as idx

        monkeypatch.setattr(idx, "SRC_DIR", tmp_src / "src")
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        results = scan_project()
        paths = [r["path"] for r in results]
        assert any("calculator.py" in p for p in paths)

    def test_scan_skips_pycache(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that __pycache__ directories are safely ignored."""
        import agent_core.indexer as idx

        pycache = tmp_src / "src" / "__pycache__"
        pycache.mkdir(parents=True, exist_ok=True)
        (pycache / "cached.py").write_text("x = 1", encoding="utf-8")

        monkeypatch.setattr(idx, "SRC_DIR", tmp_src / "src")
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        results = scan_project()
        paths = [r["path"] for r in results]
        assert not any("__pycache__" in p for p in paths)


# --- TESTS: generate_db_index ---
class TestGenerateDbIndex:
    def test_db_index_creation(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that AST nodes are written to the SQLite Memory Engine."""
        import agent_core.indexer as idx
        from agent_core.memory_engine import MemoryEngine
        from agent_core.router_core.utils import load_orchestrator_config

        # Force Memory Engine state
        config = load_orchestrator_config()
        config.memory_engine.enabled.value = True
        config.memory_engine.db_path.value = str(tmp_project / ".claude/cache/memory.db")

        # Patch BOTH the utility source and the indexer local import
        monkeypatch.setattr("agent_core.router_core.utils.load_orchestrator_config", lambda: config)
        monkeypatch.setattr("agent_core.indexer.load_orchestrator_config", lambda: config)
        monkeypatch.setattr("agent_core.memory_engine.load_orchestrator_config", lambda: config)

        # Inject isolated temp project root
        monkeypatch.setattr(idx, "ROOT", tmp_project)

        # Mock payload
        mock_index = [
            {
                "path": "src/module.py",
                "imports": ["src.auth"],
                "nodes": [
                    {
                        "type": "function",
                        "name": "login",
                        "signature": "(user)",
                        "docstring": "Authenticates user.",
                        "calls": ["hash_pwd"],
                    }
                ],
            }
        ]

        # Execute DB insertion
        generate_db_index(mock_index)

        # Validate insertion in the memory engine
        with MemoryEngine(db_path=config.memory_engine.db_path.value) as engine:
            conn = engine.get_connection()
            cursor = conn.execute(
                "SELECT name, imports, docstring FROM codebase_nodes WHERE file_path = 'src/module.py'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row["name"] == "login"
            assert "src.auth" in row["imports"]
            assert row["docstring"] == "Authenticates user."


# --- TESTS: generate_json ---
class TestGenerateJson:
    def _setup_cache(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Helper to redirect output paths for testing."""
        import agent_core.indexer as idx

        cache = tmp_src / ".claude" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(idx, "OUTPUT_JSON", cache / "agents-index.json")
        monkeypatch.setattr(idx, "CACHE_DIR", cache)
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        return cache

    def test_json_created(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that agents-index.json is physically created."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_json(index)
        assert (cache / "agents-index.json").exists()


# --- TESTS: generate_markdown ---
class TestGenerateMarkdown:
    def _setup_cache(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Helper to redirect output paths for testing."""
        import agent_core.indexer as idx

        cache = tmp_src / ".claude" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(idx, "OUTPUT_MD", cache / "AGENTS.md")
        monkeypatch.setattr(idx, "CACHE_DIR", cache)
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        return cache

    def test_markdown_created(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that AGENTS.md is physically created."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_markdown(index)
        assert (cache / "AGENTS.md").exists()

    def test_markdown_contains_functions(self, tmp_src: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that extracted functions are correctly listed in the markdown."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_markdown(index)
        content = (cache / "AGENTS.md").read_text(encoding="utf-8")
        assert "add" in content
