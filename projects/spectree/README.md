# Spectree

Hierarchical specification and planning tree for AI-assisted software development.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Spectree manages a tree of well-defined specifications and plans for complex software projects. It provides the organizational structure for AI agents (such as Adele) to collaborate on planning, own segments of work, propose changes to specifications, and track progress across a project hierarchy.

The tree has three node types: Org nodes provide root organizational context, Spec nodes declare what IS or SHOULD BE (declarative truth), and Plan nodes describe what TO DO (imperative work items). Nodes can be linked to each other (a Plan implements a Spec, a Spec depends on another Spec), and each node has an attached conversation history for agent collaboration.

Spectree is served as an MCP (Model Context Protocol) server, enabling any MCP-compatible AI client to interact with the spec tree. It is built using Mausoleum for persistent storage and deployed via the Zeus/Valet stack.

## Features

- Three node types: Org (root), Spec (declarative), Plan (imperative)
- Tree structure with parent/child relationships
- Graph links between nodes (Implements, DependsOn, RelatedTo)
- Agent ownership - assign responsibility to specific agents
- Conversation history attached to each node
- Status tracking (Draft, InProgress, Review, Complete, Archived)
- MCP server interface for AI client integration
- Node splitting and merging as scope evolves
- Built on Mausoleum for full version history

## Installation

```bash
# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .

# Run the Spectree MCP server
./build/debug/spectree serve --port 9090
```

## Usage

```ritz
import spectree { Tree, Node, NodeKind }

# Create a spec hierarchy
let tree = Tree.open("project.m7m")

let org = tree.create(NodeKind.Org, "Ritz Language", null)
let spec = tree.create(NodeKind.Spec, "Type System", org.id)
let plan = tree.create(NodeKind.Plan, "Implement Generics", spec.id)

# Link plan to the spec it implements
tree.link(plan.id, spec.id, LinkKind.Implements)

# Claim ownership (agent responsibility)
tree.claim(plan.id, "adele-agent-1")

# Query the tree
let all_plans = tree.descendants(org.id).filter_kind(NodeKind.Plan)
let drafts = tree.query().kind(NodeKind.Spec).status(Status.Draft).exec()
```

```
# MCP API (for AI clients)
spectree.get_node(id)
spectree.list_children(id)
spectree.create_node(parent, kind, title, content)
spectree.update_node(id, changes)
spectree.claim_ownership(node_id, agent_id)
spectree.propose_change(node_id, proposal)
spectree.append_message(node_id, message)
```

## Tree Structure Example

```
Org: "Ritz Language"
  Spec: "Language Design"
    Spec: "Type System"
      Plan: "Implement Generics"   <- agent owns this
    Spec: "Async Model"
  Spec: "Standard Library"
    Plan: "Port HTTP Module"
  Plan: "Q1 2026 Roadmap"
    Plan: "Phase 1: Core Compiler"
    Plan: "Phase 2: Stdlib"
```

## Dependencies

- `ritzlib` - Standard library

## Status

**Alpha** - Data model, node types, and MCP interface are designed. Core tree operations and persistence via Mausoleum are being implemented. Agent collaboration features and MCP server are planned once the data layer stabilizes.

## License

MIT License - see LICENSE file
