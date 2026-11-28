# Transactional replacement and storage-failure recovery (AGAST #4835)

| Status | Implemented (#4835). OK'd by the coordinator with the four conditions below |
|---|---|

Code: `fs/persist.ritz` (the gate, plain and durable commits) and
`fs/open_plan.ritz` (when O_CREAT creates, O_EXCL), both pure and tested by
`test/test_persist.ritz`, bound to the kernel by `fs/kfs.ritz`;
`fs/syscall.ritz` (open and close); goliath's `namespace_fork` /
`namespace_adopt` / `namespace_drop` and the flushes in `block_store_save`.

## Conditions of the OK

1. **Real-disk durability.** The old-or-new guarantee can't rest on
   write-through virtio-blk alone: the laptops and the X99 boot NVMe and
   AHCI disks with write-back caches. `block_store_save` orders image data,
   device flush, slot header, device flush, through goliath's block
   interface (`BlockDevice.flush`), and a failed flush fails the save before
   the header is written. The kernel's flush is `virtio_blk_flush`: NVMe
   sends Flush (opcode 00h, `nvme_ns_flush`, which the driver never issued
   before); AHCI already follows every write with FLUSH CACHE EXT when the
   write cache is on (#4884); virtio-blk negotiates no `VIRTIO_BLK_F_FLUSH`,
   so it runs write-through (virtio 1.x §5.2.6.2). Tests: goliath's
   `test_block_store_save_flushes_image_then_header` and
   `test_block_store_failed_flush_keeps_previous` (a RAM device recording
   the call order), and `tools/test_nvme_boot.sh` requires each namespace's
   boot-time Flush to complete.
2. **Deferred create and O_EXCL.** `O_SYNC | O_CREAT | O_EXCL` still fails
   with EEXIST at the open when the path exists (O_EXCL is new to Harland's
   open, and holds with or without O_SYNC). A deferred exclusive create
   checks again at its close and fails EEXIST if the path appeared since.
   Two `O_SYNC` creates of one missing path, without O_EXCL, are
   last-close-wins. Tests: `test_open_plan`,
   `test_deferred_exclusive_create_fails_if_the_path_appeared`,
   `test_two_deferred_creates_last_close_wins`.
3. **The gate at power-off.** The power-off save (init's exit, the ACPI
   power-off, and each process's exit) is `kfs_flush_pending`: it takes the
   gate like any save, so if a parked caller holds it, it waits for that
   caller, then saves whatever is still pending. It never skips the save
   and never writes beside another. Tests:
   `test_power_off_waits_for_a_parked_save`,
   `test_power_off_saves_what_a_parked_commit_left`, beside
   `test_contended_gate_second_save_waits`.
4. **Suite cap.** The ritz0 pytest count is at its cap, and
   `projects/ritz/tools/test_harland_*.py` count toward it, so the kernel
   host tests are harland ritzunit (`test/test_persist.ritz`), not pytest:
   net 0 new pytest cases.

## The problem today

A close of a written `/var` fd (`fs_flush_write_buffer` → `kfs_commit`)
writes two copies: the runtime tree (`g_kfs_ns`, serves `readdir /`), then
the persistent subtree (`g_kfs_pns`, serves every `/var` read and is what
`kfs_save` writes to disk). After that, a debounced `kfs_save` writes the
image. Each of the three steps can fail on its own:

| Fails | Running system reads | Next boot reads |
|---|---|---|
| persistent-subtree write (`fault-persist`) | old (pns); the runtime copy is new | old |
| image save (`fault-sync`, EIO, NoSpc) | new | old (indefinitely, until a later save succeeds) |

So a reader and a reboot can disagree, and nothing says which copy wins.

A second gap: an NVMe or AHCI storage device (kfs's block device 1 can be
either: `drivers/virtio/blk.ritz` hands them out behind the same
interface) parks the caller mid-request
(`irq_wait_vector(..., may_park=true)`), so another process can run during
a save. A second `kfs_save` can then write the same non-current slot
concurrently, and a commit can change `g_kfs_pns` while the save
serializes it.

What already holds: the on-disk image is crash-safe (goliath
`block_store.ritz`, #4226). It has two slot headers and never overwrites
the image in use, and load takes the highest valid generation. A save cut
short at any sector leaves the previous image loadable. virtio-blk
negotiates no `VIRTIO_BLK_F_FLUSH`, so QEMU runs the disk write-through:
each completed write is durable, and the header-after-image order holds.

## Design

### 1. One copy of `/var`

`/var` lives only in the persistent subtree. The runtime tree keeps an
empty `/var` directory as the mount point, so `readdir /` lists it, but no
entries below it. `kfs_commit` and `kfs_persist_mkdir` write only the
namespace `kfs_ns_for` picks. Without a claimed storage device /var is not
mounted: the runtime tree has no `/var`, so a /var path is missing there,
as it was before (`kfs_is_durable`). A `/var` commit is then one namespace commit:
goliath's copy-on-write root swap (`commit`), which no reader can observe
half done. This removes the first row of the table, and `/var` costs half
the RAM.

Which tree a path is in is `fs/route.ritz`'s (`route`), and everything
outside `/var` is the runtime tree: RAM, never saved. `/tmp` is its scratch
directory (AGAST #4957): `kfs_init` makes it, mode 01777, every process gets
`TMPDIR=/tmp` in the environment the kernel passes in RDX, and a save never
carries it, so it is empty at every boot. `unlink` (87) and `rmdir` (84)
remove from whichever tree the path routes to; under `/var` a remove is a
plain commit (`persist_remove`), owed a save like a close's.

### 2. The save gate: one writer of the persistent subtree

A kernel flag, `g_kfs_gate`. It is held across every persistent-subtree
change and every image save: `kfs_commit` and `kfs_persist_mkdir` under
`/var`, `kfs_save`, `kfs_save_later`, and the power-off save. A caller that
finds the gate held parks on the interrupt wait queue (`waitq_park`) and
re-checks when woken; the release wakes it (`waitq_wake_irq`). That only
happens on a storage driver that parks; virtio-blk holds the CPU, so it
never contends. A caller that can't park (boot, an AP) and finds the gate
held gets EAGAIN rather than spin on a holder that can't run. The kernel is
not preemptible and the BSP owns this state (SMP_USER.md §2), so the flag
needs no atomic. This closes the concurrent-save gap. A plain commit sets
`pending`; only a save that succeeds clears it.

### 3. Durable commit: `O_SYNC` (Linux's 04010000)

Plain closes stay as they are: they publish at once and save debounced
(#4321's hundred-file case). A `/var` fd opened with `O_SYNC` makes its
last close a transaction: **prepare, persist, publish**. All three steps
run under the gate.

1. **Prepare:** `cand = namespace_fork(pns)` holds the live root, and the
   file is committed into `cand`. A failure here (NoSpc, NoMem) drops `cand`.
   Nothing changed anywhere, and close returns the Errno.
2. **Persist:** `block_store_save(dev, cand)`. On failure, drop `cand`, keep
   `pending` as it was, and return EIO (or NoSpc). The running
   system never saw the new bytes, and the disk still loads the previous
   generation: **old everywhere**.
3. **Publish:** `namespace_adopt(pns, cand)`, a root swap that can't fail.
   Under the gate no one else changed `pns`, so `cand` is the live root plus
   exactly this file. It also carries every debounced change that was
   pending, so `pending` is cleared. **New everywhere**.

An `O_SYNC | O_CREAT` open of a missing `/var` path defers the create to
that close: the fd starts empty with the open's mode, and the close's
transaction creates the file and its bytes together. A failed save then
leaves no file, not an empty one. (Until the close, `stat` of the path is
ENOENT. That differs from Linux, but only for `O_SYNC` creates.) An
`O_SYNC` close at process exit takes the same path, except that a deferred
create the process exits from without writing a byte creates nothing: the
"old" state of a path that had no file, as the exit rule for O_TRUNC
already is. Only a writable open defers its create (a read-only fd
commits nothing at its close). `O_SYNC` on a RAM-only path is a plain
close; there is nothing to persist.

New goliath API, with goliath tests: `namespace_fork`, a namespace sharing
the store whose root is held; `namespace_adopt`, moving the fork's root
into the live namespace and releasing the old root; and `namespace_drop`,
releasing a fork.

### 4. Defined recovery after a storage failure

- **`O_SYNC` close:** the file is old in RAM and on disk. Close returns the
  Errno; the caller keeps its data and may retry.
- **Plain `/var` close or mkdir:** published in RAM and pending. Every later
  save (debounced, `sync`, an `O_SYNC` transaction, power-off) writes it; a
  failed save leaves it pending. `sync` returns the save's Errno: Linux's
  page-cache-and-fsync contract.
- **Reboot after any failure or crash:** loads the highest valid generation,
  which is the last save that completed. No step of a save makes that image
  unloadable (#4226). A torn header fails its checksum.
- **Nothing is repaired at boot:** there is no journal to replay, because
  the image is whole or absent. `storage_claim` (#4883) still refuses a
  damaged or foreign disk rather than overwrite it.

### 5. Fault options, redefined

- `fault-persist`: the persistent subtree's commit fails with EIO (the
  prepare step, or a plain `/var` commit). Nothing changes anywhere.
- `fault-sync`: every image save fails with EIO (unchanged).

## Editor and contract suite

- `HarlandFiles` opens `O_WRONLY | O_CREAT | O_TRUNC | O_SYNC`, keeping its
  stat/mode checks (#4832, #4833). It drops the separate `sync()`, because
  the close is the durable commit. A close failure on `/var` becomes
  `Failed`: the file is unchanged. `Unpersisted` and its "live file may have
  changed" message stay Linux's, for a failed directory fsync.
- The target-neutral cases of `test/test_save.ritz` (#4820) move into a
  contract module (`src/platform/save_contract.ritz`) that runs against a `FileStore` on a real disk: round
  trips, final newline, large file, create, a second save checked against
  the first, permissions, three changed-underneath cases (changed, a new
  mtime at the same size, created underneath), and a failing storage that
  keeps the old file and the buffer dirty. Harland has no unlink, chmod or
  utimes: "deleted underneath" stays Linux-only, and the new-mtime case
  rewrites the same bytes there (every commit takes a new file-clock
  reading). Linux runs it under
  ritzunit as today. On Harland it is a user test binary, booted under QEMU
  in the existing `test_harland_console.sh` harness, once plain and once
  with `fault-sync` and `fault-persist`. The harness then reboots and checks
  that the image holds the old file. The Linux-only cases (temp-file
  naming, the fsync/rename order, short writes through `SaveIo`) stay
  Linux-only.

## Tests (written first)

- **goliath:** fork, commit, and drop leave the live tree and the refcounts
  unchanged; fork, commit, and adopt match a direct commit; a commit on the
  live namespace while a fork exists leaves the fork intact.
- **goliath:** `block_store_save` writes image, flush, header, flush, and a
  failed flush keeps the previous generation (condition 1).
- **Kernel host tests** (harland ritzunit, `test/test_persist.ritz`, against
  `fs/persist.ritz`), with a RAM block device that can fail on demand:
  - an `O_SYNC` close whose save fails: old bytes in `pns` and in the
    reloaded image;
  - an `O_SYNC` close whose save succeeds: new bytes in both, and a pending
    plain commit is cleared;
  - a deferred create plus a failed save: no file;
  - a plain close plus a failed save: new in RAM, old after reload, still
    pending, and the next good save makes them agree;
  - fault-sync and fault-persist fail a durable commit with the file old
    everywhere, and a plain commit or mkdir under fault-persist changes
    nothing;
  - O_EXCL at the open and at a deferred create's close, and two deferred
    creates (condition 2);
  - a contended gate: the second save waits rather than writing the same
    slot; the power-off save waits for a parked holder; a caller that can't
    park gets EAGAIN (condition 3).
  - `/var` having no entries in the runtime tree is kfs routing, not
    `fs/persist.ritz`: the QEMU boots cover it (every /var read in the
    console and contract sessions goes through it).
- **QEMU:** the boot gate's `/var/boots` count, the NVMe boot's Flush, plus
  the editor's contract binary and the fault boots above.
