#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida  (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/indexer.py - The Map Maker (v 1.2)
Scans src/ and generates:
  - .claude/cache/agents-index.json  (machine index for router.py)
  - .claude/cache/AGENTS.md          (human-readable map for Queen)
"""

import ast
import json
import sys
from datetime import datetime
from pathlib import Path

# Dynamic detection of project root
ROOT = Path(__file__).parent.parent.resolve()
CACHE_DIR = ROOT / ".claude" / "cache"
SRC_DIR = ROOT / "src"
OUTPUT_JSON = CACHE_DIR / "agents-index.json"
OUTPUT_MD = CACHE_DIR / "AGENTS.md"


# ==========================================
# 1. AST PARSER
# ==========================================
def parse_python_file(path: Path, root_override: Path | None = None) -> dict:
    """Parses a single Python file and extracts its structure."""
    effective_root = root_override if root_override else ROOT

    relative_path: str
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
            "functions": [],
            "classes": [],
            "lines": 0,
        }

    functions = []
    classes = []

    for node in ast.walk(tree):
        # Extract functions (top-level and methods)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            docstring = ast.get_docstring(node) or ""
            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": docstring[:100] if docstring else "",  # Max 100 chars
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
            )

        # Extract classes
        elif isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node) or ""
            methods = [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
            classes.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": docstring[:100] if docstring else "",
                    "methods": methods,
                }
            )

    lines = len(source.splitlines())

    return {
        "path": relative_path,
        "lines": lines,
        "functions": functions,
        "classes": classes,
        "size_bytes": path.stat().st_size,
    }


# ==========================================
# 2. SCANNING src/
# ==========================================
def scan_project() -> list[dict]:
    """Scans all .py files in src/."""
    if not SRC_DIR.exists():
        print(f"  ⚠️  Directory src/ does not exist: {SRC_DIR}")
        return []

    py_files = sorted(SRC_DIR.rglob("*.py"))
    results = []

    for path in py_files:
        # Skip __pycache__
        if "__pycache__" in path.parts:
            continue
        parsed = parse_python_file(path, root_override=ROOT)
        results.append(parsed)

    return results


# ==========================================
# 3. GENERATING JSON INDEX
# ==========================================
def generate_json(index: list[dict]) -> None:
    """Writes full machine index to agents-index.json."""
    total_lines = sum(f.get("lines", 0) for f in index)
    total_functions = sum(len(f.get("functions", [])) for f in index)
    total_classes = sum(len(f.get("classes", [])) for f in index)

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
    OUTPUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"  ✅ JSON index: {OUTPUT_JSON.relative_to(ROOT)}")


# ==========================================
# 4. GENERATING MARKDOWN MAP
# ==========================================
def generate_markdown(index: list[dict]) -> None:
    """Writes human-readable map to AGENTS.md."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_lines = sum(f.get("lines", 0) for f in index)
    total_functions = sum(len(f.get("functions", [])) for f in index)
    total_classes = sum(len(f.get("classes", [])) for f in index)

    lines.append("# Agent-CI-Lens — Codebase Map")
    lines.append(f"*Generated: {now}*")
    lines.append("")
    lines.append("## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Files | {len(index)} |")
    lines.append(f"| Functions | {total_functions} |")
    lines.append(f"| Classes | {total_classes} |")
    lines.append(f"| Lines | {total_lines} |")
    lines.append("")

    # File tree (short map for Developer)
    lines.append("## File Tree (Developer View)")
    lines.append("```")
    for f in index:
        path = f["path"]
        n_funcs = len(f.get("functions", []))
        n_classes = len(f.get("classes", []))
        error = f.get("error", "")
        if error:
            lines.append(f"{path}  ⚠️ PARSE ERROR: {error}")
        else:
            lines.append(f"{path}  ({n_funcs}f, {n_classes}c, {f['lines']}L)")
    lines.append("```")
    lines.append("")

    # Detailed map (for Queen)
    lines.append("## Detailed Map (Queen View)")
    for f in index:
        if f.get("error"):
            continue
        lines.append(f"### `{f['path']}`")
        lines.append(f"*{f['lines']} lines, {f['size_bytes']} bytes*")

        if f.get("classes"):
            lines.append("")
            lines.append("**Classes:**")
            for cls in f["classes"]:
                doc = f" — {cls['docstring']}" if cls["docstring"] else ""
                lines.append(f"- `{cls['name']}` (L{cls['line']}){doc}")
                if cls["methods"]:
                    methods_str = ", ".join(f"`{m}`" for m in cls["methods"][:5])
                    if len(cls["methods"]) > 5:
                        methods_str += f" +{len(cls['methods']) - 5} others"
                    lines.append(f"  - Methods: {methods_str}")

        if f.get("functions"):
            lines.append("")
            lines.append("**Functions:**")
            for func in f["functions"]:
                prefix = "async " if func["is_async"] else ""
                doc = f" — {func['docstring']}" if func["docstring"] else ""
                lines.append(f"- `{prefix}{func['name']}` (L{func['line']}){doc}")

        lines.append("")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ Markdown map: {OUTPUT_MD.relative_to(ROOT)}")


# ==========================================
# MAIN
# ==========================================
def main() -> None:
    print("🗺️  Agent-CI-Lens Indexer")
    index = scan_project()

    if not index:
        print("  ⚠️  No Python files found in src/")
        sys.exit(0)

    generate_json(index)
    generate_markdown(index)

    print("\n✅ Indexing complete")


if __name__ == "__main__":
    main()
