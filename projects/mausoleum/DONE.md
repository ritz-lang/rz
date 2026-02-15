# Mausoleum DONE

## Phase 1: Core Storage Engine ✓

### Completed 2024-02-13

- [x] **Project structure**
  - Created ritz.toml manifest
  - Added ritz, ritzunit, cryptosec submodules
  - Created src/, lib/, test/ directories
  - Set up build.sh and build_tests.sh

- [x] **Core types (lib/m7m_types.ritz)**
  - PageId: Page identifier with file/page components
  - Result_i64: Error handling result type
  - Span: Byte buffer view (ptr + len)
  - Timestamp: Nanosecond precision timestamps
  - LSN: Log Sequence Numbers for WAL
  - TxnId: Transaction identifiers
  - Error codes (ERR_OK, ERR_IO, etc.)

- [x] **Page structure (lib/page.ritz)**
  - Page: 4KB page with 64-byte header + 4032-byte data area
  - PageHeader: magic, checksum, page_id, lsn, flags, etc.
  - Page types: META, BTREE, HEAP, OVERFLOW, WAL
  - CRC32 checksums for data integrity
  - Page validation and verification
  - Tests: 27 tests covering initialization, types, dirty flags, checksums

- [x] **Buffer Pool (lib/buffer_pool.ritz)**
  - BufferPool: Fixed-size page cache with LRU eviction
  - Frame: Individual page slot with pin counting
  - Hash table for O(1) page lookup
  - LRU list for eviction candidates
  - Page allocation, fetching, pinning/unpinning
  - Dirty page tracking
  - Cache statistics (hits, misses, evictions)
  - Tests: 15 tests covering allocation, eviction, pinning

- [x] **Write-Ahead Log (lib/wal.ritz)**
  - WalWriter: Buffered WAL record writer
  - WalReader: WAL record reader for recovery
  - Record types: BEGIN, COMMIT, ABORT, INSERT, PAGE_WRITE, CHECKPOINT
  - CRC16 checksums per record
  - LSN tracking and generation
  - Tests: 13 tests covering write/read operations

- [x] **B-tree Index (lib/btree.ritz)**
  - B+ tree with variable-length keys and values
  - Leaf nodes: store key-value pairs, linked for range scans
  - Internal nodes: store keys for navigation
  - Key-value operations: get, put, delete
  - Node splitting (leaf and internal) with proper separator promotion
  - New root creation when root splits
  - Multi-level tree support (height 3+)
  - Range scan iterator (btree_scan, btree_iter_*)
  - Tests: 36 tests covering CRUD, splits, errors, edge cases

- [x] **Recovery Manager (lib/recovery.ritz)**
  - RecoveryManager: Coordinates crash recovery using WAL
  - Analysis pass: Scans WAL, builds active transaction table
  - Redo pass: Replays committed transaction changes
  - Undo pass: Rolls back uncommitted transactions
  - Checkpoint support: Creates known-good recovery points
  - RecoveryStats: Tracks records scanned, txns committed/aborted, pages recovered
  - Tests: 15 tests covering creation, empty WAL, committed/aborted/uncommitted txns,
    checkpoints, multiple transactions, page recovery, corruption handling, null checks

- [x] **Transaction Manager (lib/txn.ritz)**
  - TxnManager: Coordinates MVCC transactions
  - Txn: Transaction state with ID, snapshot timestamp, LSN tracking
  - Transaction lifecycle: begin, commit, abort
  - Snapshot isolation: Each transaction sees data committed before its start
  - Visibility rules: Own writes visible, committed before snapshot visible
  - Delete visibility: Handles deleted rows correctly
  - Active transaction tracking: Maintains list of in-flight transactions
  - Tests: 21 tests covering lifecycle, multiple txns, visibility, errors

### Test Summary
- **208 tests passing** (328ms total)
- Types: 23 tests
- Page: 27 tests
- Buffer Pool: 15 tests
- WAL: 13 tests
- B-tree: 36 tests
- Recovery: 15 tests
- Transaction: 21 tests
- Document: 29 tests
- Collection: 18 tests
- Traversal: 11 tests

## Phase 2.1: Document Structure ✓

### Completed 2024-02-13

- [x] **DocumentId** (lib/document.ritz)
  - Collection ID + sequence number packed into i64
  - Valid/invalid checks, equality comparison

- [x] **Field types** (lib/document.ritz)
  - FIELD_NULL: Null value
  - FIELD_INT: 64-bit integers
  - FIELD_BOOL: Boolean (0/1)
  - FIELD_FLOAT: Fixed-point (value * 1000000, Ritz lacks float literals)
  - FIELD_STRING: String pointer + length
  - FIELD_BYTES: Binary data pointer + length
  - FIELD_DOCREF: Reference to another document

- [x] **Document structure** (lib/document.ritz)
  - Flexible schema: up to 64 named key-value fields
  - Parent/child relationships via parent_id
  - Graph edges: up to 32 labeled links to other documents
  - Version tracking (auto-increment on changes)
  - Timestamps: created_at, updated_at (auto-updated)

- [x] **Document operations**
  - Field CRUD: set, get, remove, has
  - Parent: set, get, clear, has
  - Links: add, has, remove, count by label
  - Version: increment, touch

- [x] **Tests**: 29 tests covering all operations

## Phase 2.2: Collection Storage ✓

### Completed 2024-02-13

- [x] **Collection** (lib/collection.ritz)
  - Collection struct: pool, B-tree, collection_id, next_sequence, doc_count
  - Initialization with buffer pool

- [x] **Document serialization**
  - Binary format with version tag
  - Full document state: id, parent_id, version, timestamps
  - Field serialization by type (null, int, bool, fixed, string, bytes, docref)
  - Link serialization (label + target)

- [x] **CRUD operations**
  - `collection_insert`: Serialize and store with auto-assigned ID
  - `collection_get`: Retrieve and deserialize by ID
  - `collection_update`: Overwrite existing document
  - `collection_delete`: Remove from B-tree
  - `collection_count`: Track document count

- [x] **Tests**: 18 tests covering creation, insert, get, update, delete, count

## Phase 2.3: Tree/Graph Traversal ✓

### Completed 2024-02-13

- [x] **Tree traversal** (lib/traversal.ritz)
  - `get_children`: Find all documents whose parent matches a given ID
  - `get_ancestors`: Follow parent chain to root (immediate parent first)
  - `get_descendants`: BFS traversal to find all children/grandchildren

- [x] **Graph traversal** (lib/traversal.ritz)
  - `get_linked`: Get documents linked FROM a source by label
  - `get_backlinks`: Get documents linking TO a target by label (reverse lookup)

- [x] **Tests**: 11 tests covering tree and graph traversal operations

## Phase 3.1: Query Builder ✓

### Completed 2024-02-14

- [x] **Query structure** (lib/query.ritz)
  - Query struct: filters, orders, limit, offset
  - Filter struct: field name, operator, value
  - OrderClause struct: field name, direction
  - QueryResult struct: dynamic array of matching document IDs

- [x] **Filter expressions**
  - Comparison: eq, ne, gt, lt, gte, lte
  - Null checks: is_null, not_null
  - String ops: contains, starts_with
  - Relationship: has_parent, has_link
  - Convenience: query_eq_int, query_gt_int, etc.

- [x] **Ordering**
  - Ascending/descending by field name
  - Multi-field ordering support (up to 4 clauses)
  - Stable sort (ties broken by document ID)

- [x] **Pagination**
  - Limit: restrict result count
  - Offset: skip first N results
  - Combined limit+offset for paging

- [x] **Query execution**
  - Full collection scan with filter matching
  - Field comparison with type-aware logic
  - String substring/prefix matching
  - In-memory sorting with insertion sort
  - Result pagination after filtering

- [x] **Convenience functions**
  - `query_first`: Execute and return first match
  - `query_count`: Count matching documents (ignores pagination)

- [x] **Tests**: 52 tests covering:
  - Query creation and initialization
  - All filter operators (eq, ne, gt, lt, gte, lte, is_null, not_null, contains, starts_with)
  - Multiple filters (AND logic)
  - Ordering (asc, desc)
  - Pagination (limit, offset, combined)
  - Query execution with various filters
  - Edge cases (null query, null collection, missing fields)

### Test Summary
- **260 tests passing** (394ms total)
- Types: 23 tests
- Page: 27 tests
- Buffer Pool: 15 tests
- WAL: 13 tests
- B-tree: 36 tests
- Recovery: 15 tests
- Transaction: 21 tests
- Document: 29 tests
- Collection: 18 tests
- Traversal: 11 tests
- Query: 52 tests

## Phase 3.2: Secondary Indexes ✓

### Completed 2024-02-14

- [x] **Index structure** (lib/index.ritz)
  - Index struct: id, name, fields, flags, B-tree, entry count
  - IndexField: field name, ascending/descending
  - IndexManager: manages indexes for a collection
  - Support for single-field and composite indexes
  - Unique index enforcement

- [x] **Index operations**
  - `index_create`: Create single-field index
  - `index_create_composite`: Create multi-field index
  - `index_drop`: Remove index by name
  - `index_get`: Find index by name
  - `index_find_for_field`: Find index that covers a field

- [x] **Index key serialization**
  - Type-tagged key format for correct sort ordering
  - Sign-bit flip for signed integers (correct lexicographic order)
  - Big-endian encoding for proper byte comparison
  - Support for all field types (null, int, bool, float, string, bytes, docref)

- [x] **Index maintenance**
  - `index_insert_doc`: Add document to all indexes
  - `index_delete_doc`: Remove document from all indexes
  - `index_update_doc`: Update indexes when document changes
  - `index_build`: Build index from existing documents
  - Unique constraint checking on insert

- [x] **Index scanning**
  - `index_scan_eq`: Scan for equality match
  - `index_scan_range`: Scan value range (for >, <, >=, <= queries)
  - `index_iter_doc_id`: Extract document ID from index entry

- [x] **Query integration**
  - Helper functions to check if filter can use index
  - Filter field name and value accessors

- [x] **Tests**: 30 tests covering:
  - Index manager creation
  - Index creation (single, unique, multiple, duplicate detection)
  - Index deletion
  - Index lookup
  - Index building from existing data
  - Unique constraint violations
  - Index maintenance (insert, delete, update)
  - Index scanning
  - Edge cases and null handling

### Test Summary
- **290 tests passing** (420ms total)
- Types: 23 tests
- Page: 27 tests
- Buffer Pool: 15 tests
- WAL: 13 tests
- B-tree: 36 tests
- Recovery: 15 tests
- Transaction: 21 tests
- Document: 29 tests
- Collection: 18 tests
- Traversal: 11 tests
- Query: 52 tests
- Index: 30 tests

## Phase 4: Server & API ✓

### Completed 2024-02-14

- [x] **Wire Protocol (lib/protocol.ritz)**
  - M7SP binary protocol (Mausoleum 7 Server Protocol)
  - 16-byte message header: magic, length, version, type, flags, request_id
  - Request types: PING, CONNECT, DISCONNECT, INSERT, GET, UPDATE, DELETE
  - Transaction: TXN_BEGIN, TXN_COMMIT, TXN_ABORT
  - Query: QUERY, QUERY_NEXT (future)
  - Index: INDEX_CREATE, INDEX_DROP (future)
  - Response types: 0x80 | request_type
  - Error handling with typed error codes
  - MessageBuffer for building messages
  - MessageReader for parsing messages
  - Big-endian encoding for network byte order
  - Tests: 51 tests covering serialization, roundtrips, edge cases

- [x] **TCP Server (lib/server.ritz)**
  - Non-blocking TCP server with epoll
  - Connection structure with recv/send buffers
  - Per-connection state: reading, processing, writing, closed
  - Session management with unique session IDs
  - Message framing and parsing
  - Request dispatching by message type
  - CRUD operation handlers (insert, get, delete)
  - Transaction handlers (begin, commit, abort)
  - LRU eviction for connection pool
  - Tests: 8 tests covering server creation, connections, constants

- [x] **Client Library (lib/client.ritz)**
  - Synchronous TCP client
  - Connection management (connect, disconnect)
  - Session tracking
  - CRUD operations (insert, get, delete)
  - Transaction support (begin, commit, abort)
  - Error handling and reconnection
  - Tests: 24 tests covering client operations, null handling

### Test Summary
- **373 tests passing** (525ms total)
- Types: 23 tests
- Page: 27 tests
- Buffer Pool: 15 tests
- WAL: 13 tests
- B-tree: 36 tests
- Recovery: 15 tests
- Transaction: 21 tests
- Document: 29 tests
- Collection: 18 tests
- Traversal: 11 tests
- Query: 52 tests
- Index: 30 tests
- Protocol: 51 tests
- Server: 8 tests
- Client: 24 tests

## Code Review & Quality Assurance ✓

### Completed 2024-02-14

#### Ritz Submodule Rebase
- Rebased ritz submodule to latest main (36 commits ahead)
- New features available: examples 33-40, float literals, async tasks

#### Valgrind Memory Analysis
- Ran full test suite under Valgrind with `--no-fork` flag
- Found and fixed memory leaks in library code

#### Issues Found & Fixed

1. **traversal.ritz - Missing iterator cleanup**
   - `get_children()` was not calling `btree_iter_destroy(iter_ptr)`
   - `get_backlinks()` was not calling `btree_iter_destroy(iter_ptr)`
   - Fixed: Added `btree_iter_destroy()` calls before return

2. **collection.ritz - Missing destroy function**
   - Added `collection_destroy()` to free the internal B-tree
   - Tests should call this before `buffer_pool_destroy()` for Valgrind cleanliness

#### Remaining Valgrind Notes
- Tests don't call cleanup functions before process exit (acceptable for unit tests)
- The "possibly lost" block from ritzunit's `discover_tests` is expected (ELF symbol table allocation)
- Zero definite leaks in library code after fixes

#### Code Quality Assessment

**Ergonomics (Good)**
- Clean separation of concerns across modules
- Consistent API patterns (init/destroy, get/put/delete)
- Builder pattern for queries (fluent interface)
- Helper functions for common operations (query_eq_int, etc.)

**Security Considerations**
- Protocol has max message size limit (16MB) - prevents memory exhaustion
- Buffer bounds checking in serialization/deserialization
- Null pointer checks on all public functions
- CRC32 checksums for page integrity
- CRC16 checksums for WAL record integrity

**Performance Notes**
- B-tree: O(log n) for point queries, O(n) for full scans
- Buffer pool: O(1) page lookup via hash table
- Secondary indexes: Proper sign-bit flip for signed integer sort order
- Full scan in traversal functions - marked with TODO for secondary index optimization

**Areas for Future Improvement**
- Add secondary indexes for parent_id lookups (traversal.ritz)
- Add secondary indexes for link target lookups (traversal.ritz)
- Consider async I/O using ritzlib.uring for server
- Index-assisted query execution (currently does full scan then filters)

## RERITZ Migration ✓

### Completed 2026-02-14

- [x] **Ritz submodule updated to RERITZ**
  - Updated from commit 34bd36f to f3b0490 (14 commits)
  - Includes RERITZ Phase 0-2: lexer tokens, parser support, emitter support
  - New features: `[[test]]` attributes, inline assembly, `[[packed]]`/`[[naked]]`

- [x] **Test attribute migration**
  - Converted all 373 `@test` annotations to `[[test]]` syntax
  - Files updated: 15 test files in test/

- [x] **Verification**
  - All 373 tests passing (530ms)
  - Build system working correctly with new syntax

### Not Yet Migrated (Awaiting ritz implementation)

- [ ] **C-string literals** - `c"..."` → `"...".as_cstr()`
  - The `.as_cstr()` method for string literals is P1 priority in RERITZ
  - Currently still using `c"..."` syntax (236 occurrences)
  - Will migrate when ritz implements the method

## RERITZ Complete Migration ✓

### Completed 2026-02-14

RERITZ is now fully implemented in the ritz compiler, and mausoleum has been updated to use the new syntax.

#### Submodule Updates
- [x] **ritz** - Updated to commit 7d6885d (RERITZ complete, legacy mode removed)
- [x] **cryptosec/ritz** - Updated to commit 7d6885d
- [x] **ritzunit** - Updated to commit d542b1b
- [x] **ritzunit/ritz** - Updated to commit 7d6885d

#### Syntax Changes Applied

| Change | Files Affected | Count |
|--------|----------------|-------|
| `[[test]]` attributes | test/*.ritz | 373 tests |
| `&x` → `@x` (address-of) | lib/*.ritz, test/*.ritz | 1000+ occurrences |
| `c"..."` for *u8 params | test/*.ritz | 100+ occurrences |

#### Key Changes

1. **Address-of operator**: `&` → `@`
   - All address-of operations in lib/ and test/ converted
   - Example: `&doc` → `@doc`

2. **Test attributes**: `@test` → `[[test]]`
   - All 373 test functions updated

3. **String literals**: `"hello"` now returns `StrView`, not `*u8`
   - Functions expecting `*u8` (like `doc_set_field`) now require `c"hello"`
   - Regular `"hello"` is zero-copy `StrView` for new APIs

4. **Runtime stub for LLVM optimization**
   - Added `runtime/bcmp.s` - LLVM may replace memcmp loops with bcmp at -O2
   - Build scripts updated to include bcmp stub

#### Build Changes

- `build.sh` - Added bcmp.o to link, added `-fno-builtin` flag
- `build_tests.sh` - Added bcmp.o assembly compilation and linking

#### Verification

- **All 373 tests passing** (546ms)
- Release build (-O2) works with bcmp stub
- Debug build (-O0) works without bcmp stub
