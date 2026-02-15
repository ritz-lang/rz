# Tome

In-memory data store for Ritz. Think Redis, but embedded and written in pure Ritz.

## Overview

Tome is a high-performance in-memory cache and data structure server. While [Mausoleum](https://github.com/ritz-lang/mausoleum) handles persistent storage (where data is entombed forever), Tome handles ephemeral, fast-access data that lives in memory.

## Design Goals

| Goal | Description |
|------|-------------|
| **In-memory first** | All data lives in RAM for sub-microsecond access |
| **Rich data structures** | Not just key-value — lists, sets, sorted sets, hashes, trees |
| **Embedded or standalone** | Link as library or run as separate process |
| **Optional persistence** | Snapshots and append-only logs for durability when needed |
| **Pub/sub** | Real-time messaging between components |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Command Layer                        │
│         GET, SET, LPUSH, SADD, PUBLISH, etc.            │
├─────────────────────────────────────────────────────────┤
│                  Data Structures                        │
│     String │ List │ Set │ SortedSet │ Hash │ Tree      │
├─────────────────────────────────────────────────────────┤
│                   Memory Layer                          │
│         Slab allocator, memory pools, eviction          │
├─────────────────────────────────────────────────────────┤
│               Optional Persistence                      │
│         RDB snapshots │ AOF (append-only file)          │
└─────────────────────────────────────────────────────────┘
```

## Data Structures

### Core Types

```ritz
// Strings - binary-safe byte sequences
tome.set("user:1:name", "Alice")
let name = tome.get("user:1:name")?

// Lists - ordered sequences, push/pop from both ends
tome.lpush("queue", "job1", "job2")
let job = tome.rpop("queue")?

// Sets - unordered unique elements
tome.sadd("tags:post:1", "ritz", "programming", "database")
let tags = tome.smembers("tags:post:1")?

// Sorted Sets - scored elements, range queries
tome.zadd("leaderboard", 100, "alice")
tome.zadd("leaderboard", 85, "bob")
let top10 = tome.zrange("leaderboard", 0, 9)?

// Hashes - field-value maps
tome.hset("user:1", "name", "Alice", "email", "alice@example.com")
let user = tome.hgetall("user:1")?

// Trees - hierarchical data (native, not Redis)
tome.tree_insert("org", "/specs/auth", node_data)
let children = tome.tree_children("org", "/specs")?
```

### Advanced Features

```ritz
// TTL - automatic expiration
tome.setex("session:abc123", 3600, session_data)  // expires in 1 hour

// Pub/Sub - real-time messaging
tome.subscribe("events:user:*", |channel, msg| {
    println("Received {msg} on {channel}")
})
tome.publish("events:user:login", json!({"user_id": 1}))

// Transactions - atomic multi-command execution
tome.multi()
    .incr("counter")
    .lpush("log", "incremented counter")
    .exec()?

// Lua scripting (or Ritz scripting!)
let script = tome.script(|t| {
    let val = t.get("key")?
    t.set("key", val + 1)
    val
})
```

## Eviction Policies

When memory limits are reached:

| Policy | Description |
|--------|-------------|
| `noeviction` | Return errors on writes when full |
| `allkeys-lru` | Evict least recently used keys |
| `volatile-lru` | Evict LRU keys with TTL set |
| `allkeys-random` | Evict random keys |
| `volatile-ttl` | Evict keys with shortest TTL |

## Persistence Options

### RDB Snapshots
Point-in-time snapshots written to disk periodically.

```ritz
// Config
tome.config_set("save", "60 1000")  // Save every 60s if 1000+ writes
```

### AOF (Append-Only File)
Every write operation logged for replay on restart.

```ritz
// Config
tome.config_set("appendonly", "yes")
tome.config_set("appendfsync", "everysec")  // or "always" for durability
```

## Usage Modes

### Embedded (Library)
```ritz
use tome::{Tome, Config}

let cache = Tome::new(Config {
    max_memory: 256 * 1024 * 1024,  // 256MB
    eviction_policy: EvictionPolicy::AllKeysLru,
})?

cache.set("key", "value")?
```

### Standalone (Server)
```bash
# Start Tome server
tome-server --port 6379 --maxmemory 1gb

# Connect from client
tome-cli SET key value
tome-cli GET key
```

### With Zeus (IPC)
Tome can communicate with Ritz apps via Zeus ring buffers for zero-copy cache access.

```
┌──────────────┐     Zeus      ┌──────────────┐
│   Ritz App   │◄─────────────►│     Tome     │
└──────────────┘  ring buffer  └──────────────┘
```

## Comparison

| | Tome | Redis | Mausoleum |
|-|------|-------|-----------|
| Storage | Memory | Memory | Disk |
| Persistence | Optional | Optional | Always |
| Embedded | Yes | No | Yes |
| Data types | Rich | Rich | Documents |
| Written in | Ritz | C | Ritz |

## Use Cases

- **Session storage** - Fast session lookups with TTL
- **Caching** - Cache database queries, API responses
- **Pub/Sub** - Real-time event distribution
- **Rate limiting** - Track request counts with expiration
- **Leaderboards** - Sorted sets for rankings
- **Job queues** - Lists as simple queues

## Status

**Design Phase** — API and data structure internals being defined.

## Dependencies

- Built in pure Ritz
- Optional: `mausoleum` for hybrid memory+disk caching
- Optional: `zeus` for zero-copy IPC mode

## License

MIT
