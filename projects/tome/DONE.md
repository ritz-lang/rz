# Tome DONE

## Phase 0: Project Setup
- [x] Create project structure (lib/, test/, build/)
- [x] Write README with design spec
- [x] Set up ritz.toml configuration
- [x] Add ritz and ritzunit submodules
- [x] Create build_tests.sh script

## Phase 1: Core Key-Value Store
- [x] Implement `Entry` type (key + value + metadata)
- [x] Implement `Store` hash table (open addressing, linear probing)
- [x] Basic operations: `get`, `set`, `del`, `exists`
- [x] Write tests for basic KV operations (9 tests passing)

## Phase 2: TTL & Expiration
- [x] Add time utilities (`time_now_secs` using `gettimeofday`)
- [x] Implement `setex` - set with TTL in seconds
- [x] Implement `expire` - set TTL on existing key
- [x] Implement `ttl` - get remaining TTL (-2 missing, -1 no expire, ≥0 secs)
- [x] Implement `persist` - remove TTL from key
- [x] Lazy expiration in `store_get` (expired keys deleted on access)
- [x] Lazy expiration check in `store_exists`
- [x] Active expiration `store_expire_sweep` (scan and delete expired)
- [x] Tests for TTL behavior (9 new tests, 18 total passing)

## Phase 3: List Type
- [x] Add `ListNode` and `List` structs (doubly-linked list)
- [x] Add `value_ptr` field to Entry for non-string types
- [x] Implement `list_new`, `list_drop` for list lifecycle
- [x] Implement `list_lpush`, `list_rpush` - push to head/tail
- [x] Implement `list_lpop`, `list_rpop` - pop from head/tail
- [x] Implement `list_len`, `list_index` (with negative index support)
- [x] Implement store-level `store_lpush`, `store_rpush`, `store_lpop`, `store_rpop`
- [x] Implement `store_llen`, `store_lindex`, `store_lrange`
- [x] Type checking: list ops return -1 on wrong type
- [x] Update `store_del` and `Drop for Store` to handle lists
- [x] Tests for list operations (8 new tests, 26 total passing)

## Phase 4: Set Type
- [x] Add `SetEntry` and `Set` structs (hash-based set)
- [x] Implement `set_new`, `set_drop`, `set_add`, `set_remove`, `set_contains`
- [x] Implement store-level `store_sadd`, `store_srem`, `store_sismember`, `store_scard`
- [x] Implement `store_smembers` - get all members as borrowed pointers
- [x] Implement `store_sunion` - returns new Set with union
- [x] Implement `store_sinter` - returns new Set with intersection
- [x] Implement `store_sdiff` - returns new Set with difference
- [x] Type checking: set ops return -1 on wrong type
- [x] Update `store_del` and `Drop for Store` to handle sets
- [x] Tests for set operations (9 new tests, 35 total passing)

## Phase 5: Sorted Set Type
- [x] Add `ZSetNode`, `ZSetHashEntry`, and `ZSet` structs (skip list + hash table)
- [x] Implement skip list with random level generation (LCG-based PRNG)
- [x] Implement `zset_new`, `zset_drop` for lifecycle management
- [x] Implement `zset_add` with O(log n) skip list insertion + hash table
- [x] Implement `zset_remove` with O(log n) skip list deletion
- [x] Implement `zset_score` for O(1) score lookup via hash table
- [x] Implement `zset_rank`, `zset_revrank` for rank queries
- [x] Implement `zset_range`, `zset_revrange` for range by rank
- [x] Implement store-level `store_zadd`, `store_zrem`, `store_zscore`
- [x] Implement `store_zrank`, `store_zrevrank`, `store_zcard`
- [x] Implement `store_zrange`, `store_zrevrange`
- [x] Type checking: zset ops return -1 or -2 on wrong type
- [x] Update `store_del` and `Drop for Store` to handle zsets
- [x] Lexicographic ordering for members with equal scores
- [x] Tests for sorted set operations (9 new tests, 44 total passing)
- Note: Using i64 scores instead of f64 (Ritz doesn't support float literals yet)

## Phase 6: Hash Type
- [x] Add `HashEntry` and `Hash` structs (hash table for field→value)
- [x] Implement `hash_new`, `hash_drop`, `hash_resize`
- [x] Implement `hash_set`, `hash_get`, `hash_del`, `hash_exists`, `hash_len`
- [x] Implement `hash_keys`, `hash_vals`, `hash_getall`
- [x] Implement store-level `store_hset`, `store_hget`, `store_hdel`, `store_hexists`
- [x] Implement `store_hlen`, `store_hkeys`, `store_hvals`, `store_hgetall`
- [x] Type checking: hash ops return -1 on wrong type
- [x] Update `store_del` and `Drop for Store` to handle hashes
- [x] Tests for hash operations (8 new tests, 52 total passing)

## Phase 7: Pub/Sub
- [x] Add `Subscriber`, `ChannelEntry`, `PatternEntry`, `PubSub` structs
- [x] Implement `pubsub_new`, `pubsub_drop` for lifecycle management
- [x] Implement channel hash table with resize support
- [x] Implement `pubsub_subscribe`, `pubsub_unsubscribe` for exact channel subscriptions
- [x] Implement `pubsub_psubscribe`, `pubsub_punsubscribe` for pattern subscriptions
- [x] Implement `glob_match` for glob-style pattern matching (`*` and `?`)
- [x] Implement `pubsub_publish` with callback invocation and auto-unsubscribe
- [x] Implement `pubsub_numsub`, `pubsub_numpat`, `pubsub_channels` query functions
- [x] Callback-based model: `fn(channel, message, context) -> i32`
- [x] Tests for pub/sub operations (9 new tests, 61 total passing)

## Phase 8: Memory Management
- [x] Add `last_access` field to Entry for LRU tracking
- [x] Add `used_memory`, `maxmemory`, `eviction_policy`, `rng_state` to Store
- [x] Implement memory calculation: `string_memory`, `entry_value_memory`, `entry_memory`
- [x] Track memory on set/get/del operations
- [x] Track memory when creating complex types (list, set, hash)
- [x] Implement eviction policies: `EVICT_NONE`, `EVICT_LRU`, `EVICT_RANDOM`
- [x] Implement volatile eviction: `EVICT_VOLATILE_LRU`, `EVICT_VOLATILE_RANDOM`, `EVICT_VOLATILE_TTL`
- [x] Implement `store_set_maxmemory`, `store_set_eviction_policy`
- [x] Implement `store_memory_usage`, `store_get_maxmemory`
- [x] Implement sampling-based LRU (sample 5 keys, evict oldest)
- [x] Implement `store_evict_if_needed` called after set operations
- [x] Tests for memory tracking and eviction (7 new tests, 68 total passing)

## Phase 9: Server Mode (Network Protocol)
- [x] Implement RESP (Redis Serialization Protocol) parser (`lib/resp.ritz`)
- [x] Implement RESP encoder for responses (simple strings, errors, integers, bulk strings, arrays)
- [x] Implement command dispatcher (`lib/commands.ritz`)
  - Server commands: PING, ECHO, COMMAND, INFO, DBSIZE, FLUSHDB
  - String commands: GET, SET, SETEX, DEL, EXISTS, TTL, EXPIRE, PERSIST
  - List commands: LPUSH, RPUSH, LPOP, RPOP, LLEN, LINDEX, LRANGE
  - Set commands: SADD, SREM, SISMEMBER, SCARD, SMEMBERS
  - Hash commands: HSET, HGET, HDEL, HEXISTS, HLEN, HKEYS, HVALS, HGETALL
- [x] Integrate with TaskServer from ritzlib/async_tasks (`lib/server.ritz`)
- [x] Basic single-process server with io_uring async I/O
- [x] `tome-server` binary with CLI args (`bin/tome_server.ritz`)
  - `-p, --port PORT` option
  - `-h, --help` option
- [x] Tests for protocol parsing (20 new tests, 101 total passing)
  - Parser tests: array, inline, incomplete, empty buffer
  - Encoder tests: simple strings, errors, integers, bulk strings, arrays
  - Argument helper tests: case-insensitive comparison, integer parsing
- [x] Tests for command dispatcher (14 command tests)
- [x] Add `store_clear` function for FLUSHDB
- Note: io_uring requires native Linux (not WSL2) for full functionality

## Phase 9b: CLI Client
- [x] `tome-cli` binary for interactive use
- [x] RESP client implementation (`lib/client.ritz`)
  - `TomeClient` struct with socket, connection status, read buffer
  - `client_connect`, `client_disconnect` for connection management
  - `client_send_cmd0/1/2/3` for sending commands with 0-3 arguments
  - `client_recv`, `client_print_response` for formatted response output
- [x] REPL with readline-style input
- [x] Tokenizer supporting quoted strings and whitespace
- [x] Host/port CLI arguments (-h/--host, -p/--port)
- [x] Human-readable response formatting (strings, integers, errors, arrays, nil)
- [x] Pipe mode for scripting (echo "SET foo bar" | tome-cli)

## Phase 11: Multi-Process Scaling (Partial)
- [x] Master process architecture (`lib/master.ritz`)
  - `MasterServer` struct tracking worker processes
  - `master_init` creates shared listen socket with SO_REUSEPORT
  - `master_spawn_workers` forks N worker processes
- [x] Worker spawning via fork()
  - Workers inherit listen socket
  - Each worker intended to have own Store (partitioned data)
- [x] Worker health monitoring (`master_check_workers`)
  - Non-blocking waitpid with WNOHANG
  - Automatic restart of crashed workers
  - Restart counter tracking
- [x] Graceful shutdown (`master_shutdown`)
  - SIGTERM to all workers
  - Wait with timeout, force SIGKILL if needed
- [x] CLI support: `-w, --workers N` flag
- [!] Known Issue: Worker initialization crashes after fork
  - Basic fork + prints works
  - Crash occurs when calling `tome_server_init_with_fd`
  - Likely related to io_uring globals or memory allocator state
  - Needs investigation on native Linux (not WSL2)

## Phase RERITZ: Language Syntax Migration
- [x] Updated ritz submodule to RERITZ-enabled version (7d6885d)
- [x] Updated ritzunit submodule to RERITZ-enabled version (d542b1b)
- [x] Converted all lib/*.ritz files to RERITZ syntax
  - `&x` → `@x` (address-of operator)
  - `&mut T` → `@&T` (mutable reference type)
  - `string_from(cstr)` → `string_from_cstr(cstr)` (API change)
  - String literals passed to *u8 params → c"..." (C-string literals)
- [x] Converted test/*.ritz files
- [x] Converted bin/*.ritz files
- [x] Renamed `glob_match` → `tome_glob_match` to avoid conflict with ritzunit
- [x] All 101 tests passing with new RERITZ syntax

## Phase API: StrView Refactor (Tech Debt)
- [x] Refactored public Store API to use `*StrView` for keys and values
- [x] Added `hash_strview` and `string_eq_strview` helper functions
- [x] Added `hash_cstr` function for internal hash table operations
- [x] Created `_cstr` convenience wrappers for backward compatibility
  - `store_set_cstr`, `store_get_cstr`, `store_del_cstr`, `store_exists_cstr`
  - `store_setex_cstr`, `store_expire_cstr`, `store_ttl_cstr`, `store_persist_cstr`
  - List ops: `store_lpush_cstr`, `store_rpush_cstr`, `store_lindex_cstr`
  - Set ops: `store_sadd_cstr`, `store_srem_cstr`, `store_sismember_cstr`
  - ZSet ops: `store_zadd_cstr`, `store_zrem_cstr`, `store_zscore_cstr`, etc.
  - Hash ops: `store_hset_cstr`, `store_hget_cstr`, `store_hdel_cstr`, etc.
- [x] Updated Store impl methods to use `_cstr` wrappers
- [x] Updated `store_grow` to properly convert keys during rehashing
- [x] Fixed type mismatches in internal functions:
  - `hash_set`: Changed `string_from_strview` to `string_from_cstr`
  - `zset_create_node`: Changed `string_from_strview` to `string_from_cstr`
  - `zset_hash_set`: Changed `string_from_strview` to `string_from_cstr`
- [x] Updated commands.ritz to use StrView API with `strview_from_cstr`
- [x] Updated test files to use `_cstr` wrapper functions
- [x] All 101 tests passing after refactor

## LARB Compliance: StrView Migration (Tech Debt)
- [x] Created GitHub Issue #1 with comprehensive LARB code review findings
- [x] Added `resp_write_simple_sv()` function for StrView-based simple string responses
- [x] Added `resp_write_error_sv()` function for StrView-based error responses
- [x] Added `resp_arg_eq_ci_sv()` for case-insensitive StrView comparison
- [x] Converted all error messages in commands.ritz from c"" to StrView literals
- [x] Converted command name lookups in dispatcher to use StrView-based comparison
- [x] Converted `tome_cli.ritz` from c"" to StrView for all print statements
- [x] Converted `server.ritz` error message from c"" to StrView
- [x] All 101 tests passing with StrView-based code
- [x] Removed obsolete API Improvements section from TODO.md (items completed or blocked)
- [x] Removed `[[test]]` item (optional - ritzunit discovers tests by `test_` prefix)

### Remaining C-String Usage (Correct Patterns)
- `strcmp()` calls require `*u8` (FFI function) - appropriate
- `_cstr` wrapper functions used in tests - intentional backward compatibility
- CLI argument parsing with `*u8` argv - required for main() signature

### Blocked Items (documented in GitHub Issue #1)
- Symbol operators (`&&`/`||` → `and`/`or`): Compiler doesn't support keyword operators yet
- Module-level StrView constants: Only `const` primitive types supported at module level

## Phase 10a: AUTH Command (Partial)
- [x] Added `password` and `is_authenticated` fields to `CommandContext`
- [x] Added `cmd_ctx_init_auth()` for creating auth-aware contexts
- [x] Implemented `AUTH password` command handler
- [x] Implemented `require_auth()` check in command dispatcher
- [x] AUTH and PING commands allowed without authentication (like Redis)
- [x] All other commands require authentication when password is set
- [x] Added 5 new tests for AUTH functionality (106 total tests passing)
- Note: Server-side per-connection auth state tracking still needed for production use
