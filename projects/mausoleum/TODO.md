# Mausoleum TODO

## Current Status

✅ **RERITZ Migration Complete** (2026-02-14)
- Ritz submodule: 7d6885d (RERITZ complete, legacy mode removed)
- All 373 tests passing (546ms)
- Syntax: `[[test]]` attributes, `@x` address-of, `c"..."` for FFI strings

## Phase 2: Document Layer ✓ (Complete)

## Phase 3: Query Layer (In Progress)

### Phase 3.1: Query Builder ✓ (Complete)
- [x] Query builder API
  - [x] Filter expressions (eq, ne, gt, lt, gte, lte, is_null, not_null, contains, starts_with)
  - [x] Ordering (asc, desc, multi-field)
  - [x] Pagination (limit, offset)
  - [x] Query execution
  - [x] 52 tests

### Phase 3.2: Secondary Indexes ✓ (Complete)
- [x] Index structure (single-field, composite, unique)
- [x] Index operations (create, drop, lookup)
- [x] Index maintenance (insert, delete, update)
- [x] Index scanning (equality, range)
- [x] 30 tests

### Phase 3.3: SQL Parser (Optional)
- [ ] Lexer/tokenizer
- [ ] Parser (SELECT, INSERT, UPDATE, DELETE)
- [ ] Query planner
- [ ] Executor

## Phase 4: Server & API ✓ (Complete)

- [x] Network server
  - [x] TCP listener with epoll
  - [x] Binary protocol (M7SP - Mausoleum 7 Server Protocol)
  - [x] Connection handling with non-blocking I/O

- [x] Client library
  - [x] Connection management
  - [x] CRUD operations
  - [x] Transaction support

## Phase 5: Future Enhancements

### Protocol Extensions
- [ ] Query protocol messages (QUERY, QUERY_NEXT)
- [ ] Index protocol messages (INDEX_CREATE, INDEX_DROP)
- [ ] Prepared statements

### Server Improvements
- [ ] Connection pooling
- [ ] SSL/TLS support
- [ ] Async I/O with io_uring (ritzlib.uring)

### Performance Optimizations
- [ ] Secondary index for parent_id lookups in traversal
- [ ] Secondary index for link target lookups (backlinks)
- [ ] Index-assisted query execution (currently full scan + filter)

### Testing & Quality
- [ ] Add cleanup calls to tests for Valgrind cleanliness
- [ ] Integration tests with real server/client
- [ ] Benchmark suite

### RERITZ Migration (Pending)
- [ ] Convert c"..." to "...".as_cstr() when ritz implements the method
  - 236 c-string occurrences across 11 files
  - Blocked on ritz implementing StrView.as_cstr()

### Future
- [ ] SQL parser (deferred to ritzgen)
