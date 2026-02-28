#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.
"""
agent_tests/test_indexer.py - Full unit tests for the Codebase Indexer (v 1.4)
Fixtures are defined in conftest.py
"""

import json
import sys
from pathlib import Path

# Ensure project root is in path before importing agent_core
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

# Fix E402: Module level import not at top of file
from agent_core.indexer import (  # noqa: E402
    generate_json,
    generate_markdown,
    parse_python_file,
    scan_project,
)


# ==========================================
# TESTS: parse_python_file
# ==========================================
class TestParsePythonFile:
    def test_parse_functions(self, tmp_src: Path) -> None:
        """Verify that top-level functions are correctly extracted."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        func_names = [f["name"] for f in result["functions"]]
        assert "add" in func_names

    def test_parse_class(self, tmp_src: Path) -> None:
        """Verify that classes are correctly identified."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        class_names = [c["name"] for c in result["classes"]]
        assert "Calculator" in class_names

    def test_parse_docstring(self, tmp_src: Path) -> None:
        """Verify that function docstrings are captured."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        add_func = next(f for f in result["functions"] if f["name"] == "add")
        assert "Adds" in add_func["docstring"]

    def test_parse_line_count(self, tmp_src: Path) -> None:
        """Verify that the parser correctly counts lines of code."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        assert result["lines"] > 0

    def test_parse_syntax_error(self, tmp_src: Path) -> None:
        """Verify that files with syntax errors return an error message."""
        result = parse_python_file(tmp_src / "src" / "broken.py", root_override=tmp_src)
        assert "error" in result
        assert result["functions"] == []

    def test_parse_empty_file(self, tmp_src: Path) -> None:
        """Verify that empty files return zero counts."""
        result = parse_python_file(tmp_src / "src" / "empty.py", root_override=tmp_src)
        assert result["functions"] == []
        assert result["classes"] == []
        assert result["lines"] == 0

    def test_relative_path_in_result(self, tmp_src: Path) -> None:
        """Verify that the reported path is relative to the project root."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        assert "src/calculator.py" in result["path"]

    def test_async_function_detected(self, tmp_src: Path) -> None:
        """Verify that async functions are correctly detected."""
        async_file = tmp_src / "src" / "async_mod.py"
        async_file.write_text("async def fetch() -> None:\n    pass\n", encoding="utf-8")
        result = parse_python_file(async_file, root_override=tmp_src)
        assert result["functions"][0]["is_async"] is True

    def test_class_methods_listed(self, tmp_src: Path) -> None:
        """Verify that class methods are correctly extracted."""
        result = parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)
        calc_class = next(c for c in result["classes"] if c["name"] == "Calculator")
        assert "multiply" in calc_class["methods"]


# ==========================================
# TESTS: scan_project
# ==========================================
class TestScanProject:
    def test_scan_finds_files(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that indexer finds Python files in the source directory."""
        import agent_core.indexer as idx
        monkeypatch.setattr(idx, "SRC_DIR", tmp_src / "src")
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        results = scan_project()
        paths = [r["path"] for r in results]
        assert any("calculator.py" in p for p in paths)

    def test_scan_skips_pycache(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that __pycache__ directories are ignored during scan."""
        import agent_core.indexer as idx
        pycache = tmp_src / "src" / "__pycache__"
        pycache.mkdir(parents=True, exist_ok=True)
        (pycache / "cached.py").write_text("x = 1", encoding="utf-8")
        
        monkeypatch.setattr(idx, "SRC_DIR", tmp_src / "src")
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        results = scan_project()
        paths = [r["path"] for r in results]
        assert not any("__pycache__" in p for p in paths)

    def test_scan_empty_src(self, tmp_path: Path, monkeypatch) -> None:
        """Verify that indexer handles empty source directories gracefully."""
        import agent_core.indexer as idx
        empty_src = tmp_path / "src"
        empty_src.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(idx, "SRC_DIR", empty_src)
        monkeypatch.setattr(idx, "ROOT", tmp_path)
        results = scan_project()
        assert results == []


# ==========================================
# TESTS: generate_json
# ==========================================
class TestGenerateJson:
    def _setup_cache(self, tmp_src: Path, monkeypatch) -> Path:
        """Helper to redirect output paths for testing."""
        import agent_core.indexer as idx
        cache = tmp_src / ".claude" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(idx, "OUTPUT_JSON", cache / "agents-index.json")
        monkeypatch.setattr(idx, "CACHE_DIR", cache)
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        return cache

    def test_json_created(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that agents-index.json is physically created."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_json(index)
        assert (cache / "agents-index.json").exists()

    def test_json_structure(self, tmp_src: Path, monkeypatch) -> None:
        """Verify the internal schema of the generated JSON index."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_json(index)
        data = json.loads((cache / "agents-index.json").read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert "summary" in data
        assert "files" in data
        assert data["summary"]["total_files"] == 1

    def test_json_summary_counts(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that summary counts in JSON are accurate."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_json(index)
        data = json.loads((cache / "agents-index.json").read_text(encoding="utf-8"))
        assert data["summary"]["total_functions"] >= 1
        assert data["summary"]["total_classes"] >= 1


# ==========================================
# TESTS: generate_markdown
# ==========================================
class TestGenerateMarkdown:
    def _setup_cache(self, tmp_src: Path, monkeypatch) -> Path:
        """Helper to redirect output paths for testing."""
        import agent_core.indexer as idx
        cache = tmp_src / ".claude" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(idx, "OUTPUT_MD", cache / "AGENTS.md")
        monkeypatch.setattr(idx, "CACHE_DIR", cache)
        monkeypatch.setattr(idx, "ROOT", tmp_src)
        return cache

    def test_markdown_created(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that AGENTS.md is physically created."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_markdown(index)
        assert (cache / "AGENTS.md").exists()

    def test_markdown_contains_file_tree(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that the markdown contains the file tree section."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_markdown(index)
        content = (cache / "AGENTS.md").read_text(encoding="utf-8")
        assert "File Tree" in content
        assert "calculator.py" in content

    def test_markdown_contains_functions(self, tmp_src: Path, monkeypatch) -> None:
        """Verify that extracted functions are listed in the markdown."""
        cache = self._setup_cache(tmp_src, monkeypatch)
        index = [parse_python_file(tmp_src / "src" / "calculator.py", root_override=tmp_src)]
        generate_markdown(index)
        content = (cache / "AGENTS.md").read_text(encoding="utf-8")
        assert "add" in content