# Kernel Subsystem

The kernel subsystem provides the lowest-level abstractions: the microkernel, filesystem, display server, and font rendering. All components are written in Ritz and run on bare x86-64 hardware.

---

## Projects in This Subsystem

| Project | Role | Status |
|---------|------|--------|
| [Harland](../projects/harland.md) | IPC-based microkernel | Active |
| [Indium](../projects/indium.md) | OS distribution (init, utilities, images) | Active |
| [Goliath](../projects/goliath.md) | Content-addressable filesystem | Design |
| [Prism](../projects/prism.md) | Display server and compositor | Active |
| [Angelo](../projects/angelo.md) | Font loading and rendering | Active |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Space                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                │
│  │  Shell  │  │ Goliath │  │  Prism  │  │  Apps   │                │
│  │  (rzsh) │  │   VFS   │  │(display)│  │         │                │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘                │
│       │            │            │            │                      │
│       └────────────┴──────┬─────┴────────────┘                      │
│                           │ IPC (message passing)                   │
├───────────────────────────┼─────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  HARLAND MICROKERNEL                         │   │
│  │                                                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │   │
│  │  │Scheduler │  │   IPC    │  │   VMM    │  │ Interrupts │   │   │
│  │  │(preempt) │  │(L4-style)│  │(4-level) │  │(APIC/IOAPIC│   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│           x86-64 Hardware (QEMU or bare metal)                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Harland: The Microkernel

Harland is an IPC-based microkernel for x86-64. The design follows the L4 microkernel philosophy: keep the kernel minimal, put everything else in user space.

**Key components:**

- **Virtual Memory Manager** — 4-level page tables (PML4), copy-on-write semantics
- **Scheduler** — Preemptive, SMP-aware, O(1) priority-based scheduling
- **IPC** — Synchronous message passing + async channels, capability-based security
- **Interrupt Handling** — Local APIC, IOAPIC, MSI-X for modern devices

Harland boots via a UEFI bootloader written in Ritz. The boot sequence:
1. Stage 0: UEFI firmware loads `BOOTX64.EFI`
2. Stage 1: UEFI app gets memory map, loads kernel, exits boot services
3. Stage 2: Kernel sets up paging, GDT, IDT, APIC

**Language extensions for kernel programming:**

| Feature | Syntax | Purpose |
|---------|--------|---------|
| Inline assembly | `asm x86_64:` block | Direct hardware access |
| Naked functions | `@naked` | Custom prologues/epilogues |
| Volatile MMIO | `@volatile` | Memory-mapped I/O |
| Packed structs | `@packed` | Hardware register layouts |

---

## Goliath: The Filesystem

Goliath is a content-addressable filesystem with a separation between content (blobs) and names (namespaces).

**Core concept:**

```
/home/user/doc.txt  →  BlobID(sha256:abc123...)  →  [raw bytes]
```

Names point to blobs. Blobs are immutable. The same content always maps to the same BlobID — deduplication is free.

**Three-layer architecture:**

1. **Namespace Layer** — Hierarchical paths, instant snapshots (just copy the namespace)
2. **Content Store** — Write-once blobs keyed by hash, garbage-collected
3. **Block Layer** — Physical storage (virtio-blk, NVMe, etc.)

---

## Prism: The Display Server

Prism is a Wayland-inspired display server that manages windows and composites the final display.

**Key design decisions:**

- **Hybrid rendering** — Clients can render to a shared memory buffer (buffer mode) or send draw commands (command mode)
- **Capability-based security** — Window handles are capabilities
- **Async scanline compositor** — Enables parallel rendering of non-overlapping screen regions
- **Triple buffering** — Front (displayed), back (ready), pending (being drawn)
- **Damage tracking** — Only redraws changed regions

**Client protocol:**

```ritz
# What Prism gives each client
struct WindowCapability
    id: WindowId
    buffer: SharedMemoryHandle      # For direct rendering
    command_ring: RingBufferHandle  # Client to Prism commands
    event_ring: RingBufferHandle    # Prism to client events

# Draw commands clients can send
enum RenderCommand
    FillRect { rect: Rect, color: Color }
    DrawText { pos: Point, text: StrView, font: FontId, size: u32 }
    BlitImage { pos: Point, image: ImageHandle }
    SubmitBuffer { damage: Vec<Rect> }
```

---

## Angelo: Font Rendering

Angelo handles all font-related operations for Prism. It is integrated as a library, not a separate process.

**Pipeline:**

```
"Hello"
    → Unicode codepoints
    → CMAP table lookup (Unicode → Glyph ID)
    → GSUB substitution (ligatures)
    → GPOS/KERN kerning
    → GLYF outline extraction
    → Bezier curve rasterization
    → Pixel bitmap with antialiasing
```

**Caching:**

Rasterized glyphs are cached by `(font_id, glyph_id, size_px, subpixel_x)`. The cache uses LRU eviction.

**Supported formats:**

- TrueType (.ttf)
- OpenType (.otf)
- OpenType features: ligatures (GSUB), advanced kerning (GPOS)

---

## Relationships

- Harland provides the address space isolation and IPC channels that Goliath and Prism run on top of
- Prism calls Angelo when processing `DrawText` render commands
- rzsh runs as a user-space process on Harland, using Goliath for file access
- Applications communicate with Prism via shared-memory ring buffers (allocated by Harland's VMM)

---

## See Also

- [Harland project page](../projects/harland.md)
- [Goliath project page](../projects/goliath.md)
- [Prism project page](../projects/prism.md)
- [Angelo project page](../projects/angelo.md)
- [Graphics Subsystem](graphics.md)
- [Architecture overview](../architecture.md)
