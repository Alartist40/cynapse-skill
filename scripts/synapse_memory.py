#!/usr/bin/env python3
"""
Synapse Memory Engine - Standalone 4-Tier Biological Memory CLI
Based on Cynapse Dendrite Architecture (https://github.com/Alartist40/cynapse)

Zero external dependencies (uses standard library sqlite3, math, json).
Provides persistent episodic, semantic, procedural, and working memory
with Ebbinghaus time-decay, BM25 keyword matching, and frequency reinforcement.
"""

import sys
import os
import re
import json
import time
import math
import hashlib
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_DB_DIR = Path.home() / ".cynapse"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "memory.db"

# Tier half-lives in days
HALF_LIVES = {
    "working": 1.0,       # Transient context, expires fast
    "episodic": 7.0,      # Session history, recedes over days
    "semantic": 30.0,     # Domain knowledge & constraints, persists across projects
    "procedural": 90.0,   # Execution rules, playbooks, error fixes
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_nodes (
    id TEXT PRIMARY KEY,
    tier TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL,
    created_at REAL NOT NULL,
    last_accessed_at REAL NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 1,
    half_life_days REAL NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0,
    hash TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_tier ON memory_nodes(tier);
CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory_nodes(last_accessed_at);
"""

def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.executescript(SCHEMA)
    return conn

def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into lowercase alphanumeric words."""
    return re.findall(r'[a-zA-Z0-9_\-\.]+', text.lower())

def compute_hash(content: str, tier: str) -> str:
    norm = re.sub(r'\s+', ' ', content.strip().lower())
    return hashlib.sha256(f"{tier}:{norm}".encode('utf-8')).hexdigest()[:16]

def calculate_decay(created_at: float, last_accessed_at: float, half_life_days: float, current_time: Optional[float] = None) -> float:
    """Calculates biological decay using exponential half-life formula."""
    now = current_time if current_time is not None else time.time()
    elapsed_seconds = max(0.0, now - last_accessed_at)
    half_life_seconds = half_life_days * 86400.0
    if half_life_seconds <= 0:
        return 1.0
    decay_lambda = math.log(2.0) / half_life_seconds
    return math.exp(-decay_lambda * elapsed_seconds)

def compute_relevance(query_tokens: List[str], content_tokens: List[str], tag_tokens: List[str]) -> float:
    """Computes bounded term match score across content and tags."""
    if not query_tokens or not content_tokens:
        return 0.0
    
    score = 0.0
    content_set = set(content_tokens)
    tag_set = set(tag_tokens)
    
    for qt in query_tokens:
        if qt in tag_set:
            score += 2.0  # Tag matches carry double weight
        elif qt in content_set:
            score += 1.0
        else:
            # Substring match for identifiers
            for ct in content_set:
                if len(qt) > 3 and qt in ct:
                    score += 0.5
                    break
                    
    # Normalized by log query length
    norm = math.log(1.0 + len(query_tokens)) + 1.0
    return score / norm

def cmd_remember(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    tier = args.tier.lower()
    if tier not in HALF_LIVES:
        print(f"Error: Invalid tier '{tier}'. Must be one of: {list(HALF_LIVES.keys())}", file=sys.stderr)
        return 1

    content = args.content.strip()
    if not content:
        print("Error: Content cannot be empty.", file=sys.stderr)
        return 1

    tags = ",".join([t.strip().lower() for t in args.tags.split(",") if t.strip()]) if args.tags else ""
    half_life = float(args.half_life) if args.half_life else HALF_LIVES[tier]
    pinned = 1 if args.pinned else 0
    node_hash = compute_hash(content, tier)
    now = time.time()
    node_id = f"mem_{node_hash[:8]}"

    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, access_count FROM memory_nodes WHERE hash = ?", (node_hash,))
        existing = cursor.fetchone()
        if existing:
            # Reinforce existing memory
            cursor.execute("""
                UPDATE memory_nodes
                SET last_accessed_at = ?,
                    access_count = access_count + 1,
                    tags = CASE WHEN length(?) > 0 THEN ? ELSE tags END,
                    pinned = max(pinned, ?)
                WHERE hash = ?
            """, (now, tags, tags, pinned, node_hash))
            print(f"[REINFORCED] Memory {existing['id']} (Accesses: {existing['access_count'] + 1})")
        else:
            cursor.execute("""
                INSERT INTO memory_nodes (
                    id, tier, content, tags, created_at, last_accessed_at,
                    access_count, half_life_days, pinned, hash
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (node_id, tier, content, tags, now, now, half_life, pinned, node_hash))
            print(f"[STORED] Memory {node_id} ({tier.upper()}) | Half-Life: {half_life}d")

    return 0

def cmd_query(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    query_text = args.query.strip()
    if not query_text:
        return 0

    query_tokens = tokenize(query_text)
    if not query_tokens:
        return 0

    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tier, content, tags, created_at, last_accessed_at,
               access_count, half_life_days, pinned, hash
        FROM memory_nodes
    """)
    rows = cursor.fetchall()
    if not rows:
        return 0

    scored_nodes = []
    now = time.time()

    for row in rows:
        content_tokens = tokenize(row["content"])
        tag_tokens = tokenize(row["tags"])
        
        match_score = compute_relevance(query_tokens, content_tokens, tag_tokens)
        if match_score <= 0.0 and not args.all:
            continue

        decay = calculate_decay(row["created_at"], row["last_accessed_at"], row["half_life_days"])
        if row["pinned"]:
            decay = 1.0  # Pinned memories do not decay

        freq_boost = min(1.0, 0.2 * math.log(1.0 + row["access_count"]))
        composite_score = (match_score * 0.7 + 0.1) * (0.6 * decay + 0.4 * freq_boost)

        scored_nodes.append((composite_score, row))

    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored_nodes[:args.limit]

    if not top_matches:
        return 0

    # Auto-reinforce matched memories
    with conn:
        for score, row in top_matches:
            conn.execute("""
                UPDATE memory_nodes
                SET last_accessed_at = ?, access_count = access_count + 1
                WHERE id = ?
            """, (now, row["id"]))

    if args.json:
        output = [
            {
                "id": r["id"],
                "tier": r["tier"],
                "content": r["content"],
                "tags": r["tags"].split(",") if r["tags"] else [],
                "score": round(score, 4),
                "pinned": bool(r["pinned"]),
                "access_count": r["access_count"] + 1,
            }
            for score, r in top_matches
        ]
        print(json.dumps(output, indent=2))
    else:
        print(f"### [Dendrite Synaptic Context ({len(top_matches)} memories)]")
        for score, r in top_matches:
            tier_badge = f"[{r['tier'].upper()}]"
            pin_badge = " [PINNED]" if r["pinned"] else ""
            print(f"- **{tier_badge}{pin_badge}** {r['content']}")

    return 0

def cmd_prune(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    cursor = conn.cursor()
    cursor.execute("SELECT id, tier, created_at, last_accessed_at, half_life_days, pinned FROM memory_nodes WHERE pinned = 0")
    rows = cursor.fetchall()
    
    threshold = args.threshold
    to_delete = []

    for r in rows:
        decay = calculate_decay(r["created_at"], r["last_accessed_at"], r["half_life_days"])
        if decay < threshold:
            to_delete.append(r["id"])

    if to_delete:
        with conn:
            cursor.executemany("DELETE FROM memory_nodes WHERE id = ?", [(id_,) for id_ in to_delete])
        print(f"[PRUNED] Cleaned up {len(to_delete)} decayed memory nodes below threshold {threshold}.")
    else:
        print(f"[OK] No memories below decay threshold {threshold}.")

    return 0

def cmd_stats(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) as total FROM memory_nodes")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT tier, count(*) as count FROM memory_nodes GROUP BY tier")
    tier_counts = {r["tier"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("SELECT count(*) as count FROM memory_nodes WHERE pinned = 1")
    pinned_count = cursor.fetchone()["count"]

    size_bytes = args.db.stat().st_size if args.db.exists() else 0

    print("========================================")
    print(" Cynapse Dendrite Synaptic Memory Stats ")
    print("========================================")
    print(f"Database Path : {args.db}")
    print(f"Database Size : {size_bytes / 1024:.1f} KB")
    print(f"Total Memories: {total}")
    print(f"Pinned Nodes  : {pinned_count}")
    print("Tier Breakdown:")
    for tier in ["working", "episodic", "semantic", "procedural"]:
        print(f"  - {tier.capitalize():<12}: {tier_counts.get(tier, 0)}")
    print("========================================")
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Cynapse Synaptic Memory Engine - Standalone 4-Tier Memory for AI Agents"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("CYNAPSE_MEMORY_DB", str(DEFAULT_DB_PATH))),
        help="Path to SQLite memory database (default: ~/.cynapse/memory.db)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # remember
    p_remember = subparsers.add_parser("remember", help="Store or reinforce a memory")
    p_remember.add_argument("--tier", choices=["working", "episodic", "semantic", "procedural"], default="episodic")
    p_remember.add_argument("--content", required=True, help="Memory content to store")
    p_remember.add_argument("--tags", help="Comma-separated keyword tags")
    p_remember.add_argument("--half-life", type=float, help="Custom decay half-life in days")
    p_remember.add_argument("--pinned", action="store_true", help="Pin permanently to prevent decay")

    # query
    p_query = subparsers.add_parser("query", help="Retrieve relevant memories for a prompt")
    p_query.add_argument("query", help="Query string or current prompt context")
    p_query.add_argument("--limit", type=int, default=4, help="Maximum memories to return (default: 4)")
    p_query.add_argument("--json", action="store_true", help="Output as JSON instead of Markdown")
    p_query.add_argument("--all", action="store_true", help="Include low-relevance memories")

    # prune
    p_prune = subparsers.add_parser("prune", help="Prune decayed memories")
    p_prune.add_argument("--threshold", type=float, default=0.05, help="Decay threshold for deletion (default: 0.05)")

    # stats
    subparsers.add_parser("stats", help="Show memory database statistics")

    args = parser.parse_args()

    if args.command == "remember":
        sys.exit(cmd_remember(args))
    elif args.command == "query":
        sys.exit(cmd_query(args))
    elif args.command == "prune":
        sys.exit(cmd_prune(args))
    elif args.command == "stats":
        sys.exit(cmd_stats(args))

if __name__ == "__main__":
    main()
