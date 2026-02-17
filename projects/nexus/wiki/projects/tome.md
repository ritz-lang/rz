# Tome

*"A book of knowledge held in memory."*

High-performance in-memory data store for the Ritz ecosystem. Design phase.

---

## Overview

Tome is the in-memory caching and messaging layer of the Ritz stack. It provides the speed of Redis without the C dependency — pure Ritz, native syscalls, zero external dependencies.

---

## Where It Fits

```
Nexus → Tome (session cache, hot page cache)
Spire → Tome (via Repository layer, optional)
Zeus → Tome (zero-copy IPC mode)
```

---

## Key Features

### Rich Data Structures

| Type | Description | Use Cases |
|------|-------------|-----------|
| **Strings** | Simple key-value byte strings | Session tokens, counters, feature flags |
| **Lists** | Ordered, doubly-linked sequences | Activity feeds, message queues, recent items |
| **Sets** | Unordered unique collections | Tags, permissions, online users |
| **Sorted Sets** | Score-ordered collections | Leaderboards, priority queues, rate limiting |
| **Hashes** | Field-value maps per key | User profiles, cached objects, stats |

### Time-To-Live (TTL)

Every key can have an expiry time. Expired keys are lazily evicted on access or actively purged in background sweeps:

```ritz
import tome { Client }

let tome = Client.connect("localhost:6380")?
tome.set("session:abc123", session_data, ttl: 3600)?   # Expires in 1 hour
tome.set("rate:ip:1.2.3.4", "1", ttl: 60)?             # Expires in 60 seconds
```

### Pub/Sub Messaging

Tome supports channel-based publish/subscribe for real-time event broadcasting:

```ritz
# Publisher
tome.publish("notifications:user:42", json!({ "type": "mention", "from": "alice" }))?

# Subscriber
let sub = tome.subscribe("notifications:user:42")?
loop
    let msg = sub.recv().await?
    handle_notification(msg)
```

### Eviction Policies

When Tome reaches its memory limit, it evicts keys based on the configured policy:

| Policy | Behavior |
|--------|----------|
| `lru` | Evict least recently used |
| `lfu` | Evict least frequently used |
| `random` | Evict a random key |
| `volatile-lru` | Evict LRU among keys with TTL set |
| `noeviction` | Return error when full |

---

## Usage

### Basic Operations

```ritz
import tome { Client }

let tome = Client.connect("localhost:6380")?

# Strings
tome.set("key", "value")?
let val = tome.get("key")?    # Option<String>

# Lists
tome.lpush("queue", "item1")?
tome.lpush("queue", "item2")?
let item = tome.rpop("queue")?

# Sets
tome.sadd("online_users", "alice")?
tome.sadd("online_users", "bob")?
let count = tome.scard("online_users")?    # 2
let members = tome.smembers("online_users")?

# Hashes
tome.hset("user:42", "name", "Alice")?
tome.hset("user:42", "email", "alice@example.com")?
let name = tome.hget("user:42", "name")?

# Sorted sets (score, member pairs)
tome.zadd("leaderboard", 1000.0, "alice")?
tome.zadd("leaderboard", 850.0, "bob")?
let top3 = tome.zrange("leaderboard", 0, 2, reverse: true)?
```

### Session Management

```ritz
fn create_session(user: User) -> String
    let token = generate_token()
    let session = Session { user_id: user.id, created_at: now() }
    tome.set(
        "session:{token}",
        encode_session(session),
        ttl: 86400   # 24 hours
    ).unwrap()
    token

fn get_session(token: String) -> Option<Session>
    match tome.get("session:{token}")?
        Some(data) => Some(decode_session(data))
        None => None
```

### Cache-Aside Pattern

```ritz
fn get_wiki_page(slug: String) -> Result<WikiPage, Error>
    let cache_key = "page:{slug}"

    # Check cache first
    if let Some(cached) = tome.get(cache_key)?
        return Ok(decode_page(cached))

    # Miss — load from Mausoleum
    let page = db.query().kind("page").where("slug", slug).first()?
        .ok_or(Error.not_found("Page not found"))?

    # Store in cache for 5 minutes
    tome.set(cache_key, encode_page(page), ttl: 300)?

    Ok(page)
```

---

## Optional Persistence

Tome is primarily an in-memory store, but optional persistence is supported:

### Snapshots (RDB-style)

Periodic full snapshots to disk:

```toml
[persistence]
snapshot_interval = 300    # Every 5 minutes
snapshot_path = "./tome.snap"
```

### Append-Only File (AOF)

Every write operation is logged:

```toml
[persistence]
aof_enabled = true
aof_path = "./tome.aof"
aof_fsync = "everysec"    # "always", "everysec", "no"
```

---

## Zero-Copy IPC Mode (Zeus Integration)

When Tome runs in-process via Zeus, it operates in zero-copy mode. Ritz application workers can read cached values directly from shared memory without copying through a socket. This eliminates network overhead entirely for hot-path cache accesses.

---

## Current Status

Design phase. Architecture and data structures defined.

---

## Related Projects

- [Mausoleum](mausoleum.md) — Persistent storage, often used alongside Tome
- [Zeus](zeus.md) — App server that enables zero-copy IPC mode
- [Spire](spire.md) — Uses Tome via the Repository layer
- [Nexus](nexus.md) — Uses Tome for session and hot page caching
- [Data Subsystem](../subsystems/data.md)
