# Goliath

Content-addressable filesystem for Harland, as a Ritz library and a CLI.
**What works today:** SHA-256 blob ids, an in-memory blob store
(put/get/exists/delete), a store persisted in one host file, a VirtIO-backed
store, and a path namespace (`./rz test goliath`: 46 tests plus `test.sh`).
The `goliath` binary stores files and reads them back: `goliath put FILE`
prints the file's blob id, `goliath get ID` writes the blob to stdout, and
`goliath ls PATH` lists the namespace (AGAST #2788).

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Goliath is a modern filesystem designed for the Harland microkernel, built on content-addressing principles. Content is stored by its SHA-256 hash (making each blob immutable and automatically deduplicated), while a separate mutable namespace layer maps human-readable paths to blob IDs.

This design makes certain operations trivially cheap: snapshots are just copies of the namespace (not the data), deduplication is automatic (same bytes = same hash = same blob), and integrity is guaranteed (the hash IS the address - any corruption is immediately detectable). Goliath is inspired by Git's object store and Plan 9's namespace design.

Goliath is usable as a standalone library on Linux as well as the native filesystem for Harland. It uses cryptosec for SHA-256 hashing and is designed to eventually support squeeze for compressed blob storage.

## Features

- Content-addressable blob storage - store by hash, retrieve by hash
- Automatic deduplication - identical content stored once
- Mutable namespace layer - paths point to blob IDs
- Atomic operations - no partial writes ever
- Integrity verification - hash IS the address
- Instant snapshots - copy namespace, not data
- Garbage collection - unreferenced blobs cleaned up
- Capability-protected namespaces
- Usable standalone on Linux or as Harland's native filesystem

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# goliath = { path = "../goliath" }

# Build and run tests (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build goliath
./rz test goliath                               # unit tests + test.sh
```

## Usage

### CLI

```bash
export GOLIATH_STORE=/tmp/demo.store   # default: ./goliath.store
goliath put notes.txt                  # stores it as /notes.txt
# 1f2c...e9  (the SHA-256 of notes.txt: its blob id)
goliath get 1f2c...e9 > copy.txt       # the exact bytes back
goliath ls /                           # ID  SIZE  NAME, one line per entry
goliath ls /notes.txt                  # just that file's line
```

`put` links the file at `/<its name>`, replacing an older file of that name.
`get` and `ls` only read the store; a missing store is an empty one. Exit
status: 0 done, 1 failed (not found, unreadable, corrupt store), 2 usage.

The store file (`src/file_store.ritz`) holds every blob and the namespace
root. It is read whole and written back whole (to `<store>.tmp.<pid>`, then
renamed over the store). `put` holds an exclusive `flock` on `<store>.lock`
from load to save, so concurrent `put`s queue up rather than lose each other's
updates (#3882). A file that isn't a complete, intact store is refused, never
half-read. Each blob is checked against its id on load. Limits for now: the
root directory holds 256 entries; every `put` keeps the superseded root
directory blob, so the store grows until garbage collection lands (#1881).

### Library

```ritz
import goliath { BlobStore, Namespace, BlobId }

# Content store - write-once, read-forever
let store = BlobStore.open("./data")

# Store content by hash
let data: *u8 = "Hello, Goliath!"
let id: BlobId = store.put(data, strlen(data))
# id is now sha256("Hello, Goliath!")

# Retrieve by hash - guaranteed to match
let retrieved: *u8 = store.get(id)

# Namespace - maps paths to blob IDs
let ns = Namespace.open("./namespace", store)
ns.put("/hello.txt", id)

# Resolve path to blob
let blob_id: BlobId = ns.get("/hello.txt")
let content = store.get(blob_id)
```

```ritz
# Snapshot - just copies the namespace, not the data
let snapshot_ns = ns.snapshot()

# Delete from namespace (blob stays in store until GC)
ns.remove("/hello.txt")

# Garbage collect unreferenced blobs
store.gc(ns.all_blob_ids())
```

## Dependencies

- `cryptosec` - SHA-256 for content addressing

## Status

**Alpha, with a passing suite.** `./rz test goliath` runs 5 test files
(46 tests) and `test.sh`, which drives the CLI end to end against a temp
store. Run it to get today's numbers.

Core blob store (put/get/exists), the host-file store, namespaces and path
handling are implemented. Garbage collection and snapshot support are still
planned. The CLI has no `mkdir` yet, so `put` only fills `/`.

## License

MIT License - see LICENSE file
