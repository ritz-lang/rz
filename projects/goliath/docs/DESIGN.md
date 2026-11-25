# Goliath Design Document

## Overview

Goliath is a content-addressable filesystem designed for the Harland microkernel. It separates the concerns of **content storage** (immutable blobs) from **naming** (mutable namespace mappings).

## Core Concepts

### 1. Content Addressing

Every piece of content is identified by its cryptographic hash:

```ritz
pub struct BlobID
    hash: [32]u8    # SHA-256

# BlobID is computed, not assigned
fn compute_blob_id(data: ByteView) -> BlobID
    sha256(data)
```

**Properties**:
- Same content → same BlobID (automatic deduplication)
- BlobID is a checksum (corruption always detectable)
- Blobs are immutable (you can't change content without changing ID)

### 2. Namespaces

A namespace maps human-readable names to BlobIDs:

```ritz
pub struct Namespace
    root: BlobID        # Points to root directory blob
    cap: Cap            # Capability to access this namespace

pub struct NsEntry
    name: String        # Up to 255 bytes UTF-8
    kind: EntryKind
    metadata: Metadata

pub enum EntryKind
    File(BlobID)
    Dir(BlobID)         # Points to directory blob
    Symlink(String)     # Target path
    Mount(NamespaceID)  # Mount point
```

**Properties**:
- Directories are also blobs (just serialized NsEntry lists)
- Modifying a directory creates a new directory blob
- Old versions remain until garbage collected

### 3. Blob Store

The blob store manages physical storage of content:

```ritz
pub trait BlobStore
    fn get(&self, id: BlobID) -> Result<ByteView, Error>
    fn put(&mut self, data: ByteView) -> Result<BlobID, Error>
    fn exists(&self, id: BlobID) -> bool
    fn delete(&mut self, id: BlobID) -> Result<(), Error>
```

**Implementation options**:
- **Flat file**: One file per blob, filename = hex(BlobID)
- **Pack files**: Multiple blobs packed together (like git)
- **Block device**: Direct storage on virtio-blk

---

## On-Disk Format

Implemented (AGAST #1881): one format, the **image** (`src/image.ritz`): a
`GOLIATHS` header naming the root directory blob, then every live blob as
`{ id, size, bytes }`. A host file holds one image (`src/file_store.ritz`);
a block device holds two from sector 2, each named by a `GOLIATHB` slot
header (sectors 0 and 1) carrying a generation and a checksum
(`src/block_store.ritz`). A save writes its image beside the one in use and
then the other header, so a save cut short still loads the previous tree
(AGAST #4226). Loading verifies every blob's hash and
that the tree is whole. The store is in memory between loads and saves, so
the image carries only live blobs and needs no allocation bitmap.

The extent / bitmap / blob-index layout this section used to sketch is a
possible later format for stores too big to hold in memory.

------  ----  -----
0x00    8     Magic: "GOLIATH\0"
0x08    4     Version (1)
0x0C    4     Block size (4096)
0x10    8     Total blocks
0x18    8     Free blocks
0x20    32    Root namespace BlobID
0x40    32    Blob index BlobID
0x60    8     Flags
0x68    8     Last mount time
0x70    8     Last write time
0x78    8     Reserved
```

### Block Allocation Bitmap

Following superblock. 1 bit per block.

### Blob Storage

Blobs are stored in extents (contiguous block runs):

```ritz
pub struct BlobHeader
    magic: u32          # 0x424C4F42 ("BLOB")
    id: BlobID          # SHA-256 hash
    size: u64           # Uncompressed size
    compressed_size: u64
    compression: u8     # 0=none, 1=lz4, 2=zstd
    flags: u8
    checksum: u32       # CRC32 of compressed data
```

### Blob Index

The blob index maps BlobID → physical location:

```ritz
pub struct BlobIndex
    entries: BTreeMap<BlobID, BlobLocation>

pub struct BlobLocation
    block: u64
    offset: u32
    size: u32
```

The index itself is stored as a blob! (Bootstrap: superblock points to it)

---

## Operations

### Reading a File

```
1. Namespace lookup: /home/user/file.txt
   - Read root dir blob from namespace
   - Find "home" → DirBlobID
   - Read that blob, find "user" → DirBlobID
   - Read that blob, find "file.txt" → FileBlobID

2. Content fetch:
   - Look up FileBlobID in blob index
   - Read blob from disk
   - Verify hash matches BlobID
   - Return content
```

### Writing a File

```
1. Store new content as blob:
   - Compute BlobID = sha256(content)
   - If blob exists, skip storage (dedup!)
   - Otherwise, allocate blocks and write

2. Update namespace:
   - Load parent directory blob
   - Create new NsEntry pointing to new BlobID
   - Store new directory as blob
   - Recursively update parent directories to root
   - Update namespace root pointer

3. (Optional) Cleanup:
   - Old blobs remain until GC
   - Instant "undo" if we keep old namespace pointer
```

### Copy-on-Write

COW is **free** with this design:

```ritz
fn copy_file(src_ns: &Namespace, src_path: &str,
             dst_ns: &mut Namespace, dst_path: &str) -> Result<(), Error>
    # Just copy the BlobID reference!
    let blob_id = src_ns.resolve(src_path)?
    dst_ns.link(dst_path, blob_id)
    # No data copied - both point to same blob
```

### Snapshots

Also **free**:

```ritz
fn snapshot(ns: &Namespace) -> NamespaceSnapshot
    # Just remember the current root BlobID
    NamespaceSnapshot {
        root: ns.root,
        timestamp: now(),
    }

fn restore(ns: &mut Namespace, snap: &NamespaceSnapshot)
    ns.root = snap.root
    # Entire filesystem state restored instantly
```

---

## Garbage Collection

Implemented (AGAST #1881) as reference counting (`src/blob_store.ritz`,
`src/namespace.ritz`): a blob is held once per directory entry naming it and
the root once by the namespace. A directory blob takes its children's
references when first stored, and drops them when its own last reference
goes, so replacing the root frees everything only the old tree reached.
Loading an image recounts by marking from the root and sweeps the rest.

---

## Capabilities Integration

Goliath integrates with Harland's capability system:

```ritz
# Namespace access requires capability
pub struct NamespaceCap
    ns_id: NamespaceID
    rights: NamespaceRights

pub enum NamespaceRights: u32
    Read        = 1 << 0    # List dirs, read files
    Write       = 1 << 1    # Create/modify files
    Delete      = 1 << 2    # Remove files
    Snapshot    = 1 << 3    # Create snapshots
    Mount       = 1 << 4    # Create sub-namespaces
    Admin       = 1 << 5    # Change permissions

# Example: Read-only access to /var/log
let log_cap = namespace_derive(system_ns, "/var/log",
                               NamespaceRights.Read)
```

---

## Milestones

### G1: In-Memory Prototype
- [ ] BlobStore trait with HashMap backend
- [ ] Namespace with directory operations
- [ ] Basic CRUD operations
- [ ] Unit tests

### G2: Persistence
- [ ] On-disk format implementation
- [ ] Block allocation
- [ ] Blob index
- [ ] Mount/unmount

### G3: Integrity
- [ ] Hash verification on read
- [ ] Checksum verification
- [ ] Corruption detection
- [ ] Recovery tools

### G4: Performance
- [ ] Blob caching
- [ ] Directory caching
- [ ] Write batching
- [ ] Compression (LZ4)

### G5: Advanced Features
- [ ] Garbage collection
- [ ] Snapshots
- [ ] Quotas
- [ ] Encryption

### G6: Harland Integration
- [ ] Capability-based access control
- [ ] virtio-blk backend
- [ ] Ring 2 filesystem service
- [ ] IPC interface

---

## Comparison with Traditional Filesystems

| Feature | ext4 | ZFS | Goliath |
|---------|------|-----|---------|
| Content addressing | ❌ | ✅ (checksums) | ✅ (hash=address) |
| Deduplication | ❌ | ✅ (block level) | ✅ (automatic) |
| Snapshots | ❌ | ✅ | ✅ (free!) |
| COW | ❌ | ✅ | ✅ (free!) |
| Corruption detection | ❌ | ✅ | ✅ |
| Atomic writes | Limited | ✅ | ✅ (always) |
| Complexity | Medium | High | Low |

---

## Open Questions

1. **Large file handling**: Split into chunks? What size?
2. **Directories with millions of files**: B-tree index?
3. **Concurrent access**: Locking strategy? MVCC?
4. **Network transparency**: Distributed blob store?
5. **Quotas**: Per-namespace? Per-user?

---

## References

- Git object model (content-addressed storage)
- IPFS (content-addressed networking)
- Btrfs/ZFS (COW, snapshots)
- Fossil (Venti backend)
- Perkeep (content-addressed personal storage)
