# Spectree

Hierarchical specification and planning tree for AI-assisted software development. Alpha.

---

## Overview

Spectree manages a tree of well-defined specifications and plans for complex software projects. It provides organizational structure for AI agents to collaborate on planning, take ownership of work segments, propose spec changes, and track progress across a project hierarchy.

Spectree is served as an MCP (Model Context Protocol) server, enabling any MCP-compatible AI client to interact with the spec tree.

---

## Where It Fits

```
AI Agents (Adele, Claude, etc.)
    │ MCP protocol
    ▼
SPECTREE (MCP server)
    │
    ▼
MAUSOLEUM (persistent storage)
    │
    ▼
VALET + ZEUS (deployment)
```

---

## Node Types

Spectree organizes work in three node types:

| Type | Meaning | Examples |
|------|---------|---------|
| **Org** | Root organizational context | "Ritz Language", "Q1 2026" |
| **Spec** | Declarative truth — what IS or SHOULD BE | "Type System", "Async Model" |
| **Plan** | Imperative work — what TO DO | "Implement Generics", "Port HTTP Module" |

---

## Tree Structure Example

```
Org: "Ritz Language"
  Spec: "Language Design"
    Spec: "Type System"
      Plan: "Implement Generics"    <- agent owns this
    Spec: "Async Model"
  Spec: "Standard Library"
    Plan: "Port HTTP Module"
  Plan: "Q1 2026 Roadmap"
    Plan: "Phase 1: Core Compiler"
    Plan: "Phase 2: Stdlib"
```

---

## Key Features

- **Tree structure** — Parent/child relationships for hierarchical planning
- **Graph links** — Nodes can link to each other: `Implements`, `DependsOn`, `RelatedTo`
- **Agent ownership** — Assign responsibility for a node to a specific agent
- **Conversation history** — Each node has an attached discussion thread
- **Status tracking** — Draft → InProgress → Review → Complete → Archived
- **MCP server** — Standard interface for AI clients
- **Node splitting** — Break large specs/plans into smaller pieces as scope clarifies
- **Full version history** — Via Mausoleum's MVCC

---

## API

### Ritz Library

```ritz
import spectree { Tree, Node, NodeKind }

let tree = Tree.open("project.m7m")

# Create nodes
let org  = tree.create(NodeKind.Org, "Ritz Language", null)
let spec = tree.create(NodeKind.Spec, "Type System", org.id)
let plan = tree.create(NodeKind.Plan, "Implement Generics", spec.id)

# Link nodes
tree.link(plan.id, spec.id, LinkKind.Implements)

# Claim ownership
tree.claim(plan.id, "adele-agent-1")

# Query
let all_plans = tree.descendants(org.id).filter_kind(NodeKind.Plan)
let drafts = tree.query().kind(NodeKind.Spec).status(Status.Draft).exec()
```

### MCP Server

```bash
spectree serve --port 9090
```

Available MCP operations:
- `spectree.get_node(id)` — Get a node by ID
- `spectree.list_children(id)` — List child nodes
- `spectree.create_node(parent, kind, title, content)` — Create a new node
- `spectree.update_node(id, changes)` — Update node fields
- `spectree.claim_ownership(node_id, agent_id)` — Assign ownership
- `spectree.propose_change(node_id, proposal)` — Propose a spec change
- `spectree.append_message(node_id, message)` — Add to conversation

---

## Current Status

Alpha. Data model, node types, and MCP interface are designed. Core tree operations and Mausoleum persistence are being implemented.

---

## Related Projects

- [Mausoleum](mausoleum.md) — Primary storage backend (full version history)
- [Zeus](zeus.md) — App server for deployment
- [Valet](valet.md) — HTTP server for the MCP endpoint
- [Nexus](nexus.md) — Uses Spectree concepts for wiki organization
