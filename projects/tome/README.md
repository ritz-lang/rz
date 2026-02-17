# Tome

In-memory data store for Ritz - embedded cache and data structure server with Redis-compatible semantics.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Tome is a high-performance in-memory cache and data structure store written in pure Ritz. While Mausoleum handles persistent document storage, Tome handles ephemeral fast-access data that lives in RAM. Think Redis, but embedded - it can be linked directly into a Ritz application as a library, or run as a standalone server process with a network protocol.

Tome provides rich data structures beyond simple key-value pairs: lists, sets, sorted sets, hash maps, and native tree structures. It supports TTL-based automatic expiration, pub/sub messaging, and optional persistence via snapshots or append-only log files. Tome integrates with Zeus ring buffers for zero-copy cache access from worker processes.

## Features

- In-memory storage with sub-microsecond access
- Strings, lists, sets, sorted sets, hash maps, and trees
- TTL-based key expiration
- Pub/sub messaging between components
- Atomic transactions (multi-command execution)
- LRU and other eviction policies when memory limits are reached
- Optional persistence via RDB snapshots or AOF logging
- Embedded library mode (link into your app)
- Standalone server mode with CLI client
- Integration with Zeus for zero-copy IPC access

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# tome = { path = "../tome" }

# Build all binaries
export RITZ_PATH=/path/to/ritz
./ritz build .

# Start the standalone server
./build/debug/tome-server --port 6379

# Interactive CLI
./build/debug/tome-cli
```

## Usage

```ritz
import tome { Tome }

# Embedded usage
let cache = Tome.new(256 * 1024 * 1024)  # 256MB

# String operations
cache.set("user:1:name", "Alice")
let name = cache.get("user:1:name")

# List operations (queue)
cache.lpush("jobs", "job1")
let job = cache.rpop("jobs")

# Set operations
cache.sadd("tags:post:1", "ritz")
let tags = cache.smembers("tags:post:1")

# Sorted set (leaderboard)
cache.zadd("scores", 100, "alice")
cache.zadd("scores", 85, "bob")
let top = cache.zrange("scores", 0, 9)

# TTL expiration (session storage)
cache.setex("session:abc", 3600, session_data)  # 1 hour TTL

# Pub/sub
cache.subscribe("events:*", fn(channel: *u8, msg: *u8)
    println(msg)
)
cache.publish("events:login", "user 1 logged in")
```

## Dependencies

Tome has no required dependencies beyond `ritzlib`. Optional integrations:
- `mausoleum` - For hybrid memory+disk caching
- `zeus` - For zero-copy IPC mode

## Status

**Alpha** - API design and data structure internals are being defined. Basic string and list operations are being implemented with the embedded server mode. Persistence, pub/sub, and Zeus integration are planned for subsequent phases.

## License

MIT License - see LICENSE file
