# Goliath

Content-addressable filesystem for Harland. Design phase.

---

## Overview

Goliath is a modern filesystem built on content-addressing and namespace overlays. It separates the storage of content (blobs) from the naming of content (namespaces), enabling atomic writes, automatic deduplication, and instant snapshots.

---

## Where It Fits

```
User processes (shell, editors, etc.)
    │ File operations (open, read, write, stat)
    ▼
  GOLIATH (VFS / filesystem server)
    ├── Namespace Layer (hierarchical paths)
    ├── Content Store (immutable blobs)
    └── Block Layer (hardware storage)
         │
         ▼
   Harland VMM / VirtIO block
```

---

## Philosophy

| Principle | Description |
|-----------|-------------|
| **Immutable blobs** | Content is identified by hash, never modified in-place |
| **Mutable namespaces** | Paths point to blob IDs. Paths can be reassigned. |
| **Atomic everything** | No partial writes. A write either fully succeeds or does not happen. |
| **Deduplication free** | Same content always has the same blob ID. Identical files share storage. |
| **Integrity built-in** | The hash is the address. Data corruption is immediately detectable. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Namespace Layer                          │
│  /home/user/doc.txt  →  BlobID(sha256:abc123...)        │
│                                                          │
│  - Hierarchical paths (familiar filesystem interface)   │
│  - Capability-protected (you can only access your tree) │
│  - Instant snapshots (copy namespace metadata, not data)│
├─────────────────────────────────────────────────────────┤
│                 Content Store                            │
│  BlobID(sha256:abc123...) → [raw bytes]                 │
│                                                          │
│  - Write-once, read-forever                              │
│  - Automatic deduplication                               │
│  - Garbage collected (unreferenced blobs reclaimed)     │
├─────────────────────────────────────────────────────────┤
│                 Block Layer                              │
│  Physical storage: VirtIO-blk (QEMU), NVMe              │
└─────────────────────────────────────────────────────────┘
```

---

## Key Operations

### Writing a File

1. Compute SHA-256 of the content
2. Check if BlobID already exists in the content store (deduplication check)
3. If not, write content to a new blob
4. Update namespace: `/home/user/doc.txt → BlobID(sha256:abc123...)`

The write is atomic: the namespace pointer is only updated after the blob is fully persisted.

### Instant Snapshots

To snapshot `/home/user/`:

1. Copy the namespace tree for `/home/user/` (just metadata — blob IDs, not data)
2. Store the snapshot's root namespace pointer

This is O(tree_size), not O(data_size). The actual content is shared between the snapshot and the live filesystem.

### Deduplication

If you have 1000 copies of the same file, the content store holds it once. All 1000 namespace entries point to the same BlobID.

---

## Comparison with Traditional Filesystems

| Feature | ext4 / NTFS | Goliath |
|---------|-------------|---------|
| Atomic writes | Journal (limited) | Always atomic |
| Deduplication | Optional, complex | Built-in |
| Snapshots | LVM snapshots (copy-on-write) | Instant namespace copy |
| Integrity | Optional checksums | Always (hash = address) |
| Modification | In-place update | New blob, pointer update |

---

## Capability-Based Access

Following Harland's capability model, Goliath uses capabilities to control filesystem access:

- Processes receive a `NamespaceCapability` that grants access to a subtree
- A process with `/home/alice/` capability cannot access `/home/bob/`
- Capabilities can be delegated (restricted, not escalated)

---

## Current Status

Design phase. Architecture defined in `docs/DESIGN.md`.

---

## Related Projects

- [Harland](harland.md) — Microkernel that Goliath runs on
- [rzsh](rzsh.md) — Shell that uses Goliath for filesystem access
- [Kernel Subsystem](../subsystems/kernel.md)
