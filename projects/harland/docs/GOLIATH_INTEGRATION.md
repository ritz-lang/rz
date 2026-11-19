# Goliath in the Harland kernel

The kernel's filesystem **is goliath** (`projects/goliath`), the same code
goliath's Linux tests run. Until AGAST #1881 this file planned, and the kernel
carried, ports of it (`fs/kblob`, `fs/kpath`, `fs/kdir_entry`,
`fs/knamespace`, plus a copy of cryptosec's SHA-256 in `lib/sha256.ritz`),
because goliath and cryptosec imported the hosted ritzlib (`ritzlib.sys`).
The forks drifted: goliath lost nested writes (LARB v4 M13) that the kernel
port had fixed, and the kernel kept a second on-disk format (`HARBLOB`) that
was never restored at boot. #1881 removed all of them.

## How the kernel binds goliath

`kernel/src/fs/kfs.ritz` is the only kernel-specific filesystem code:

| goliath needs | the kernel gives it |
|---------------|---------------------|
| `goliath.alloc.Allocator` (memory for blobs and buffers) | `kalloc` / `kfree` |
| `goliath.block_store.BlockDevice` (512-byte sectors) | the second virtio-blk device (`virtio_blk_read` / `virtio_blk_write`) |
| ritzlib core's platform hooks (`ritz_platform_page_map` / `_unmap` / `_fatal`) | `kernel/src/platform.ritz`: the kernel heap, and a panic |

It also maps goliath's `ErrorCode`s to the `Errno`s syscalls return, and
keeps the one global `Namespace` (`kfs_get`). Syscalls, the initramfs loader
and exec call goliath's `namespace_*` through it.

## Boot order

1. `virtio_blk_init_nth(1)`: the storage disk, if there is one.
2. `kfs_init(storage)`: restore the namespace from the disk's goliath image
   (`block_store_load`); a blank disk, or none, starts an empty tree.
3. `kfs_record_boot()`: count this boot in `/var/boots` and save the image
   (`block_store_save`). The log says
   `[OK] Persistent storage (goliath image: boot N, M blobs)`.
4. The initramfs loads on top, so the saved image holds what was written,
   not the boot binaries.

`tools/test_tier1_boot.sh` boots the GRUB image twice on one blank qcow2
storage disk and requires `boot 1`, then `boot 2`.

## One on-disk format

goliath's image (`goliath.image`) is the only format: in a host file
(`goliath.file_store`) or behind two crash-safe slot headers on a block device
(`goliath.block_store`, "GOLIATHB"). Only live blobs are written, so deleting a
file frees its space at the next save. The initramfs is still a TAR, read
once at boot.

## Open files and GC

goliath frees a blob when nothing references it (refcounts, #1881). An open
fd keeps a pointer to its file's bytes, so `sys_open` holds the blob
(`namespace_hold`) and the last close drops it (`namespace_unhold`). A rewrite
or delete of the path then can't free the bytes under a reader.

## Not done yet

- Nothing saves after boot: files written at run time persist only if a later
  boot's save includes them. A `sync` syscall, or a save on close, is
  follow-up work.
- Saves write the whole namespace. Once run-time saves exist, they will also
  write the initramfs binaries.
