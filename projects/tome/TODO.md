# Tome TODO

## Phase 10: Authentication (In Progress)
- [x] AUTH command implementation (password-based)
- [x] Server-side per-connection auth state (integrate with TomeServer)
- [x] Password authentication (via g_password global)
- [ ] Requirepass config via CLI flag (--password)
- [ ] Pluggable authentication backend interface
- [ ] JWT authentication with trusted issuer verification
- [ ] OIDC authentication support
- [ ] ACL system for command-level permissions

## Phase 11: Multi-Process Scaling (In Progress)
- [x] Master process with worker spawning (fork + SO_REUSEPORT)
- [x] Worker health monitoring and restart
- [x] Graceful shutdown with SIGTERM handling
- [x] Configurable worker count via CLI (`-w, --workers`)
- [ ] Fix: Worker initialization crashes after fork (likely io_uring + globals issue)
- [ ] Connection draining on worker restart

## Known Issues
- [ ] LLVM 20 crash in SelectionDAGISel when building async_tasks.ll (workaround: use -O1)
- [ ] io_uring returns -22 (EINVAL) on accept - may be sandbox restriction

## Phase 12: Shared Memory Store (Optional)
- [ ] Design lock-free or spinlock-based Store
- [ ] Implement shared memory allocation via mmap(MAP_SHARED)
- [ ] Atomic operations for counters and flags
- [ ] Memory-mapped hash table with CAS for updates
- [ ] Cross-process pub/sub via shared ring buffer

## Future
- [ ] Persistence (RDB snapshots, AOF)
- [ ] Transactions (MULTI/EXEC)
- [ ] Tree data structure
- [ ] Zeus IPC integration
- [ ] Cluster mode (sharding across machines)
- [ ] Lua scripting support

## LARB Compliance (GitHub Issue #1)
### Blocked - Requires Ecosystem Changes
- [ ] Replace `&&`/`||` with `and`/`or` keywords (compiler doesn't support yet)
- [ ] Module-level StrView constants (compiler only supports `const` primitives)
- [ ] Convert raw pointers to borrows (ritzlib still uses `*T`; wait for ecosystem migration)

### Documentation
- [ ] Add documentation comments to pub functions

### File Splitting (> 500 lines)
- [ ] Split `lib/tome.ritz` (3,495 lines) into modules
