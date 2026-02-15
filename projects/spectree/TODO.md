# Spectree TODO

## Phase 1: Foundation (Complete)

- [x] Explore Ritz codebase patterns
- [x] Design data model
- [x] Scaffold project structure
- [x] Implement core types (NodeKind, Status, Link, Uuid, Node)
- [x] Implement UUID generation and formatting
- [x] Implement in-memory store with CRUD
- [x] All 45 tests passing

## Phase 2: MCP Interface (Complete)

- [x] Define MCP server protocol types (result codes, McpServer)
- [x] Implement node operations (get, list_children, create, update, move, delete)
- [x] Implement link operations (link_nodes, unlink_nodes, get_links)
- [x] Implement agent operations (claim_ownership, release, get_agents)
- [x] All 67 tests passing (45 store + 22 MCP)
- [x] Code review: Apply larb code standards (Issue #1)
  - [x] Convert pointer params to references (&T / &mut T)
  - [x] Update string handling (*u8 → Span<u8>)
- [x] RERITZ migration: Update to new Ritz syntax
  - [x] `@test` → `[[test]]` attributes
  - [x] `&T` → `@T`, `&mut T` → `@&T` reference types
  - [x] `&x` → `@x`, `&mut x` → `@&x` address-of operators

## Phase 3: Conversation History (Complete)

- [x] Design conversation/message types (Message, Conversation, ConversationSummary)
- [x] Implement message storage per node (ConversationStore, ConversationEntry)
- [x] Implement get_conversation and append_message
- [x] Add MCP conversation operations (create, get, list, append_message, get_messages, delete)
- [x] All 91 tests passing (45 store + 22 MCP + 15 conversation + 9 MCP conversation)

## Phase 4: Integration (Spire App Architecture)

**Architecture Context:**
- **Zeus**: Process runner with shared memory ring buffer IPC
- **Valet**: HTTP server routing to Zeus workers
- **Spire**: MVC-like framework running on Zeus (not yet implemented)
- **Spectree**: Should be a Spire app providing both MCP server + visualization API

**Tasks:**
- [ ] Design Spire app structure for Spectree
- [ ] Implement Zeus worker integration (request/response via ring buffer)
- [ ] HTTP API layer for visualization (routes via Valet)
- [ ] MCP protocol transport (JSON-RPC over HTTP)
- [ ] End-to-end testing with Docker Compose (like Nexus)

## Future

- [ ] Persistent storage via mausoleum
- [ ] Real-time updates via WebSocket
- [ ] Multi-agent collaboration features
- [ ] Spec change proposal workflow

## Deferred (Blocked by Language Features)

- [ ] Use `match` instead of `if/else if` for constant dispatch (requires i32→enum migration)
- [ ] Use `bool` return type for predicate functions (ritzlib uses i32 pattern)
- [ ] Return `Option<&T>` instead of `*T` for nullable returns (requires deeper ritzlib patterns)
