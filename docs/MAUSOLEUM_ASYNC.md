# Mausoleum async serve loop — design

## Problem

Today `serve_loop_plain` in `projects/mausoleum/src/main.ritz` is **serial,
not async**: one client at a time, blocking on `sys_read`.  A single
misbehaving connection (or even a slow one) takes the entire database
offline for everyone else.

Concretely:

```ritz
loop:
    poll(listen_fd, 1s)              # only listening socket
    if listen_fd has POLLIN:
        client_fd = accept()
        handle_plain_session(...)    # ← blocks until client disconnects
        close(client_fd)
```

`handle_plain_session` is itself a `loop { sys_read(fd, buf, 4096); ... }`.
The listening socket isn't polled again until the current session ends.

This is the same bug that surfaced as nexus-orphans hijacking the
mausoleum slot during my SCAN-impl testing.

## Goal

Match valet's architecture: io_uring event loop, per-connection state
machine, no client can stall any other.

## Architecture

Reuse `ritzlib.async_tasks.TaskServer` — the same runtime valet uses.
That gives us:

- Multishot `accept` SQE for new connections (kernel ≥ 5.19)
- Per-connection `Task` slot with `read_buf` / `write_buf` / `handler_state`
- io_uring CQE → handler dispatch with full state-machine support
- Idle timeout, max-connection cap, graceful shutdown all already wired

### Per-connection state

Each `Task` slot gets one paired `M7SPSession` in a side table indexed by
task index (because `task.user_data` is canonically the `*TaskPool` for
the lib's internal helpers and we shouldn't repurpose it).

```ritz
struct M7SPSession
    active_txn: i64           # -1 = none, else transaction id
    parse_state: i32          # NEED_HEADER | NEED_BODY | DISPATCHING | SENDING
    msg_len: i32              # parsed from header, total bytes for current msg
    have: i32                 # bytes accumulated so far in this message

    # Variable-size send buffer for SCAN_RESULTs (heap-allocated when needed)
    big_send: *u8             # null when not using a big buffer
    big_send_len: i32
    big_send_pos: i32

var g_sessions: [256]M7SPSession   # index by task pool slot
```

### State machine

```
NEED_HEADER (0)  ← initial state
    │ recv() completes — task.read_len now has up to 8192 bytes
    │
    ▼
NEED_BODY (1)
    │ have += read_len
    │ if have >= PROTO_HEADER_SIZE:
    │     msg_len = parse_length_be(read_buf[4..8])
    │     if have >= msg_len:
    │         goto DISPATCHING
    │     else:
    │         submit_recv() (kernel reads into read_buf[have..])
    │
    ▼
DISPATCHING (2)
    │ msg_type = parse_msg_type(read_buf)
    │ build response in write_buf (or big_send if SCAN)
    │ submit_send()
    │
    ▼
SENDING (3)
    │ send completes
    │ if big_send: free, reset
    │ have = 0, msg_len = 0
    │ goto NEED_HEADER (keep-alive — submit recv for next message)
```

### Handling SCAN_RESULT batches > 8KB

`handle_scan` currently builds 32 KiB batches.  Two clean options:

**Option A: shrink batches to fit `task.write_buf` (8 KiB)**
- Cap `batch_byte_budget` at ~7 KiB
- Smaller batches, more `SCAN_RESULT` messages per scan
- Simpler — no extra allocation
- Tradeoff: more CQE roundtrips on big scans

**Option B: per-session big buffer**
- `m7sp_session_alloc_big_send(session, size)` mmaps a heap region
- `task_submit_send_zc_buf(pool, task, big_send, len)` sends from it
- Free on send completion
- Cleaner for bursty large responses

**Decision: A first, B as a second-pass optimization.**  Wiki seed has
3 docs ≈ 800 bytes total, fits trivially in 7 KiB.  If/when we have
collections big enough to need batches > 7 KiB worth visiting, switch
to B.

### File layout

```
projects/mausoleum/lib/server_async.ritz   ← NEW: serve_loop_async + handlers
projects/mausoleum/src/main.ritz            ← gate: --serial keeps old loop
                                              for now; default → async
```

The new file is library code; the choice of which loop to run lives in
`main.ritz` so the rollout is staged.  Run with `--serial` to fall back
to the existing path if anything breaks.

## Implementation phases

| # | Phase | Effort | Done when |
|---|---|---|---|
| 1 | Skeleton: `server_async.ritz` with `serve_async`, the `M7SPSession` table, and a `handle_task_event(task)` that just echoes incoming bytes | 2-3 h | `mausoleum serve --async` accepts connections, echoes |
| 2 | M7SP framing: parse header, accumulate body into per-task buffer, dispatch by msg_type | 3-4 h | wiki-seed CLI works against `--async` mausoleum |
| 3 | All message handlers wired (CONNECT, PING, INSERT, GET, UPDATE, DELETE, TXN_*, SCAN) | 2-3 h | nexus pass 1 (seed) works against `--async` |
| 4 | SCAN multi-message response — emit one `SCAN_RESULT` per task event, track iter state in session | 2-3 h | nexus pass 2 (rebuild from existing 3 docs) works |
| 5 | Concurrent client correctness — two clients hammering simultaneously without blocking each other | 1-2 h | parallel wiki-seed × 2 against same DB succeeds — **DONE**: `tools/concurrent_test.sh` (14/14 assertions); fixed two latent bugs unmasked by phase-5 stress (see Notes). |
| 6 | Encryption variant (`serve_loop_encrypted` → `serve_async_encrypted`) | 4-6 h | TLS path works |
| 7 | Make async the default; keep `--serial` as escape hatch for bisecting | 30 min | benchmark shows it's at least as fast |

**Total: 1.5-2 days of focused work, in 6+1 phases.**  Phases 1-5 are
required for nexus's wiki use case to work concurrently. Phase 6 only
matters when encryption is on (off in dev mode).  Phase 7 is the cherry
on top — flip the default once we trust the new path.

## Testing strategy

- **Phase 1**: `nc 127.0.0.1 7777`, type bytes, see them echoed
- **Phase 2-3**: existing `wiki-seed` CLI — already builds + tested
- **Phase 4**: nexus rebuild_index_from_mausoleum, confirms SCAN
- **Phase 5**: two `wiki-seed` invocations in parallel
- **Phase 6**: `mausoleum shell` (which uses encryption) against
  `--async` mausoleum
- All phases: `make matrix` 33/33

## Phase 5 — Notes on bugs fixed

Phase 5 stress-testing (parallel wiki-seed, slow-client isolation,
concurrent SCAN starvation) surfaced two latent bugs that were
invisible to phase 1-4 because none of those phases had two clients
hitting the server in interleaved patterns under load.

1. **`sys_io_uring_enter` was using `syscall4`** (`projects/ritz/
   ritzlib/uring.ritz`).  The kernel's `io_uring_enter` actually takes
   six args — `(fd, to_submit, min_complete, flags, argp, argsz)`.
   With `syscall4`, registers `r8` and `r9` (argp / argsz) held
   whatever the call site left there.  When the bytes happened to be
   non-zero the kernel saw a "real" `argp` pointer, and because
   `IORING_ENTER_EXT_ARG` wasn't set, it required `argsz ==
   sizeof(sigset_t)` and rejected the call with `-EINVAL`.  Symptom:
   the async serve loop crashed with `ret=-22` immediately after the
   first client cleanly disconnected.  Fix: switch to `syscall6` and
   pass explicit `argp=0, argsz=0`.

2. **`client_scan` callback was cast as `*fn(...)`** instead of
   `fn(...)` (`projects/mausoleum/lib/client.ritz`).  The emitter
   compiled `(*cb)(...)` as "load eight bytes from the function's
   entry point and call THAT pointer," which read raw machine code
   and called into garbage.  For tiny scans (≤5 docs) the loaded
   bytes occasionally landed somewhere survivable; longer scans were
   guaranteed to crash.  Phase 4 hadn't seen it because it tested
   SCAN through the nexus client (Ritz-side `client_scan` was
   exercised here for the first time).  Fix: cast to `fn(...)` and
   call `cb(...)` directly.

After both fixes, `tools/concurrent_test.sh` reports 14/14 assertions:
parallel seed succeeds, a silent `nc` client doesn't stall a
concurrent wiki-seed (~7 ms wall), and 30 background SCAN iters
(15,000 doc reads) interleave with 10 ping-loops with `max=10ms` —
indistinguishable from the no-contention baseline.

## Risks

| Risk | Mitigation |
|---|---|
| ritzlib's `Task` struct doesn't fit M7SP framing well | Side-table sessions; option B for big buffers |
| TaskPool's 256-task cap too low for production | Make it configurable when we hit it |
| Phase 4 (SCAN multi-message) is the hardest — iter state must persist across CQEs | Store `*BTreeIter` in `M7SPSession`; reissue `task_submit_send` after each batch's send completes |
| Encryption path (`serve_loop_encrypted`) is more complex (stateful TLS) | Phase 6 is optional — defer if dev-mode-only is acceptable |

## Why opt-in via `--async` first

Three reasons:

1. The existing `serve_loop_plain` actually works for the demo today.
   Risk isolation matters when refactoring core infrastructure.
2. Bisecting will be much easier — when something breaks, `--serial`
   gives us a known-good baseline to compare against.
3. The matrix has been green every commit this session.  Don't break
   that for an architecture change that takes multiple days.

## Out of scope

- **Connection limits / backpressure**: rely on TaskPool's existing 256-task cap
- **Per-connection arena reuse**: heap alloc per session is fine for now
- **Multi-process workers**: zeus already does this for valet; if we
  need it for mausoleum, fork-after-listen the same way valet does
- **Zero-copy from B-tree pages**: `task_submit_send_zc_buf` already
  supports this, but the buffer-pool unpin lifecycle is tricky enough
  to defer

## Reference

- valet's connection state machine: `projects/valet/lib/valet.ritz:746-1014`
  (`CONN_STATE_RECV` / `_PARSE` / `_SEND`)
- valet's `valet_run` calls `task_server_run(srv, valet_handle_connection)`:
  `projects/valet/lib/valet.ritz:1422-1424`
- ritzlib `TaskServer` API: `projects/ritz/ritzlib/async_tasks.ritz:419-715`
