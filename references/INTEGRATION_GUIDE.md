# Cynapse Synaptic Memory: Multi-Agent Integration Guide

This guide details how to install and activate **Cynapse Synaptic Memory** across major AI agent environments in under 2 minutes.

---

## 1. Claude Code (Anthropic CLI)

### Installation
Copy the skill folder into your Claude configuration or repository skills directory:
```bash
# Global installation (available across all projects)
mkdir -p ~/.claude/skills/
cp -r /path/to/cynapse-skill ~/.claude/skills/cynapse-synaptic-memory

# Or project-scoped installation
mkdir -p .claude/skills/
cp -r /path/to/cynapse-skill .claude/skills/cynapse-synaptic-memory
```

### Auto-Trigger via `CLAUDE.md`
Add the following directive to your root `CLAUDE.md`:
```markdown
## Persistent Memory Hook
Before planning or implementing tasks, run:
`python3 ~/.claude/skills/cynapse-synaptic-memory/scripts/synapse_memory.py query "$USER_REQUEST"`
Respect all retrieved [SEMANTIC] and [PROCEDURAL] constraints.
After resolving bugs or receiving user instructions, store key lessons with:
`python3 ~/.claude/skills/cynapse-synaptic-memory/scripts/synapse_memory.py remember --tier procedural|semantic --content "..."`
```

---

## 2. Cursor IDE

### Project Configuration (`.cursorrules`)
Add the following block to your project's `.cursorrules` or `.cursor/rules/memory.mdc`:

```markdown
# Cynapse Synaptic Memory Protocol
You are equipped with lifelong synaptic memory via Cynapse.
1. Recall: When starting a new feature, refactor, or bug fix, run:
   python3 /path/to/cynapse-skill/scripts/synapse_memory.py query "<current problem or symbols>"
2. Keyhole Surgery: Never overwrite entire files. Edit only the target line range.
3. Consolidation: When the user confirms a preference or a bug fix succeeds:
   python3 /path/to/cynapse-skill/scripts/synapse_memory.py remember --tier semantic --content "<rule>"
```

---

## 3. GitHub Copilot CLI & VS Code

### Workspace Instructions (`.github/copilot-instructions.md`)
Add:
```markdown
- Check persistent memories before suggesting major architectural changes:
  `python3 scripts/synapse_memory.py query "architecture"`
- Always record user-specified conventions in semantic memory so subsequent sessions retain them.
```

---

## 4. Antigravity & Open-Standard Agents

### Direct Drop-In
Place the directory into `.agents/skills/`:
```bash
cp -r /path/to/cynapse-skill .agents/skills/cynapse-synaptic-memory
```
The agent host automatically parses `SKILL.md` frontmatter and exposes the memory toolchain.

---

## 5. Verification Command
To verify that the host environment can run the memory engine cleanly:
```bash
python3 /path/to/cynapse-skill/scripts/synapse_memory.py stats
```
Expected output:
```text
========================================
 Cynapse Dendrite Synaptic Memory Stats 
========================================
Database Path : ~/.cynapse/memory.db
...
```
