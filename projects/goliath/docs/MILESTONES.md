# Goliath Development Milestones

## Goal: Content-Addressable Filesystem for Harland

---

## G1: In-Memory Prototype
**Goal**: Core data structures and operations working in memory

**Tasks**:
1. [ ] BlobID type (SHA-256 wrapper)
2. [ ] ByteView / ByteViewMut types
3. [ ] BlobStore trait definition
4. [ ] MemoryBlobStore implementation
5. [ ] DirEntry / Directory structures
6. [ ] Namespace with path resolution
7. [ ] create_file / read_file / delete_file
8. [ ] create_dir / list_dir / delete_dir
9. [ ] Unit tests for all operations

**Test**: Create namespace, write files, read back, verify content

---

## G2: On-Disk Persistence
**Goal**: Survive restarts

**Tasks**:
1. [ ] Superblock format
2. [ ] Block allocation bitmap
3. [ ] Blob header format
4. [ ] DiskBlobStore implementation
5. [ ] Blob index (BlobID → block location)
6. [ ] Mount / unmount operations
7. [ ] fsync / flush semantics
8. [ ] Integration tests with file backend

**Test**: Write data, unmount, remount, verify data intact

---

## G3: Integrity & Reliability
**Goal**: Detect and handle corruption

**Tasks**:
1. [ ] Hash verification on blob read
2. [ ] CRC32 checksum on blob header
3. [ ] Corruption error types
4. [ ] Bad block handling
5. [ ] Journal / WAL for namespace updates
6. [ ] Crash recovery
7. [ ] fsck equivalent tool

**Test**: Corrupt blob on disk, verify detection on read

---

## G4: Performance
**Goal**: Fast enough for real use

**Tasks**:
1. [ ] Blob cache (LRU)
2. [ ] Directory cache
3. [ ] Write batching / delayed allocation
4. [ ] LZ4 compression
5. [ ] Extent-based allocation (reduce fragmentation)
6. [ ] Parallel blob hashing
7. [ ] Benchmarks

**Test**: 1000 file creates < 1 second

---

## G5: Advanced Features
**Goal**: Features that make Goliath special

**Tasks**:
1. [ ] Garbage collection (mark & sweep)
2. [ ] Incremental GC (online)
3. [ ] Snapshot creation
4. [ ] Snapshot restore
5. [ ] Per-namespace quotas
6. [ ] Encryption (per-blob, key management)
7. [ ] Large file chunking

**Test**: Create snapshot, modify files, restore, verify original state

---

## G6: Harland Integration
**Goal**: Run as Ring 2 filesystem service

**Tasks**:
1. [ ] Capability-based access control
2. [ ] NamespaceCap with rights
3. [ ] IPC protocol (Channel<FsMsg>)
4. [ ] virtio-blk backend
5. [ ] DMA buffer management
6. [ ] Async I/O
7. [ ] Multiple namespace support
8. [ ] Mount/bind operations

**Test**: Ring 3 app reads/writes files via Ring 2 filesystem service

---

## Milestone Dependencies

```
G1 (In-Memory)
    │
    ▼
G2 (Persistence)
    │
    ├──────────┐
    ▼          ▼
G3 (Integrity) G4 (Performance)
    │          │
    └────┬─────┘
         ▼
    G5 (Advanced)
         │
         ▼
    G6 (Harland)
```

---

## Quick Start (After G1)

```ritz
import goliath

fn main() -> i32
    # Create in-memory filesystem
    let store = MemoryBlobStore.new()
    let mut ns = Namespace.new(&store)

    # Write a file
    ns.write("/hello.txt", s"Hello, Goliath!")?

    # Read it back
    let content = ns.read("/hello.txt")?
    print(content)

    # List directory
    for entry in ns.list("/")?
        print("  {entry.name}")

    0
```

---

## API Overview

```ritz
# Core types
pub struct BlobID { hash: [32]u8 }
pub struct Namespace { ... }
pub struct DirEntry { name: String, kind: EntryKind, meta: Metadata }

# BlobStore trait
pub trait BlobStore
    fn get(&self, id: BlobID) -> Result<ByteView, Error>
    fn put(&mut self, data: ByteView) -> Result<BlobID, Error>
    fn exists(&self, id: BlobID) -> bool
    fn delete(&mut self, id: BlobID) -> Result<(), Error>

# Namespace operations
impl Namespace
    fn new(store: &dyn BlobStore) -> Self
    fn read(&self, path: &str) -> Result<ByteView, Error>
    fn write(&mut self, path: &str, data: ByteView) -> Result<(), Error>
    fn delete(&mut self, path: &str) -> Result<(), Error>
    fn list(&self, path: &str) -> Result<Vec<DirEntry>, Error>
    fn mkdir(&mut self, path: &str) -> Result<(), Error>
    fn rmdir(&mut self, path: &str) -> Result<(), Error>
    fn stat(&self, path: &str) -> Result<Metadata, Error>
    fn snapshot(&self) -> Snapshot
    fn restore(&mut self, snap: &Snapshot)
```
