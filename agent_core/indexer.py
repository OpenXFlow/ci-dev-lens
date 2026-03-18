#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/indexer.py - The Dual-Output Semantic Map Maker (v 2.1).
Parses codebase into AGENTS.md (Human Fallback) and SQLite Memory Engine (RAG).
"""

import ast
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Dynamic detection of project root to allow standalone execution
ROOT = Path(__file__).parent.parent.resolve()

try:
    from agent_core.memory_engine import MemoryEngine
    from agent_core.router_core.utils import load_orchestrator_config
except ImportError:
    sys.path.insert(0, str(ROOT))
    from agent_core.memory_engine import MemoryEngine
    from agent_core.router_core.utils import load_orchestrator_config

CACHE_DIR = ROOT / ".claude" / "cache"
SRC_DIR = ROOT / "src"
OUTPUT_JSON = CACHE_DIR / "agents-index.json"
OUTPUT_MD = CACHE_DIR / "AGENTS.md"


# ==========================================
# 1. AST PARSER (Token-Protected Extraction)
# ==========================================
def _get_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Extracts function signature cleanly."""
    try:
        args = ast.unparse(node.args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    except Exception:
        return "(...)"
    else:
        return f"({args}){returns}"


def _get_calls(node: ast.AST) -> list[str]:
    """Extracts external function calls made inside the given AST node."""
    calls = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            with contextlib.suppress(Exception):
                calls.add(ast.unparse(child.func))
    return list(calls)


def _get_first_docstring_line(node: ast.AST) -> str:
    """Extracts only the first line of a docstring to save context tokens."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module):
        doc = ast.get_docstring(node)
        if doc:
            return doc.strip().split("\n")[0]
    return ""


def parse_python_file(path: Path, root_override: Path | None = None) -> dict[str, Any]:
    """Parses a single Python file and extracts semantic RAG nodes."""
    effective_root = root_override if root_override else ROOT

    try:
        relative_path = str(path.resolve().relative_to(effective_root.resolve()))
    except ValueError:
        relative_path = path.name

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        return {
            "path": relative_path,
            "error": str(e),
            "imports": [],
            "nodes": [],
            "lines": 0,
            "size_bytes": 0,
        }

    local_imports = []
    nodes: list[dict[str, Any]] = []

    # 1. Extract Local Imports (Ignore standard libraries to reduce noise)
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.ImportFrom)
            and stmt.module
            and ((stmt.level is not None and stmt.level > 0) or stmt.module.startswith(("src", "agent_core")))
        ):
            local_imports.append(stmt.module)

    # 2. Extract Structural Nodes (Functions, Classes, Methods)
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            nodes.append(
                {
                    "type": "function",
                    "name": stmt.name,
                    "line": stmt.lineno,
                    "signature": _get_signature(stmt),
                    "docstring": _get_first_docstring_line(stmt),
                    "calls": _get_calls(stmt),
                }
            )
        elif isinstance(stmt, ast.ClassDef):
            nodes.append(
                {
                    "type": "class",
                    "name": stmt.name,
                    "line": stmt.lineno,
                    "signature": "",
                    "docstring": _get_first_docstring_line(stmt),
                    "calls": [],
                }
            )
            # Parse Class Methods
            for child in stmt.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    nodes.append(
                        {
                            "type": "method",
                            "name": f"{stmt.name}.{child.name}",
                            "line": child.lineno,
                            "signature": _get_signature(child),
                            "docstring": _get_first_docstring_line(child),
                            "calls": _get_calls(child),
                        }
                    )

    return {
        "path": relative_path,
        "lines": len(source.splitlines()),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "imports": list(set(local_imports)),
        "nodes": nodes,
    }


def scan_project() -> list[dict[str, Any]]:
    """Scans all .py files in src/."""
    if not SRC_DIR.exists():
        print(f"  ⚠️  Directory src/ does not exist: {SRC_DIR}")
        return []

    py_files = sorted(SRC_DIR.rglob("*.py"))

    return [parse_python_file(path, root_override=ROOT) for path in py_files if "__pycache__" not in path.parts]


# ==========================================
# 2. DATABASE INDEXING (Dual Output)
# ==========================================
def generate_db_index(index: list[dict[str, Any]]) -> None:
    """Writes the parsed AST map securely into the SQLite Memory Engine."""
    try:
        config = load_orchestrator_config()
        if not config.memory_engine.enabled.value:
            print("  ℹ️  Memory Engine disabled in config. Skipping DB index.")  # noqa: RUF001
            return
    except Exception as e:
        print(f"  ⚠️  Failed to read config for DB indexing: {e}")
        return

    print("  🧠 Synchronizing Memory Engine (codebase_nodes)...")

    with MemoryEngine() as engine:
        conn = engine.get_connection()
        for f in index:
            if f.get("error"):
                continue

            path = f["path"]
            imports_json = json.dumps(f.get("imports", []))

            try:
                # The 'with conn:' context manager handles BEGIN/COMMIT automatically.
                # If an exception occurs, it triggers an atomic ROLLBACK for this file.
                with conn:
                    conn.execute("DELETE FROM codebase_nodes WHERE file_path = ?", (path,))
                    for node in f.get("nodes", []):
                        conn.execute(
                            """
                            INSERT INTO codebase_nodes
                            (file_path, node_type, name, signature, docstring, imports, calls)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                path,
                                node["type"],
                                node["name"],
                                node["signature"],
                                node["docstring"],
                                imports_json,
                                json.dumps(node.get("calls", [])),
                            ),
                        )
            except Exception as e:
                print(f"  ⚠️  Database transaction failed for {path}: {e}")


# ==========================================
# 3. JSON & MARKDOWN MAPS (Legacy Fallback)
# ==========================================
def generate_json(index: list[dict[str, Any]]) -> None:
    """Writes full machine index to agents-index.json."""
    total_lines = sum(f.get("lines", 0) for f in index)
    total_functions = sum(1 for f in index for n in f.get("nodes", []) if n["type"] in ("function", "method"))
    total_classes = sum(1 for f in index for n in f.get("nodes", []) if n["type"] == "class")

    output = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_files": len(index),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
        },
        "files": index,
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ JSON index: {OUTPUT_JSON.relative_to(ROOT)}")


def generate_markdown(index: list[dict[str, Any]]) -> None:
    """Writes human-readable map to AGENTS.md."""
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    total_lines = sum(f.get("lines", 0) for f in index)
    total_functions = sum(1 for f in index for n in f.get("nodes", []) if n["type"] in ("function", "method"))
    total_classes = sum(1 for f in index for n in f.get("nodes", []) if n["type"] == "class")

    lines.append("# Agent-CI-Lens — Codebase Map")
    lines.append(f"*Generated: {now}*")
    lines.append("\n## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Files | {len(index)} |")
    lines.append(f"| Functions | {total_functions} |")
    lines.append(f"| Classes | {total_classes} |")
    lines.append(f"| Lines | {total_lines} |\n")

    # Developer short map
    lines.append("## File Tree (Developer View)")
    lines.append("```")
    for f in index:
        path = f["path"]
        error = f.get("error", "")
        if error:
            lines.append(f"{path}  ⚠️ PARSE ERROR: {error}")
        else:
            n_funcs = sum(1 for n in f.get("nodes", []) if n["type"] in ("function", "method"))
            n_classes = sum(1 for n in f.get("nodes", []) if n["type"] == "class")
            lines.append(f"{path}  ({n_funcs}f, {n_classes}c, {f.get('lines', 0)}L)")
    lines.append("```\n")

    # Queen detailed map
    lines.append("## Detailed Map (Queen View)")
    for f in index:
        if f.get("error"):
            continue

        lines.append(f"### `{f['path']}`")
        lines.append(f"*{f.get('lines', 0)} lines, {f.get('size_bytes', 0)} bytes*\n")

        classes = [n for n in f.get("nodes", []) if n["type"] == "class"]
        functions = [n for n in f.get("nodes", []) if n["type"] == "function"]
        methods = [n for n in f.get("nodes", []) if n["type"] == "method"]

        if classes:
            lines.append("**Classes:**")
            for cls in classes:
                doc = f" — {cls['docstring']}" if cls.get("docstring") else ""
                lines.append(f"- `{cls['name']}` (L{cls['line']}){doc}")
                cls_methods = [m["name"].split(".")[1] for m in methods if m["name"].startswith(f"{cls['name']}.")]
                if cls_methods:
                    methods_str = ", ".join(f"`{m}`" for m in cls_methods[:5])
                    if len(cls_methods) > 5:
                        methods_str += f" +{len(cls_methods) - 5} others"
                    lines.append(f"  - Methods: {methods_str}")
            lines.append("")

        if functions:
            lines.append("**Functions:**")
            for func in functions:
                doc = f" — {func['docstring']}" if func.get("docstring") else ""
                lines.append(f"- `{func['name']}` (L{func['line']}){doc}")
            lines.append("")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ Markdown map: {OUTPUT_MD.relative_to(ROOT)}")


# ==========================================
# MAIN
# ==========================================
def main() -> None:
    print("🗺️  Agent-CI-Lens Indexer (ACMI Enabled)")
    index = scan_project()

    if not index:
        print("  ⚠️  No Python files found in src/")
        sys.exit(0)

    generate_json(index)
    generate_markdown(index)
    generate_db_index(index)

    print("\n✅ Indexing complete")


if __name__ == "__main__":
    main()
