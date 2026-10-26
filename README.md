# Cynapse Synaptic Memory: 4-Tier Biological Memory for AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests: 6/6 Passing](https://img.shields.io/badge/Tests-6%2F6%20Passing-brightgreen.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-orange.svg)]()
[![Offline First](https://img.shields.io/badge/Privacy-100%25%20Local%20%2F%20Air--Gapped-success.svg)]()

> **Give Claude Code, Cursor, Copilot, and Antigravity lifelong persistent memory across sessions — with zero cloud subscriptions, zero API keys, and zero telemetry.**

Derived from the [Cynapse Sovereign Agent Architecture](https://github.com/Alartist40/cynapse).

---

## The Problem: AI Agent Amnesia

When you work with AI coding agents:
1. **Every session starts from zero**: The agent forgets your architecture decisions, database ports, coding conventions, and past bug resolutions the moment you close the terminal or start a new chat.
2. **Context Window Waste**: Frameworks attempt to fix this by stuffing megabytes of raw chat logs into the prompt, exhausting token limits and driving up API costs.
3. **Cloud Surveillance**: Storing memories in hosted vector databases (Pinecone, Chroma Cloud) sends your proprietary codebase patterns and internal secrets across external servers.

---

## The Solution: Cynapse Synaptic Memory

**Cynapse Synaptic Memory** gives any AI agent a compact, biological memory engine:
- **4 Cognitive Tiers**: Working (1d), Episodic (7d), Semantic (30d), and Procedural (90d/Pinned).
- **Ebbinghaus Exponential Decay**: Stale debug traces fade away; frequently recalled rules grow stronger.
- **Microsecond Local Retrieval**: Pure standard-library SQLite (< 2ms per query); no pip packages, no C++ compilation, no Docker daemon.
- **Strict Context Budgeting**: Injects strictly the top 3–5 most relevant memories ($\le 120$ tokens) into the prompt.
- **Keyhole Surgery Guard**: Enforces bounded line replacements to stop agents from truncating large files.

---

## Comparison Matrix

| Feature | Raw Chat History | Cloud Vector DB (Pinecone) | Cynapse Synaptic Memory |
| :--- | :--- | :--- | :--- |
| **Token Overhead** | 3,000–8,000 tokens | 500–1,500 tokens | **< 150 tokens** |
| **Query Latency** | 0ms | 400–900ms (Network) | **< 2ms (In-Memory / SQLite)** |
| **Cloud Dependency** | None | High (External API) | **Zero (100% Air-Gapped)** |
| **Time-Decay Pruning** | None (Static) | None (Manual deletion) | **Automatic (Ebbinghaus)** |
| **Monthly Cost** | API token waste | \$20–\$70/month | **\$0 (Free & Self-Contained)** |

---

## Quickstart (60 Seconds)

### 1. Run Diagnostics & Self-Test
```bash
python3 scripts/synapse_memory.py stats
python3 tests/test_synapse_memory.py
```

### 2. Store a Hardened Project Rule
```bash
python3 scripts/synapse_memory.py remember \
  --tier procedural \
  --content "When running migrations, always test rollback with 'npm run migrate:down'" \
  --tags "database,migrations,testing" \
  --pinned
```

### 3. Query Relevant Memories
```bash
python3 scripts/synapse_memory.py query "database migration"
```
Output:
```markdown
### [Dendrite Synaptic Context (1 memories)]
- **[PROCEDURAL] [PINNED]** When running migrations, always test rollback with 'npm run migrate:down'
```

---

## Supported Agent Frameworks

- **Claude Code**: Drop into `~/.claude/skills/cynapse-synaptic-memory/` and reference in `CLAUDE.md`.
- **Cursor IDE**: Add activation directive into `.cursorrules`.
- **GitHub Copilot**: Add into `.github/copilot-instructions.md`.
- **Antigravity**: Copy to workspace `.agents/skills/`.
- **OpenHands & Windsurf**: Compatible via standard `SKILL.md` parser.

See the complete [Integration Guide](references/INTEGRATION_GUIDE.md) for copy-paste instructions for each platform.

---

## Marketplace & Listing Details (Agensi.io)

This skill package is structured specifically for distribution on [Agensi.io](https://www.agensi.io/sell):
- Standard `SKILL.md` root manifest with valid YAML frontmatter.
- Zero external runtime dependencies (works out of the box on macOS, Linux, and Windows).
- Self-contained automated test suite (`tests/test_synapse_memory.py`).
- Clear non-exclusive licensing (MIT).

### Packaging for Upload
Run the packaging script to generate a clean distribution zip:
```bash
bash package_skill.sh
```
This produces `cynapse-synaptic-memory.zip` ready for upload to your Agensi seller dashboard.

---

## Attribution & Parent Project

Cynapse Synaptic Memory is open-source technology developed by **Xander (Alartist40)** as part of the **Cynapse Sovereign Edge AI Agent** ecosystem.

- **Main Repository**: [https://github.com/Alartist40/cynapse](https://github.com/Alartist40/cynapse)
- **License**: MIT
