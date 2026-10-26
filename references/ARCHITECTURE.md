# Cynapse Synaptic Memory Architecture

> **Source**: Derived from the [Cynapse Sovereign Edge Agent System](https://github.com/Alartist40/cynapse).

---

## 1. The Problem with Naive Agent Memory

Most AI agent memory systems make one of two mistakes:
1. **Chat History Dumps**: They inject the last 50 conversation turns into the prompt. On a model with a 4k or 8k context window, this consumes 80% of available tokens on stale chatter, leaving no room for actual source code or compiler diagnostics.
2. **Naive Cloud Vector DBs**: They send every user message to a remote vector database (Pinecone, Weaviate, Chroma). This introduces 500ms network latency, incurs monthly API bills, and leaks confidential code to third-party cloud servers. Furthermore, standard vector search treats a memory from 6 months ago with the exact same weight as a memory from 5 minutes ago.

---

## 2. The 4-Tier Biological Model

Human cognition does not store all memories in one flat bucket. It uses specialized cognitive subsystems:

```
┌────────────────────────────────────────────────────────┐
│ 1. WORKING MEMORY (Half-Life: 1 Day)                   │
│    Active scratchpad, current task blockers, PID logs  │
├────────────────────────────────────────────────────────┤
│ 2. EPISODIC MEMORY (Half-Life: 7 Days)                 │
│    Chronological execution timeline, past debug logs   │
├────────────────────────────────────────────────────────┤
│ 3. SEMANTIC MEMORY (Half-Life: 30 Days)                │
│    Facts, domain constraints, architecture patterns    │
├────────────────────────────────────────────────────────┤
│ 4. PROCEDURAL MEMORY (Half-Life: 90 Days / Pinned)     │
│    Hardened playbooks, verified fixes, invariant rules │
└────────────────────────────────────────────────────────┘
```

### Tier Transitions & Reinforcement
When an agent encounters a repeated pattern:
- An observation starts in **Working** or **Episodic** memory.
- If repeatedly accessed or verified across multiple tasks, its access count increases and it can be promoted to **Semantic** or **Procedural** memory.
- Unreinforced memories decay naturally toward zero and are pruned, keeping the SQLite database small, cache-resident, and lightning fast (< 2ms query latency).

---

## 3. Mathematical Foundations

### Ebbinghaus Decay Function
The retention probability $R(t)$ follows exponential decay:

$$R(t) = e^{-\lambda \Delta t}$$

Where:
- $\Delta t$ is elapsed time since last retrieval: $t_{\text{current}} - t_{\text{accessed}}$
- $\lambda = \frac{\ln(2)}{T_{1/2}}$ ($T_{1/2}$ is the tier half-life in seconds).

### Frequency Reinforcement Boost
To model synaptic long-term potentiation (LTP), each retrieval reinforces the memory:

$$F(c) = 1 + 0.2 \cdot \ln(1 + c)$$

Where $c$ is the access count.

### Composite Relevance Score
When a query arrives, the system computes:

$$\text{Score} = (S_{\text{match}} \cdot 0.7 + 0.1) \times (0.6 \cdot R(t) + 0.4 \cdot \min(1.0, 0.2 \cdot \ln(1 + c)))$$

Where $S_{\text{match}}$ is the keyword/token overlap score against content and tags.

---

## 4. Keyhole Surgery File Modification Guard

A common defect in autonomous coding agents is **file overwriting amnesia**:
- To change 3 lines in an 800-line file, the model attempts to generate all 800 lines.
- It hits output token limits at line 450, truncating the file and destroying production code.
- Cynapse Synaptic Memory enforces **Keyhole Surgery**:
  - Edits must specify targeted line ranges.
  - The agent replaces only the surgical diff.
  - If lines do not match, the patch aborts immediately rather than writing corrupted partial text.
