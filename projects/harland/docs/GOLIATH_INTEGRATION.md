# Goliath Filesystem Integration Plan

## Overview

Goliath is a content-addressable filesystem. Integration with Harland requires:
1. **Kernel-space blob store** for boot-time filesystem access
2. **VFS abstraction** for userspace filesystem operations
3. **Ring 2 filesystem service** for runtime operations

## Current State

### Goliath
- `BlobStore`: Content-addressed storage (hash → data)
- `Namespace`: Path → BlobId mapping
- Uses `sys_mmap()` for memory allocation (Linux syscalls)

### Harland Kernel
- `kalloc()`/`kfree()`: Kernel heap allocator
- `pmm_alloc_page()`/`pmm_free_page()`: Physical memory
- VirtIO block driver for disk access

## Integration Phases

### Phase 1: Kernel Blob Store (Boot-time)

Create `kernel/src/fs/kblob.ritz`:
- `KBlobStore` using `kalloc()` instead of `sys_mmap()`
- Minimal subset for reading initramfs
- No persistence (RAM-only for now)

```ritz
# Kernel blob store using kalloc
pub struct KBlobStore
    entries: *KBlobEntry
    capacity: i32
    count: i32

pub fn kblob_store_new() -> KBlobStore
    let entries: *KBlobEntry = kalloc(64 * 56) as *KBlobEntry
    # ...

pub fn kblob_store_put(store: *KBlobStore, data: *u8, size: u64) -> BlobId
pub fn kblob_store_get(store: *KBlobStore, id: *BlobId) -> *u8
```

### Phase 2: VFS Abstraction

Create `kernel/src/fs/vfs.ritz`:
- Abstract filesystem operations
- Multiple backend support (Goliath, devfs, procfs)

```ritz
pub struct VfsOps
    open: fn(*u8, u64, i32) -> i32
    read: fn(i32, *u8, u64) -> i64
    write: fn(i32, *u8, u64) -> i64
    close: fn(i32) -> i32
    stat: fn(*u8, u64, *Stat) -> i32

pub fn vfs_register_fs(name: *u8, ops: *VfsOps) -> i32
pub fn vfs_mount(source: *u8, target: *u8, fstype: *u8) -> i32
```

### Phase 3: Initramfs Loading

At boot:
1. Load initramfs from VirtIO disk (or embedded in kernel)
2. Parse as Goliath namespace blob
3. Mount at `/`

```ritz
# In kernel_main()
kblob_store_init()
initramfs_load()
vfs_mount("goliath://boot", "/", "goliath")
```

### Phase 4: Ring 2 Filesystem Service

Once userspace works:
1. Goliath runs as Ring 2 service
2. Kernel forwards syscalls via IPC
3. Goliath uses shared memory for zero-copy I/O

## Allocator Abstraction

To share code between kernel and userspace Goliath:

```ritz
# goliath/src/alloc.ritz
pub struct Allocator
    alloc: fn(u64) -> *u8
    free: fn(*u8, u64)

# Kernel provides:
pub fn kernel_allocator() -> Allocator
    Allocator {
        alloc: kalloc,
        free: kfree_sized
    }

# Userspace provides:
pub fn user_allocator() -> Allocator
    Allocator {
        alloc: mmap_alloc,
        free: munmap_free
    }
```

## File Descriptors

The kernel needs to track open files:

```ritz
# kernel/src/fs/fd.ritz
pub struct FileDescriptor
    inode: u64           # Or BlobId for Goliath
    position: u64        # Current read/write offset
    flags: u32           # O_RDONLY, O_WRONLY, etc.
    refcount: i32

# Per-process file descriptor table
pub struct FdTable
    fds: [64]FileDescriptor
    count: i32
```

## Syscalls

New syscalls for filesystem:

| # | Name | Description |
|---|------|-------------|
| 10 | sys_open | Open file |
| 11 | sys_close | Close file descriptor |
| 12 | sys_read | Read from file |
| 13 | sys_write | Write to file |
| 14 | sys_lseek | Seek in file |
| 15 | sys_stat | Get file info |
| 16 | sys_mkdir | Create directory |
| 17 | sys_readdir | List directory |

## Testing Strategy

1. Unit tests in Goliath project (host mode)
2. Kernel integration tests in QEMU:
   - Load test blobs into KBlobStore
   - Verify read/write operations
   - Test VFS mount/unmount

## Dependencies

- [x] Kernel heap (`kalloc`/`kfree`)
- [x] VirtIO block driver
- [ ] Kernel blob store (`kblob`)
- [ ] VFS abstraction
- [ ] File descriptor management
- [ ] Syscall handlers

## Timeline

| Phase | Work | Estimate |
|-------|------|----------|
| 1 | Kernel blob store | 2-3 hours |
| 2 | VFS abstraction | 2-3 hours |
| 3 | Initramfs loading | 3-4 hours |
| 4 | Ring 2 service | 4-6 hours |

Total: ~12-16 hours of focused work
