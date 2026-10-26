#!/usr/bin/env python3
"""
Unit tests for Synapse Memory Engine (Cynapse Dendrite Architecture).
Runs with standard library unittest - zero external dependencies.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import synapse_memory

class TestSynapseMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.conn = synapse_memory.get_connection(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_schema_initialization(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_nodes'")
        row = cursor.fetchone()
        self.assertIsNotNone(row)

    def test_hash_consistency(self):
        h1 = synapse_memory.compute_hash("Always compile before commit", "procedural")
        h2 = synapse_memory.compute_hash("  always compile before commit  ", "procedural")
        self.assertEqual(h1, h2)

    def test_remember_and_reinforce(self):
        # Insert
        args = type("Args", (), {
            "db": self.db_path,
            "tier": "semantic",
            "content": "User prefers strict typing in TypeScript",
            "tags": "typescript,types,preferences",
            "half_life": None,
            "pinned": False,
        })()
        ret = synapse_memory.cmd_remember(args)
        self.assertEqual(ret, 0)

        cursor = self.conn.cursor()
        cursor.execute("SELECT access_count, pinned FROM memory_nodes")
        row = cursor.fetchone()
        self.assertEqual(row["access_count"], 1)
        self.assertEqual(row["pinned"], 0)

        # Reinforce with pin
        args.pinned = True
        synapse_memory.cmd_remember(args)
        cursor.execute("SELECT access_count, pinned FROM memory_nodes")
        row = cursor.fetchone()
        self.assertEqual(row["access_count"], 2)
        self.assertEqual(row["pinned"], 1)

    def test_query_ranking(self):
        # Insert 3 memories
        memories = [
            ("procedural", "Run cargo test --workspace before pushing code", "rust,cargo,test"),
            ("semantic", "Database credentials are stored in local .env only", "db,postgres,secrets"),
            ("episodic", "Fixed bug in token compression logic yesterday", "bug,compression,tokens"),
        ]
        for tier, content, tags in memories:
            args = type("Args", (), {
                "db": self.db_path,
                "tier": tier,
                "content": content,
                "tags": tags,
                "half_life": None,
                "pinned": False,
            })()
            synapse_memory.cmd_remember(args)

        # Query for 'cargo'
        args_query = type("Args", (), {
            "db": self.db_path,
            "query": "cargo test runner",
            "limit": 2,
            "json": True,
            "all": False,
        })()
        
        # Capture stdout
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            synapse_memory.cmd_query(args_query)
        import json
        results = json.loads(f.getvalue())
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["tier"], "procedural")
        self.assertIn("cargo test", results[0]["content"])

    def test_decay_calculation(self):
        now = 1000000.0
        # 0 elapsed time -> decay = 1.0
        decay_0 = synapse_memory.calculate_decay(now, now, 7.0, current_time=now)
        self.assertAlmostEqual(decay_0, 1.0, places=4)

        # 7 days elapsed (half life) -> decay = 0.5
        seven_days_ago = now - (7.0 * 86400.0)
        decay_half = synapse_memory.calculate_decay(now, seven_days_ago, 7.0, current_time=now)
        self.assertAlmostEqual(decay_half, 0.5, places=2)

    def test_pruning_unpinned(self):
        # Insert old unpinned memory
        h = synapse_memory.compute_hash("Old ephemeral log", "working")
        old_time = 1000.0
        self.conn.execute("""
            INSERT INTO memory_nodes (id, tier, content, tags, created_at, last_accessed_at, access_count, half_life_days, pinned, hash)
            VALUES ('mem_old', 'working', 'Old ephemeral log', 'log', ?, ?, 1, 1.0, 0, ?)
        """, (old_time, old_time, h))
        self.conn.commit()

        # Prune with threshold 0.1
        args_prune = type("Args", (), {"db": self.db_path, "threshold": 0.1})()
        synapse_memory.cmd_prune(args_prune)

        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) as count FROM memory_nodes WHERE id = 'mem_old'")
        self.assertEqual(cursor.fetchone()["count"], 0)

if __name__ == "__main__":
    unittest.main()
