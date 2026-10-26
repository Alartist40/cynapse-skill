use clap::{Parser, Subcommand, ValueEnum};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Parser)]
#[command(name = "cynapse-synaptic-memory")]
#[command(about = "Pure Rust 4-Tier Biological Memory CLI for AI Agents", long_about = None)]
struct Cli {
    #[arg(long, help = "Path to SQLite database (default: ~/.cynapse/memory.db)")]
    db: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Remember {
        #[arg(long, value_enum, default_value_t = MemoryTier::Episodic)]
        tier: MemoryTier,

        #[arg(long, help = "Memory content")]
        content: String,

        #[arg(long, help = "Comma-separated tags")]
        tags: Option<String>,

        #[arg(long, help = "Custom decay half-life in days")]
        half_life: Option<f64>,

        #[arg(long, help = "Pin permanently to prevent decay")]
        pinned: bool,
    },

    Query {
        #[arg(help = "Query prompt or keywords")]
        query: String,

        #[arg(long, default_value_t = 4, help = "Max memories to return")]
        limit: usize,

        #[arg(long, help = "Output formatted as JSON")]
        json: bool,

        #[arg(long, help = "Include low-relevance memories")]
        all: bool,
    },

    Prune {
        #[arg(long, default_value_t = 0.05, help = "Retention decay threshold")]
        threshold: f64,
    },

    Stats,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Serialize, Deserialize, Debug)]
#[serde(rename_all = "lowercase")]
enum MemoryTier {
    Working,
    Episodic,
    Semantic,
    Procedural,
}

impl MemoryTier {
    fn as_str(&self) -> &'static str {
        match self {
            MemoryTier::Working => "working",
            MemoryTier::Episodic => "episodic",
            MemoryTier::Semantic => "semantic",
            MemoryTier::Procedural => "procedural",
        }
    }

    fn default_half_life_days(&self) -> f64 {
        match self {
            MemoryTier::Working => 1.0,
            MemoryTier::Episodic => 7.0,
            MemoryTier::Semantic => 30.0,
            MemoryTier::Procedural => 90.0,
        }
    }
}

#[derive(Serialize, Deserialize)]
struct MemoryNode {
    id: String,
    tier: String,
    content: String,
    tags: String,
    created_at: f64,
    last_accessed_at: f64,
    access_count: i64,
    half_life_days: f64,
    pinned: i64,
    hash: String,
}

#[derive(Serialize)]
struct QueryResultJson {
    id: String,
    tier: String,
    content: String,
    tags: Vec<String>,
    score: f64,
    pinned: bool,
    access_count: i64,
}

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}

fn resolve_db_path(custom: Option<PathBuf>) -> PathBuf {
    if let Some(p) = custom {
        return p;
    }
    if let Ok(env_path) = std::env::var("CYNAPSE_MEMORY_DB") {
        return PathBuf::from(env_path);
    }
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
    home.join(".cynapse").join("memory.db")
}

fn init_db(db_path: &PathBuf) -> Connection {
    if let Some(parent) = db_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let conn = Connection::open(db_path).expect("Failed to open SQLite database");
    conn.execute_batch(
        r#"
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
        "#,
    )
    .expect("Failed to initialize database schema");
    conn
}

fn tokenize(text: &str) -> Vec<String> {
    text.split(|c: char| !c.is_alphanumeric() && c != '_' && c != '-' && c != '.')
        .filter(|s| !s.is_empty())
        .map(|s| s.to_lowercase())
        .collect()
}

fn compute_hash(content: &str, tier: &str) -> String {
    let norm = content.trim().to_lowercase();
    let mut hasher = Sha256::new();
    hasher.update(format!("{}:{}", tier, norm).as_bytes());
    let hex = format!("{:x}", hasher.finalize());
    hex[..16].to_string()
}

fn calculate_decay(last_accessed_at: f64, half_life_days: f64, now: f64) -> f64 {
    let elapsed = (now - last_accessed_at).max(0.0);
    let half_life_secs = half_life_days * 86400.0;
    if half_life_secs <= 0.0 {
        return 1.0;
    }
    let lambda = 2.0_f64.ln() / half_life_secs;
    (-lambda * elapsed).exp()
}

fn compute_relevance(query_tokens: &[String], content_tokens: &[String], tag_tokens: &[String]) -> f64 {
    if query_tokens.is_empty() || content_tokens.is_empty() {
        return 0.0;
    }
    let mut score = 0.0;
    for qt in query_tokens {
        if tag_tokens.contains(qt) {
            score += 2.0;
        } else if content_tokens.contains(qt) {
            score += 1.0;
        } else {
            for ct in content_tokens {
                if qt.len() > 3 && ct.contains(qt) {
                    score += 0.5;
                    break;
                }
            }
        }
    }
    let norm = (1.0 + query_tokens.len() as f64).ln() + 1.0;
    score / norm
}

fn main() {
    let cli = Cli::parse();
    let db_path = resolve_db_path(cli.db);
    let mut conn = init_db(&db_path);

    match cli.command {
        Commands::Remember {
            tier,
            content,
            tags,
            half_life,
            pinned,
        } => {
            let content = content.trim();
            if content.is_empty() {
                eprintln!("Error: Content cannot be empty.");
                std::process::exit(1);
            }
            let tier_str = tier.as_str();
            let norm_tags = tags
                .map(|t| {
                    t.split(',')
                        .map(|s| s.trim().to_lowercase())
                        .filter(|s| !s.is_empty())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default();
            let half_life_val = half_life.unwrap_or_else(|| tier.default_half_life_days());
            let node_hash = compute_hash(content, tier_str);
            let node_id = format!("mem_{}", &node_hash[..8]);
            let now = now_secs();
            let pin_val = if pinned { 1 } else { 0 };

            let existing_id: rusqlite::Result<String> = conn.query_row(
                "SELECT id FROM memory_nodes WHERE hash = ?1",
                params![node_hash],
                |row| row.get(0),
            );

            if let Ok(id) = existing_id {
                conn.execute(
                    r#"
                    UPDATE memory_nodes
                    SET last_accessed_at = ?1,
                        access_count = access_count + 1,
                        tags = CASE WHEN length(?2) > 0 THEN ?2 ELSE tags END,
                        pinned = max(pinned, ?3)
                    WHERE hash = ?4
                    "#,
                    params![now, norm_tags, pin_val, node_hash],
                )
                .expect("Failed to update existing memory");
                println!("[REINFORCED] Memory {} (Access Count Reinforced)", id);
            } else {
                conn.execute(
                    r#"
                    INSERT INTO memory_nodes (
                        id, tier, content, tags, created_at, last_accessed_at,
                        access_count, half_life_days, pinned, hash
                    ) VALUES (?1, ?2, ?3, ?4, ?5, ?5, 1, ?6, ?7, ?8)
                    "#,
                    params![node_id, tier_str, content, norm_tags, now, half_life_val, pin_val, node_hash],
                )
                .expect("Failed to insert new memory");
                println!(
                    "[STORED] Memory {} ({}) | Half-Life: {:.1}d",
                    node_id,
                    tier_str.to_uppercase(),
                    half_life_val
                );
            }
        }

        Commands::Query {
            query,
            limit,
            json,
            all,
        } => {
            let query = query.trim();
            if query.is_empty() {
                return;
            }
            let query_tokens = tokenize(query);
            if query_tokens.is_empty() {
                return;
            }

            let mut stmt = conn
                .prepare(
                    r#"
                    SELECT id, tier, content, tags, created_at, last_accessed_at,
                           access_count, half_life_days, pinned, hash
                    FROM memory_nodes
                    "#,
                )
                .expect("Failed to prepare query");

            let node_iter = stmt
                .query_map([], |row| {
                    Ok(MemoryNode {
                        id: row.get(0)?,
                        tier: row.get(1)?,
                        content: row.get(2)?,
                        tags: row.get(3)?,
                        created_at: row.get(4)?,
                        last_accessed_at: row.get(5)?,
                        access_count: row.get(6)?,
                        half_life_days: row.get(7)?,
                        pinned: row.get(8)?,
                        hash: row.get(9)?,
                    })
                })
                .expect("Failed to read memory nodes");

            let now = now_secs();
            let mut scored = Vec::new();

            for node_res in node_iter {
                if let Ok(node) = node_res {
                    let content_tokens = tokenize(&node.content);
                    let tag_tokens = tokenize(&node.tags);
                    let match_score = compute_relevance(&query_tokens, &content_tokens, &tag_tokens);

                    if match_score <= 0.0 && !all {
                        continue;
                    }

                    let decay = if node.pinned != 0 {
                        1.0
                    } else {
                        calculate_decay(node.last_accessed_at, node.half_life_days, now)
                    };

                    let freq_boost = (0.2 * (1.0 + node.access_count as f64).ln()).min(1.0);
                    let composite = (match_score * 0.7 + 0.1) * (0.6 * decay + 0.4 * freq_boost);
                    scored.push((composite, node));
                }
            }

            scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
            let top_matches: Vec<_> = scored.into_iter().take(limit).collect();

            if top_matches.is_empty() {
                return;
            }

            // Auto-reinforce accessed memories
            for (_, node) in &top_matches {
                let _ = conn.execute(
                    "UPDATE memory_nodes SET last_accessed_at = ?1, access_count = access_count + 1 WHERE id = ?2",
                    params![now, node.id],
                );
            }

            if json {
                let json_items: Vec<_> = top_matches
                    .iter()
                    .map(|(score, n)| QueryResultJson {
                        id: n.id.clone(),
                        tier: n.tier.clone(),
                        content: n.content.clone(),
                        tags: n.tags.split(',').map(|s| s.to_string()).filter(|s| !s.is_empty()).collect(),
                        score: (score * 10000.0).round() / 10000.0,
                        pinned: n.pinned != 0,
                        access_count: n.access_count + 1,
                    })
                    .collect();
                println!("{}", serde_json::to_string_pretty(&json_items).unwrap());
            } else {
                println!("### [Dendrite Synaptic Context ({} memories)]", top_matches.len());
                for (_, n) in &top_matches {
                    let pin_badge = if n.pinned != 0 { " [PINNED]" } else { "" };
                    println!("- **[{}]{}** {}", n.tier.to_uppercase(), pin_badge, n.content);
                }
            }
        }

        Commands::Prune { threshold } => {
            let mut stmt = conn
                .prepare("SELECT id, last_accessed_at, half_life_days FROM memory_nodes WHERE pinned = 0")
                .expect("Failed to prepare prune");

            let now = now_secs();
            let mut to_delete = Vec::new();

            let rows = stmt
                .query_map([], |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, f64>(1)?,
                        row.get::<_, f64>(2)?,
                    ))
                })
                .expect("Failed to query prune candidates");

            for row in rows.flatten() {
                let (id, accessed, half_life) = row;
                let decay = calculate_decay(accessed, half_life, now);
                if decay < threshold {
                    to_delete.push(id);
                }
            }
            drop(stmt);

            if !to_delete.is_empty() {
                let tx = conn.transaction().expect("Failed transaction");
                for id in &to_delete {
                    tx.execute("DELETE FROM memory_nodes WHERE id = ?1", params![id])
                        .expect("Failed delete");
                }
                tx.commit().expect("Failed commit");
                println!(
                    "[PRUNED] Cleaned up {} decayed memory nodes below threshold {}.",
                    to_delete.len(),
                    threshold
                );
            } else {
                println!("[OK] No memories below decay threshold {}.", threshold);
            }
        }

        Commands::Stats => {
            let total: i64 = conn
                .query_row("SELECT count(*) FROM memory_nodes", [], |r| r.get(0))
                .unwrap_or(0);
            let pinned: i64 = conn
                .query_row("SELECT count(*) FROM memory_nodes WHERE pinned = 1", [], |r| r.get(0))
                .unwrap_or(0);

            let size_bytes = fs::metadata(&db_path).map(|m| m.len()).unwrap_or(0);

            println!("========================================");
            println!(" Cynapse Dendrite Synaptic Memory (Rust)");
            println!("========================================");
            println!("Database Path : {}", db_path.display());
            println!("Database Size : {:.1} KB", size_bytes as f64 / 1024.0);
            println!("Total Memories: {}", total);
            println!("Pinned Nodes  : {}", pinned);
            println!("Engine        : Native Rust (Zero Python / Zero Daemon)");
            println!("========================================");
        }
    }
}
