# Spectree

Hierarchical specification and planning tree for AI-assisted software development. Built in Ritz, served over Zeus/Valet.

## Overview

Spectree manages a tree of well-defined specifications and plans. It provides the organizational structure for complex projects where AI agents (like Adele) can collaborate on planning, own segments of work, and propose changes to specs.

## Concepts

### Node Types

| Type | Purpose | Contains |
|------|---------|----------|
| **Org** | Root node | Top-level organizational context |
| **Spec** | Declarative truth | What IS or SHOULD BE |
| **Plan** | Imperative work | What TO DO |

### Tree Structure

```
Org: "Ritz Language"
├── Spec: "Language Design"
│   ├── Spec: "Type System"
│   │   ├── Spec: "Borrowing Semantics"
│   │   └── Spec: "Generic Constraints"
│   └── Spec: "Async Model"
│       └── Plan: "Implement Async/Await"  ← agent owns this
├── Spec: "Standard Library"
│   └── Spec: "HTTP Module"
│       └── Plan: "Port from Valet"
└── Plan: "Q1 2025 Roadmap"
    ├── Plan: "Phase 1: Core Compiler"
    └── Plan: "Phase 2: Stdlib"
```

### Links

Plans reference the specs they implement or modify. Specs can reference other specs they depend on.

## Agent Integration

Spectree is designed for AI agent collaboration:

### Conversation History
Each node has an attached conversation history - like a "room" in Adele's UI.

```
┌─────────────────────────────────────────────┐
│  Node: "Borrowing Semantics Spec"           │
├─────────────────────────────────────────────┤
│  Status: Draft                              │
│  Agents: @adele-1 (owner), @adele-2 (review)│
├─────────────────────────────────────────────┤
│  [Conversation History]                     │
│  [Proposed Changes]                         │
│  [Child Nodes]                              │
└─────────────────────────────────────────────┘
```

### Agent Capabilities

- **Own** a node (responsible for completion)
- **Collaborate** on planning phases (turn-by-turn chat)
- **Propose** spec changes or plan adjustments
- **Split/merge** nodes as scope clarifies
- **Complete** segments and update status

## Architecture

Spectree is:
- **Separate** from Adele's UI (clean separation of concerns)
- **Hookable** by Adele's ecosystem (MCP server interface)
- **Built in Ritz** (dogfooding the language)
- **Served over Zeus/Valet** (dogfooding the stack)

```
┌─────────────────────────────────────────────┐
│              Adele UI                       │
│         (or any MCP client)                 │
└───────────────────┬─────────────────────────┘
                    │ MCP Protocol
┌───────────────────▼─────────────────────────┐
│              Spectree                       │
│         (Ritz application)                  │
└───────────────────┬─────────────────────────┘
                    │ Zeus Protocol
┌───────────────────▼─────────────────────────┐
│           Valet + Zeus                      │
│         (HTTP server layer)                 │
└─────────────────────────────────────────────┘
```

## Data Model

```ritz
enum NodeKind {
    Org,
    Spec,
    Plan,
}

struct Node {
    id: Uuid,
    kind: NodeKind,
    title: String,
    content: Markdown,
    status: Status,
    parent: Option<NodeId>,
    children: Vec<NodeId>,
    links: Vec<Link>,
    agents: Vec<AgentRef>,
    history: ConversationId,
    created_at: Timestamp,
    updated_at: Timestamp,
}

enum Status {
    Draft,
    InProgress,
    Review,
    Complete,
    Archived,
}

struct Link {
    kind: LinkKind,  // Implements, DependsOn, RelatedTo
    target: NodeId,
}
```

## API (MCP Server)

```
spectree.get_node(id)
spectree.list_children(id)
spectree.create_node(parent, kind, title, content)
spectree.update_node(id, changes)
spectree.move_node(id, new_parent)
spectree.link_nodes(from, to, kind)
spectree.claim_ownership(node_id, agent_id)
spectree.propose_change(node_id, proposal)
spectree.get_conversation(node_id)
spectree.append_message(node_id, message)
```

## Status

**Design Phase** - Data model and MCP interface being defined.

## License

MIT
