# Goliath

Content-addressable filesystem for Harland - immutable blob storage with mutable namespace overlays.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

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

# Build and run tests
export RITZ_PATH=/path/to/ritz
./ritz build .
./build/debug/goliath-tests
```

## Usage

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

**Alpha** - Architecture, blob ID design, and test infrastructure are in place. Core blob store (put/get/exists) and namespace operations are being implemented via TDD. Garbage collection and snapshot support are planned for subsequent phases.

## License

MIT License - see LICENSE file
