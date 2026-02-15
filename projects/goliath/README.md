# Goliath

**Content-Addressable Filesystem for Harland**

A modern filesystem built on content-addressing with namespace overlays. Designed for the Harland microkernel but usable standalone.

## Philosophy

- **Immutable blobs** - Content is stored by hash, never modified
- **Mutable namespaces** - Names point to blobs, names can change
- **Atomic everything** - No partial writes, ever
- **Deduplication free** - Same content = same blob
- **Integrity built-in** - Hash IS the address

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Namespace Layer                          │
│  /home/user/doc.txt  →  BlobID(sha256:abc123...)        │
│                                                          │
│  - Hierarchical paths (familiar UX)                      │
│  - Capability-protected                                  │
│  - Instant snapshots (copy namespace, not data)          │
├─────────────────────────────────────────────────────────┤
│                 Content Store                            │
│  BlobID(sha256:abc123...) → [raw bytes]                 │
│                                                          │
│  - Write-once, read-forever                              │
│  - Automatic deduplication                               │
│  - Garbage collected (unreferenced blobs cleaned up)     │
├─────────────────────────────────────────────────────────┤
│                 Block Layer                              │
│  Physical storage (virtio-blk, NVMe, etc.)              │
└─────────────────────────────────────────────────────────┘
```

## Status

🚧 **Design Phase** - See `docs/DESIGN.md` for architecture details.

## Building

```bash
cd /path/to/ritz
./ritz build goliath
```

## License

MIT
