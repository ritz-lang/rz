# Spectree DONE

## 2026-02-13 - Initial Scaffolding

### Phase 1: Foundation

**Exploration:**
- Reviewed Ritz language docs (LANGUAGE.md)
- Studied cryptosec patterns (flat lib/, test/ structure, ritz.toml config)
- Examined ritzunit for testing patterns (@test attribute, assertions)

**Project Setup:**
- Created `ritz.toml` with package metadata
- Added `ritz` submodule and `ritzlib` symlink
- Created `lib/`, `test/`, `src/`, `build/` directories
- Created `build.sh` with build/test/clean commands

**Core Types (lib/types.ritz):**
- `NodeKind`: NODE_ORG, NODE_SPEC, NODE_PLAN constants
- `NodeStatus`: Draft, InProgress, Review, Complete, Archived
- `LinkKind`: Implements, DependsOn, RelatedTo
- `Uuid`: 128-bit identifier (high/low u64 pair)
- `Link`: Relationship between nodes
- `AgentRef`: Agent assignment with role
- `Timestamp`: Unix nanos
- `Node`: Core tree node structure

**UUID Operations (lib/uuid.ritz):**
- `uuid_generate()`: V4 random UUID via /dev/urandom
- `uuid_format()`: Standard hex string (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
- `uuid_parse()`: Parse from hex string

**In-Memory Store (lib/store.ritz):**
- `Store`: Collection of NodeEntry
- Node CRUD: create, get, update_title, update_content, update_status
- Tree operations: move, delete, get_children
- Link operations: add_link, remove_link, get_links
- Agent operations: assign_agent, get_agents

**Tests:**
- `test/test_types.ritz`: NodeKind, Status, LinkKind, Uuid, Node tests
- `test/test_uuid.ritz`: Generation, formatting, parsing tests
- `test/test_store.ritz`: Full CRUD, link, agent tests

## 2026-02-13 - Fixed Store Tests

**Issue:** Store tests failing (17/45 failures) with `Unknown function: vec_len` and `Cannot take address of immutable binding: id`

**Root Causes:**
1. Generic vec functions (`vec_len`, `vec_push`, etc.) require explicit type parameters
2. Ritz `let` bindings are immutable - cannot take address of fields through immutable pointers

**Fixes Applied:**
- Added typed helper functions in store.ritz for each Vec type (entries, children, links, agents)
- Changed `let` to `var` for all bindings that later have addresses taken
- Renamed Node.id field to Node.uuid to avoid parser ambiguity with `&entry.node.id`
- Updated test file to use `var` for pointer bindings used with `&ptr.field`

**Results:** All 45 tests passing

## 2026-02-13 - Phase 2: MCP Interface

**lib/mcp.ritz:**
- MCP result codes: MCP_OK, MCP_ERR_NOT_FOUND, MCP_ERR_INVALID_ID, etc.
- McpServer struct wrapping Store
- Node operations: mcp_get_node, mcp_list_children, mcp_create_node, mcp_update_*, mcp_move_node, mcp_delete_node
- Link operations: mcp_link_nodes, mcp_unlink_nodes, mcp_get_links
- Agent operations: mcp_claim_ownership, mcp_release_ownership, mcp_get_agents_count, mcp_get_agent

**test/test_mcp.ritz:**
- 22 tests covering all MCP operations
- Server creation, node CRUD, hierarchy, links, agents

**Ritz Learnings:**
- Multi-line imports not supported (use full module import instead)
- Generic pointer types `*Vec<T>` cannot be used in cast expressions (`0 as *Vec<u8>` fails)
- Workaround: cast pointer to i64 for null comparison (`let ptr: i64 = p as i64; if ptr != 0`)

**Results:** All 67 tests passing (45 Phase 1 + 22 Phase 2)

## 2026-02-14 - Code Review: Apply larb Code Standards

**Issue:** GitHub Issue #1 - Code review identified violations of larb standards (LANGUAGE_REVIEW.md)

**Changes Applied:**

1. **Pointer → Reference Conversion (20+ locations)**
   - All `store_*` functions: `*Store` → `&mut Store`, `*Uuid` → `&Uuid`
   - All `mcp_*` functions: `*McpServer` → `&mut McpServer`
   - `uuid_eq`, `node_is_root`: `*T` → `&T` for read-only params
   - `uuid_format`: `*Uuid` → `&Uuid`
   - `uuid_parse`: `*u8` → `&Span<u8>`, `*Uuid` → `&mut Uuid`

2. **String Handling: `*u8` → `Span<u8>` (5 functions)**
   - `node_kind_name`: returns `Span<u8>` via `span_from_cstr()`
   - `status_name`: returns `Span<u8>`
   - `link_kind_name`: returns `Span<u8>`
   - `uuid_parse`: input changed to `&Span<u8>`
   - Updated test files to use `span_get<u8>()` for character checks

3. **Test Updates**
   - `test_types.ritz`: Import `ritzlib.span`, use `Span<u8>` for name tests
   - `test_uuid.ritz`: Use `span_from_cstr()` for parse tests

**Deferred Items (Blocked by Language):**
- `match` for constant dispatch: Would require converting i32 constants to enums
- `bool` return type: ritzlib uses i32 pattern (0/1) throughout
- `Option<&T>` returns: Would require deeper ritzlib integration

**Results:** All 67 tests passing

## 2026-02-14 - RERITZ Migration

**Issue:** Previous changes used `&mut T` syntax which was never part of the official Ritz language.
RERITZ (The Great Ritz Language Overhaul) introduced the actual reference syntax.

**RERITZ Syntax Changes Applied:**

1. **Attributes: `@test` → `[[test]]`**
   - All 67 test functions updated in 4 test files

2. **Reference Types: `&T` → `@T`, `&mut T` → `@&T`**
   - lib/types.ritz: `uuid_eq(a: @Uuid, b: @Uuid)`, `node_is_root(n: @Node)`
   - lib/uuid.ritz: `uuid_format(u: @Uuid, ...)`, `uuid_parse(s: @Span<u8>, out: @&Uuid)`

3. **Mutable Reference Params: Type-based `@&T` vs Param-based `:&`**
   - Key insight: Ritz uses `param: @&T` for TYPE-level mutable refs (like ritzlib)
   - The `:&` colon-ampersand syntax is for semantic parameter passing, not for internal function calls
   - lib/store.ritz: All store functions use `s: @&Store` for mutable store access
   - lib/mcp.ritz: All mcp functions use `server: @&McpServer`

4. **Address-of: `&x` → `@x`, `&mut x` → `@&x`**
   - All call sites updated: `store_get(@&s, @id)`, `vec_push<u8>(@&title, c)`
   - Immutable refs use `@`: `uuid_eq(@a, @b)`
   - Mutable refs use `@&`: `entries_push(@&s.entries, entry)`

5. **Ritz Submodule Updated**
   - Updated from c24ef29 to b078d54 (43 commits with RERITZ implementation)
   - Legacy mode removed, RERITZ is now the only mode

**Key Learnings:**
- RERITZ distinguishes TYPE syntax (`@T`, `@&T`) from PARAM syntax (`:`, `:&`, `:=`)
- For internal function calls, use TYPE syntax: `fn store_get(s: @&Store, id: @Uuid)`
- The PARAM syntax (`:&`) is for clean call-sites where borrowing is implicit
- ritzlib uses TYPE syntax exclusively (e.g., `vec_push<T>(v: @&Vec<T>, item: T)`)

**Results:** All 67 tests passing (15 types + 13 uuid + 17 store + 22 mcp)

## 2026-02-15 - Phase 3: Conversation History

**lib/types.ritz - New Types:**
- `Message`: Single conversation message with role, content, timestamp
- `Conversation`: Container for messages attached to a node
- `ConversationSummary`: Compressed summary for context windows
- `ROLE_USER`, `ROLE_ASSISTANT`, `ROLE_SYSTEM` constants
- Helper functions: `role_name()`, `message_new()`, `conversation_new()`

**lib/conversation.ritz - Conversation Storage:**
- `ConversationStore`: Root container for all conversations
- `ConversationEntry`: Internal storage (conversation + messages Vec)
- `MessageEntry`: Internal storage for individual messages
- CRUD operations: `conv_create`, `conv_get`, `conv_count_for_node`, `conv_get_for_node`
- Message operations: `conv_append_message`, `conv_message_count`, `conv_get_message`
- Typed Vec helpers prefixed with `conv_` to avoid linker conflicts with store.ritz

**lib/mcp.ritz - MCP Conversation Operations:**
- `mcp_create_conversation`: Create conversation for a node (validates node exists)
- `mcp_get_conversation`: Retrieve conversation by ID
- `mcp_conversation_count`: Count conversations for a node
- `mcp_get_conversation_for_node`: Get conversation by index
- `mcp_append_message`: Add message to conversation
- `mcp_message_count`: Count messages in conversation
- `mcp_get_message`: Get message by index
- `mcp_delete_conversation`: Delete a conversation
- `mcp_total_conversation_count`: Server-wide conversation count

**test/test_conversation.ritz - 15 Tests:**
- Store creation, conversation creation
- Multiple conversations per node, different nodes
- Conversation retrieval, message appending
- Message roles, deletion

**test/test_mcp.ritz - 9 New Tests:**
- MCP conversation create, get, append
- Invalid node/conversation handling
- Full conversation flow test

**Learnings:**
- Ritz linker requires unique function names across compilation units
- Vec helper functions must be uniquely named (prefixed with module name)
- Ownership requires saving values before move (e.g., save UUID before moving struct)

**Results:** All 91 tests passing (15 types + 13 uuid + 17 store + 31 mcp + 15 conversation)
