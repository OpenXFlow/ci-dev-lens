#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/memory_engine.py - The ACMI Standalone Database Core (v 6.0.0).
Provides thread-safe, context-managed SQLite integration with idempotent migrations.
Milestone 6.0: Added Token Telemetry columns and provider tracking.
"""

import argparse
import csv
import json
import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Self, cast

try:
    from .router_core.utils import ROOT, load_orchestrator_config
except ImportError:
    # Fallback for strict standalone execution if module paths are mangled
    ROOT = Path(__file__).parent.parent.resolve()
    sys.path.insert(0, str(ROOT))
    from agent_core.router_core.utils import ROOT, load_orchestrator_config


class MemoryEngine:
    """
    Thread-safe, Context-Managed SQLite Engine for Agent-CI Memory Intelligence (ACMI).
    Handles standalone schema migrations, connection pooling, and FTS capabilities.
    """

    MIGRATIONS: ClassVar[dict[int, str]] = {
        1: """
            -- 1. Dynamic Reality: Codebase AST Map
            CREATE TABLE IF NOT EXISTS codebase_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                node_type TEXT NOT NULL,
                name TEXT NOT NULL,
                signature TEXT,
                docstring TEXT,
                imports TEXT,
                calls TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_codebase_name ON codebase_nodes(name);
            CREATE INDEX IF NOT EXISTS idx_codebase_path ON codebase_nodes(file_path);
            CREATE INDEX IF NOT EXISTS idx_codebase_type ON codebase_nodes(node_type);

            -- 2. Rotating Memory: High-Fidelity Execution Logs
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                tool TEXT NOT NULL,
                result TEXT NOT NULL,
                output TEXT NOT NULL,
                duration_ms INTEGER,
                attempt INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_execlog_task ON execution_logs(task_id, timestamp DESC);

            -- 3. Rotating Memory: System Reflections (Auto-pruned AI learnings)
            CREATE TABLE IF NOT EXISTS system_reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                error_pattern TEXT NOT NULL,
                solution TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 4. Permanent Intelligence: Knowledge Bank (Enterprise Expert Library)
            CREATE TABLE IF NOT EXISTS knowledge_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,       -- 'manual_entry' | 'external_lib'
                category TEXT NOT NULL,     -- 'performance' | 'security' | 'typing' | 'testing'
                content TEXT NOT NULL,
                confidence_score REAL DEFAULT 1.0,
                verified_by TEXT,           -- 'human' | 'ci_pass'
                project_scope TEXT,         -- NULL for global, else project name
                vector BLOB,                -- NULL placeholder for Phase 6 (sqlite-vec)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            );
        """,
        2: """
            -- 1. Extend knowledge_bank table with semantic metadata (Milestone 4)
            ALTER TABLE knowledge_bank ADD COLUMN subcategory TEXT;
            ALTER TABLE knowledge_bank ADD COLUMN type TEXT;
            ALTER TABLE knowledge_bank ADD COLUMN tags TEXT;

            -- 2. Create FTS5 Virtual Table for System Reflections
            CREATE VIRTUAL TABLE IF NOT EXISTS system_reflections_fts USING fts5(
                error_pattern, solution, tags,
                content=system_reflections, content_rowid=id
            );

            -- 3. Triggers to keep system_reflections_fts synced
            CREATE TRIGGER IF NOT EXISTS system_reflections_ai AFTER INSERT ON system_reflections BEGIN
                INSERT INTO system_reflections_fts(rowid, error_pattern, solution, tags)
                VALUES (new.id, new.error_pattern, new.solution, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS system_reflections_ad AFTER DELETE ON system_reflections BEGIN
                INSERT INTO system_reflections_fts(system_reflections_fts, rowid, error_pattern, solution, tags)
                VALUES ('delete', old.id, old.error_pattern, old.solution, old.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS system_reflections_au AFTER UPDATE ON system_reflections BEGIN
                INSERT INTO system_reflections_fts(system_reflections_fts, rowid, error_pattern, solution, tags)
                VALUES ('delete', old.id, old.error_pattern, old.solution, old.tags);
                INSERT INTO system_reflections_fts(rowid, error_pattern, solution, tags)
                VALUES (new.id, new.error_pattern, new.solution, new.tags);
            END;

            -- 4. Create FTS5 Virtual Table for Knowledge Bank
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_bank_fts USING fts5(
                category, subcategory, type, tags, content,
                content=knowledge_bank, content_rowid=id
            );

            -- 5. Triggers to keep knowledge_bank_fts synced
            CREATE TRIGGER IF NOT EXISTS knowledge_bank_ai AFTER INSERT ON knowledge_bank BEGIN
                INSERT INTO knowledge_bank_fts(rowid, category, subcategory, type, tags, content)
                VALUES (new.id, new.category, new.subcategory, new.type, new.tags, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS knowledge_bank_ad AFTER DELETE ON knowledge_bank BEGIN
                INSERT INTO knowledge_bank_fts(knowledge_bank_fts, rowid, category, subcategory, type, tags, content)
                VALUES ('delete', old.id, old.category, old.subcategory, old.type, old.tags, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS knowledge_bank_au AFTER UPDATE ON knowledge_bank BEGIN
                INSERT INTO knowledge_bank_fts(knowledge_bank_fts, rowid, category, subcategory, type, tags, content)
                VALUES ('delete', old.id, old.category, old.subcategory, old.type, old.tags, old.content);
                INSERT INTO knowledge_bank_fts(rowid, category, subcategory, type, tags, content)
                VALUES (new.id, new.category, new.subcategory, new.type, new.tags, new.content);
            END;
        """,
        3: """
            -- Milestone 4.5: Parent-Child Retrieval & JSON Tags Support
            CREATE TABLE knowledge_bank_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                type TEXT,
                tags TEXT DEFAULT '[]',
                content TEXT NOT NULL,
                confidence_score REAL DEFAULT 1.0,
                verified_by TEXT,
                project_scope TEXT,
                vector BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                parent_id INTEGER REFERENCES knowledge_bank_new(id),
                chunk_index INTEGER DEFAULT 0,
                content_length INTEGER GENERATED ALWAYS AS (length(content)) VIRTUAL
            );

            INSERT INTO knowledge_bank_new (
                id, source, category, subcategory, type, tags, content,
                confidence_score, verified_by, project_scope, vector, created_at, updated_at
            )
            SELECT
                id, source, category, subcategory, type,
                CASE WHEN tags IS NULL OR tags = '' THEN '[]' ELSE '["' || replace(tags, ';', '","') || '"]' END,
                content, confidence_score, verified_by, project_scope, vector, created_at, updated_at
            FROM knowledge_bank;

            DROP TABLE knowledge_bank;
            ALTER TABLE knowledge_bank_new RENAME TO knowledge_bank;

            -- Recreate FTS5 Triggers to flatten JSON arrays into space-separated strings for indexing
            DROP TRIGGER IF EXISTS knowledge_bank_ai;
            DROP TRIGGER IF EXISTS knowledge_bank_ad;
            DROP TRIGGER IF EXISTS knowledge_bank_au;

            CREATE TRIGGER knowledge_bank_ai AFTER INSERT ON knowledge_bank BEGIN
                INSERT INTO knowledge_bank_fts(rowid, category, subcategory, type, tags, content)
                VALUES (new.id, new.category, new.subcategory, new.type, replace(replace(replace(new.tags, '[', ''), ']', ''), '"', ''), new.content);
            END;
            CREATE TRIGGER knowledge_bank_ad AFTER DELETE ON knowledge_bank BEGIN
                INSERT INTO knowledge_bank_fts(knowledge_bank_fts, rowid, category, subcategory, type, tags, content)
                VALUES ('delete', old.id, old.category, old.subcategory, old.type, replace(replace(replace(old.tags, '[', ''), ']', ''), '"', ''), old.content);
            END;
            CREATE TRIGGER knowledge_bank_au AFTER UPDATE ON knowledge_bank BEGIN
                INSERT INTO knowledge_bank_fts(knowledge_bank_fts, rowid, category, subcategory, type, tags, content)
                VALUES ('delete', old.id, old.category, old.subcategory, old.type, replace(replace(replace(old.tags, '[', ''), ']', ''), '"', ''), old.content);
                INSERT INTO knowledge_bank_fts(rowid, category, subcategory, type, tags, content)
                VALUES (new.id, new.category, new.subcategory, new.type, replace(replace(replace(new.tags, '[', ''), ']', ''), '"', ''), new.content);
            END;
        """,
        4: """
            -- Systematic Data Correction: Robust metadata-based re-categorization
            -- Targets Rule 2 (Verification Contract)
            UPDATE knowledge_bank
            SET category = 'quality', subcategory = 'verification'
            WHERE category = 'orchestration'
              AND (content LIKE 'VERIFICATION CONTRACT%' OR content LIKE '%success criterion%');

            -- Targets Rule 8 (Silent Success Trap)
            UPDATE knowledge_bank
            SET category = 'quality', subcategory = 'verification'
            WHERE category = 'orchestration'
              AND type = 'anti-pattern'
              AND (content LIKE '%Silent Success%' OR content LIKE '%RESULT:PASS%');
        """,
        5: """
            -- Milestone 5.0: Deterministic Mandatory Rules
            ALTER TABLE knowledge_bank ADD COLUMN is_mandatory INTEGER DEFAULT 0;
        """,
        6: """
            -- Milestone 6.0: Token Telemetry
            ALTER TABLE execution_logs ADD COLUMN provider TEXT DEFAULT '';
            ALTER TABLE execution_logs ADD COLUMN tokens_used INTEGER DEFAULT 0;
            ALTER TABLE execution_logs ADD COLUMN tokens_prompt INTEGER DEFAULT 0;
            ALTER TABLE execution_logs ADD COLUMN tokens_completion INTEGER DEFAULT 0;
        """,
    }

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initializes the thread-safe connection manager and configures the DB path."""
        self._local = threading.local()

        if db_path is None:
            try:
                config = load_orchestrator_config()
                raw_path = config.memory_engine.db_path.value
                self.db_path = raw_path if raw_path == ":memory:" else str(ROOT / raw_path)
            except Exception as e:
                print(f"⚠️  MemoryEngine Config Warning: {e}. Falling back to :memory:.")
                self.db_path = ":memory:"
        else:
            self.db_path = str(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection with optimal PRAGMAs."""
        if getattr(self._local, "connection", None) is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row

            # Performance and Integrity PRAGMAs
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA cache_size=-64000")

            self._local.connection = conn

        return cast(sqlite3.Connection, self._local.connection)

    def close(self) -> None:
        """Safely closes the connection for the current thread."""
        if getattr(self._local, "connection", None) is not None:
            cast(sqlite3.Connection, self._local.connection).close()
            self._local.connection = None

    def __enter__(self) -> Self:
        """Context manager entry - guarantees active connection."""
        self.get_connection()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit - safely cleans up resources."""
        self.close()

    def init_db(self) -> None:
        """Applies idempotent migrations to ensure the schema is up to date."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Bootstrap migration tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row and row[0] is not None else 0

        # Apply missing migrations
        for version, sql in sorted(self.MIGRATIONS.items()):
            if version > current_version:
                # Disable FK checks temporarily for safe table recreation
                conn.execute("PRAGMA foreign_keys=OFF")
                cursor.executescript(sql)
                cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
                conn.execute("PRAGMA foreign_keys=ON")

        conn.commit()

    def health_check(self) -> dict[str, Any]:
        """Provides diagnostic information about the database state."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        version = row[0] if row and row[0] is not None else 0

        db_size_mb = 0.0
        if self.db_path != ":memory:" and Path(self.db_path).exists():
            db_size_mb = Path(self.db_path).stat().st_size / (1024 * 1024)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cursor.fetchall()}
        expected_tables = {"schema_version", "codebase_nodes", "execution_logs", "system_reflections", "knowledge_bank"}

        latest_migration = max(self.MIGRATIONS.keys()) if self.MIGRATIONS else 0

        return {
            "wal_mode": journal_mode.upper() == "WAL" or self.db_path == ":memory:",
            "schema_version": version,
            "db_size_mb": round(db_size_mb, 2),
            "tables_ok": expected_tables.issubset(tables),
            "pending_migrations": latest_migration - version,
        }

    def maintenance(self, wipe_ast: bool = False) -> None:
        """Executes physical database maintenance and trims old execution logs."""
        if self.db_path == ":memory:":
            return

        conn = self.get_connection()
        try:
            if wipe_ast:
                conn.execute("DELETE FROM codebase_nodes")
                print("🧠 ACMI AST Cache wiped internally.")

            # Load rotation logic
            try:
                config = load_orchestrator_config()
                max_logs = config.memory_engine.max_execution_logs.value
            except Exception as cfg_err:
                print(f"⚠️  Could not read config for log rotation: {cfg_err}. Falling back to 2000.")
                max_logs = 2000

            # Safely prune execution logs, keeping only the most recent N records
            conn.execute(
                "DELETE FROM execution_logs WHERE id NOT IN (SELECT id FROM execution_logs ORDER BY timestamp DESC LIMIT ?)",
                (max_logs,),
            )

            # STAFF ENGINEER FIX: Commit before VACUUM to release internal locks
            conn.commit()

            # HACK: Brief sleep to allow Docker/Windows filesystem sync
            time.sleep(0.2)

            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.commit()
        except sqlite3.Error as e:
            if "locked" in str(e).lower():
                print(
                    f"⚠️  Database maintenance failed: {e}. HINT: Close any external SQLite viewers (like VS Code SQLiteViewer) and try again."
                )
            else:
                print(f"⚠️  Database maintenance failed: {e}")

    # ==========================================
    # KNOWLEDGE BANK EXPERT METHODS
    # ==========================================
    def add_knowledge(
        self,
        category: str,
        content: str,
        subcategory: str | None = None,
        type_: str | None = None,
        tags: str | list[str] | None = None,
        source: str = "manual_entry",
        confidence: float = 1.0,
        verified_by: str = "human",
        project_scope: str | None = None,
        parent_id: int | None = None,
        chunk_index: int = 0,
        is_mandatory: bool = False,
    ) -> int | None:
        """Inserts structured knowledge, supports JSON tags, Parent-Child logic and Mandatory flag."""
        conn = self.get_connection()

        # Deduplication check
        cursor = conn.execute("SELECT id FROM knowledge_bank WHERE content = ?", (content,))
        if cursor.fetchone():
            return None

        # Smart JSON tags conversion
        if isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split(";") if t.strip()]
        elif isinstance(tags, list):
            tags_list = [str(t).strip() for t in tags]
        else:
            tags_list = []
        tags_json = json.dumps(tags_list)

        cursor = conn.execute(
            """
            INSERT INTO knowledge_bank
            (source, category, subcategory, type, tags, content, confidence_score,
             verified_by, project_scope, parent_id, chunk_index, is_mandatory)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                category,
                subcategory,
                type_,
                tags_json,
                content,
                confidence,
                verified_by,
                project_scope,
                parent_id,
                chunk_index,
                1 if is_mandatory else 0,
            ),
        )
        conn.commit()
        return cast(int, cursor.lastrowid)

    def import_csv(self, file_path: str | Path) -> dict[str, int]:
        """Bulk ingest expert knowledge from a structured CSV file with Smart Delimiter detection."""
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        stats = {"imported": 0, "skipped": 0, "errors": 0}

        with csv_path.open(newline="", encoding="utf-8") as f:
            # Smart Delimiter Sniffing
            try:
                sample = f.read(2048)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=",;|")
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ","  # Default fallback

            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                raise ValueError("CSV is empty or missing headers.")

            headers = {name.strip().lower(): name for name in reader.fieldnames}

            for row in reader:
                try:
                    # Extract fields resiliently
                    content = row.get(headers.get("content", "CONTENT"), "").strip()
                    if not content:
                        stats["skipped"] += 1
                        continue

                    category = row.get(headers.get("category", "CATEGORY"), "general").strip()
                    subcategory = row.get(headers.get("subcategory", "SUBCATEGORY"), "").strip()
                    entry_type = row.get(headers.get("type", "TYPE"), "").strip()
                    tags = row.get(headers.get("tags", "TAGS"), "").strip()

                    added_id = self.add_knowledge(
                        category=category,
                        subcategory=subcategory if subcategory else None,
                        type_=entry_type if entry_type else None,
                        tags=tags if tags else None,
                        content=content,
                        source="external_lib",
                        confidence=1.0,
                        verified_by="human",
                    )

                    if added_id is not None:
                        stats["imported"] += 1
                    else:
                        stats["skipped"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    print(f"Error parsing row: {e}")

        return stats

    def search_knowledge(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Queries the FTS5 Knowledge Bank index using Parent-Child fallback."""
        conn = self.get_connection()
        # Escape quotes for safe FTS matching syntax ("phrase search")
        safe_query = query.replace('"', '""')

        try:
            # JOIN query that resolves children back to their parent content if exists
            cursor = conn.execute(
                """
                SELECT coalesce(p.category, c.category) as category,
                       coalesce(p.subcategory, c.subcategory) as subcategory,
                       coalesce(p.type, c.type) as type,
                       coalesce(p.tags, c.tags) as tags,
                       coalesce(p.content, c.content) as content
                FROM knowledge_bank_fts f
                JOIN knowledge_bank c ON f.rowid = c.id
                LEFT JOIN knowledge_bank p ON c.parent_id = p.id
                WHERE knowledge_bank_fts MATCH '(' || ? || ')'
                ORDER BY f.rank LIMIT ?
                """,
                (safe_query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # FTS syntax error fallback (e.g., invalid query tokens)
            return []

    def export_knowledge(self, output_path: Path) -> None:
        """Exports the knowledge_bank table to a portable JSON file."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT source, category, subcategory, type, tags, content,
                   confidence_score, verified_by, project_scope, parent_id, chunk_index, is_mandatory
            FROM knowledge_bank
            """
        )
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Successfully exported {len(data)} knowledge records to {output_path}")

    def export_knowledge_debug(self, output_path: Path) -> None:
        """Exports the entire knowledge_bank table with all columns for debugging."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_bank")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Successfully exported {len(data)} full debug records to {output_path}")

    def import_knowledge(self, input_path: Path) -> None:
        """Imports knowledge bank entries from a JSON file, ignoring duplicates."""
        if not input_path.exists():
            print(f"❌ Import failed: File not found at {input_path}")
            sys.exit(1)

        try:
            data = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"❌ Import failed: Invalid JSON format - {e}")
            sys.exit(1)

        imported = 0
        for entry in data:
            added_id = self.add_knowledge(
                category=entry.get("category", "general"),
                content=entry.get("content", ""),
                subcategory=entry.get("subcategory"),
                type_=entry.get("type"),
                tags=entry.get("tags"),
                source=entry.get("source", "imported_json"),
                confidence=entry.get("confidence_score", 1.0),
                verified_by=entry.get("verified_by", "system"),
                project_scope=entry.get("project_scope"),
                parent_id=entry.get("parent_id"),
                chunk_index=entry.get("chunk_index", 0),
                is_mandatory=bool(entry.get("is_mandatory", False)),
            )
            if added_id is not None:
                imported += 1

        print(f"✅ Successfully imported {imported} new knowledge records.")


def main() -> None:
    """CLI interface for MemoryEngine maintenance and portable knowledge operations."""
    parser = argparse.ArgumentParser(description="ACMI Standalone Database Core")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Health & Maintenance
    subparsers.add_parser("health", help="Run database diagnostic check")

    p_maint = subparsers.add_parser("maintenance", help="Run VACUUM, Checkpoint and Log rotation")
    p_maint.add_argument("--wipe-ast", action="store_true", help="Wipe codebase AST cache before optimization")

    # JSON Export / Import
    parser_export = subparsers.add_parser("knowledge-export", help="Export Knowledge Bank to JSON")
    parser_export.add_argument("--output", required=True, help="Path to output JSON file")

    parser_import = subparsers.add_parser("knowledge-import", help="Import Knowledge Bank from JSON")
    parser_import.add_argument("--input", required=True, help="Path to input JSON file")

    parser_export_debug = subparsers.add_parser(
        "knowledge-export-debug", help="Export full Knowledge Bank for debugging"
    )
    parser_export_debug.add_argument("--output", required=True, help="Path to output JSON file")

    # CSV Bulk Ingest & Manual Entry
    p_add = subparsers.add_parser("knowledge-add", help="Add single knowledge entry")
    p_add.add_argument("--category", required=True)
    p_add.add_argument("--content", required=True)
    p_add.add_argument("--subcategory", default=None)
    p_add.add_argument("--type", default=None)
    p_add.add_argument("--tags", default=None)
    p_add.add_argument("--mandatory", action="store_true", help="Flag as mandatory rule for RAG")

    p_import_csv = subparsers.add_parser("knowledge-import-csv", help="Bulk ingest from CSV")
    p_import_csv.add_argument("--file", required=True, help="Path to the CSV file")

    args = parser.parse_args()

    # Context-managed execution to guarantee DB cleanup
    with MemoryEngine() as engine:
        if args.command == "health":
            status = engine.health_check()
            print("\n🧠 Memory Engine Health Check:")
            for k, v in status.items():
                print(f"   {k}: {v}")
            if not status["tables_ok"] or status["pending_migrations"] > 0:
                sys.exit(1)

        elif args.command == "maintenance":
            print("🧹 Running SQLite maintenance (Checkpoint, Vacuum, Analyze, Log Rotation)...")
            engine.maintenance(wipe_ast=args.wipe_ast)
            print("✅ Database maintenance completed.")

        elif args.command == "knowledge-export":
            engine.export_knowledge(Path(args.output).resolve())

        elif args.command == "knowledge-export-debug":
            engine.export_knowledge_debug(Path(args.output).resolve())

        elif args.command == "knowledge-import":
            engine.import_knowledge(Path(args.input).resolve())

        elif args.command == "knowledge-add":
            added_id = engine.add_knowledge(
                category=args.category,
                content=args.content,
                subcategory=args.subcategory,
                type_=args.type,
                tags=args.tags,
                is_mandatory=args.mandatory,
            )
            if added_id is not None:
                print(f"✅ Knowledge added under category '{args.category}'. Mandatory: {args.mandatory}")
            else:
                print("⚠️ Entry already exists (duplicate). Skipped.")

        elif args.command == "knowledge-import-csv":
            try:
                stats = engine.import_csv(args.file)
                print(
                    f"✅ CSV Import Complete: {stats['imported']} imported, "
                    f"{stats['skipped']} skipped (dupes), {stats['errors']} errors."
                )
            except Exception as e:
                print(f"❌ Failed to import CSV: {e}")
                sys.exit(1)


if __name__ == "__main__":
    main()
