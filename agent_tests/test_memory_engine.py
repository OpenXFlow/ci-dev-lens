#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_tests/test_memory_engine.py - Unit tests for the ACMI Database Core (v 4.3).
Verifies thread safety, WAL mode, idempotent migrations, Knowledge Bank CLI,
and FTS5 semantic search integration.
"""

import sqlite3
import threading
from pathlib import Path

from agent_core.memory_engine import MemoryEngine


class TestMemoryEngineCore:
    """Test suite for the core capabilities of the MemoryEngine."""

    def test_schema_migration_idempotent(self, tmp_path: Path) -> None:
        """Verify that initializing the database multiple times does not crash and keeps version intact."""
        db_path = tmp_path / "test_idempotent.db"
        engine = MemoryEngine(db_path)

        # Initial check
        health1 = engine.health_check()
        assert health1["tables_ok"] is True
        assert health1["schema_version"] >= 2
        assert health1["pending_migrations"] == 0

        # Second initialization should be silent and idempotent
        engine.init_db()
        health2 = engine.health_check()
        assert health2["schema_version"] >= 2

        engine.close()

    def test_wal_mode_active_on_file(self, tmp_path: Path) -> None:
        """Verify that physical database files correctly enable WAL mode."""
        db_path = tmp_path / "test_wal.db"
        engine = MemoryEngine(db_path)

        # Verify via health check wrapper
        health = engine.health_check()
        assert health["wal_mode"] is True

        # Verify via direct PRAGMA query
        conn = engine.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0].upper()
        assert journal_mode == "WAL"

        engine.close()

    def test_wal_mode_skipped_in_memory(self) -> None:
        """Verify that in-memory databases do not force WAL mode (which is invalid for RAM)."""
        engine = MemoryEngine(":memory:")

        conn = engine.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0].upper()

        # In-memory databases use 'MEMORY' journal mode, not 'WAL'
        assert journal_mode == "MEMORY"

        engine.close()

    def test_thread_isolation(self, tmp_path: Path) -> None:
        """Verify that different threads receive distinct SQLite connection objects."""
        db_path = tmp_path / "test_threads.db"
        engine = MemoryEngine(db_path)

        # Connection in the main thread
        conn_main = engine.get_connection()

        # Shared list to retrieve connection from the background thread
        conn_thread_list: list[sqlite3.Connection] = []

        def worker() -> None:
            # This should create and return a NEW connection for this thread
            conn_thread_list.append(engine.get_connection())

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        conn_worker = conn_thread_list[0]

        # Assert that the objects are strictly different memory instances
        assert conn_main is not conn_worker

        # Clean up
        engine.close()

    def test_context_manager_closes_connection(self, tmp_path: Path) -> None:
        """Verify that __enter__ and __exit__ correctly manage connection lifecycle."""
        db_path = tmp_path / "test_ctx.db"

        with MemoryEngine(db_path) as engine:
            conn = engine.get_connection()
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

            # The connection should exist in the thread local storage
            assert getattr(engine._local, "connection", None) is not None

        # After the context block, the connection should be cleared
        assert getattr(engine._local, "connection", None) is None


class TestMemoryEngineKnowledgeBank:
    """Test suite for Milestone 4 Expert Knowledge features (FTS5, CSV import)."""

    def test_import_export_knowledge_json(self, tmp_path: Path) -> None:
        """Verify that knowledge can be exported and imported without duplicates (Legacy JSON)."""
        db_path = tmp_path / "test_knowledge.db"
        export_path = tmp_path / "export.json"

        # 1. Seed database with one entry
        with MemoryEngine(db_path) as engine:
            conn = engine.get_connection()
            conn.execute(
                """
                INSERT INTO knowledge_bank (source, category, content, confidence_score)
                VALUES ('manual_entry', 'testing', 'Always use pytest.', 1.0)
                """
            )
            conn.commit()

            # 2. Export knowledge
            engine.export_knowledge(export_path)

        assert export_path.exists()

        # 3. Create a fresh DB and import the data
        db_path2 = tmp_path / "test_knowledge_target.db"
        with MemoryEngine(db_path2) as target_engine:
            target_engine.import_knowledge(export_path)

            conn2 = target_engine.get_connection()
            cursor2 = conn2.execute("SELECT COUNT(*) FROM knowledge_bank")
            count_initial = cursor2.fetchone()[0]
            assert count_initial == 1

            # 4. Import again to verify deduplication
            target_engine.import_knowledge(export_path)
            cursor2 = conn2.execute("SELECT COUNT(*) FROM knowledge_bank")
            count_after_duplicate = cursor2.fetchone()[0]
            assert count_after_duplicate == 1

    def test_csv_bulk_import_and_deduplication(self, tmp_path: Path) -> None:
        """Verify parsing of custom CSV files and correct insertion of metadata."""
        db_path = tmp_path / "test_csv_import.db"
        csv_path = tmp_path / "expert_data.csv"

        # Create a mock CSV file simulating ab-testing.csv
        csv_content = (
            "CATEGORY,SUBCATEGORY,TYPE,TAGS,CONTENT\n"
            "ab-testing,design,rule,python;sqlite,Use deterministic hashing for traffic splitting.\n"
            "ab-testing,metrics,anti-pattern,stats,Do not peek at p-values early.\n"
            ",,,,  \n"  # Empty line, should be skipped
        )
        csv_path.write_text(csv_content, encoding="utf-8")

        with MemoryEngine(db_path) as engine:
            stats = engine.import_csv(csv_path)

            assert stats["imported"] == 2
            assert stats["skipped"] == 1  # The empty line
            assert stats["errors"] == 0

            # Verify data persistence and column mapping
            conn = engine.get_connection()
            cursor = conn.execute(
                "SELECT category, type, tags, content FROM knowledge_bank WHERE subcategory = 'design'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row["category"] == "ab-testing"
            assert row["type"] == "rule"
            assert "deterministic hashing" in row["content"]

            # Test deduplication on a second run
            stats2 = engine.import_csv(csv_path)
            assert stats2["imported"] == 0
            assert stats2["skipped"] == 3  # Both valid lines + the empty one are skipped

    def test_fts5_semantic_search(self) -> None:
        """Verify that FTS5 virtual tables and SQL triggers work seamlessly."""
        with MemoryEngine(":memory:") as engine:
            # Add knowledge using the abstraction method
            engine.add_knowledge(
                category="github-actions",
                subcategory="secrets",
                type_="anti-pattern",
                tags="security;yaml",
                content="NEVER store API keys in plain text.",
            )
            engine.add_knowledge(
                category="python",
                subcategory="typing",
                type_="best-practice",
                tags="mypy",
                content="Always use explicit type hints for new functions.",
            )

            # Query 1: Search by content keyword
            results_content = engine.search_knowledge("keys")
            assert len(results_content) == 1
            assert results_content[0]["category"] == "github-actions"

            # Query 2: Search by tag
            results_tag = engine.search_knowledge("mypy")
            assert len(results_tag) == 1
            assert results_tag[0]["type"] == "best-practice"

            # Query 3: Non-existent term
            results_none = engine.search_knowledge("javascript")
            assert len(results_none) == 0

    # ARCHITECT FIX: Commented out Parent-Child test until Milestone 4.5 is officially merged into memory_engine.py
    #  Verify Small-to-Big retrieval logic (Parent-Child relation).
    """
     def test_parent_child_retrieval(self) -> None:
         with MemoryEngine(":memory:") as engine:
             parent_id = engine.add_knowledge(
                 category="architecture",
                 type_="pattern",
                 tags="resilience",
                 content="PARENT_DOC: Always implement a Circuit Breaker.",
             )
             engine.add_knowledge(
                 category="architecture",
                 type_="pattern",
                 content="CHILD_CHUNK: If downstream returns 503 repeatedly.",
                 parent_id=parent_id,
             )
             results = engine.search_knowledge("downstream")
             assert len(results) == 1
             assert "PARENT_DOC:" in results[0]["content"]
    """
