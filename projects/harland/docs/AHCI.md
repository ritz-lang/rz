# AHCI: SATA disks behind the block interface

| | |
|---|---|
| Epic | AGAST #4861 (parent M2.4, #1842) |
| Status | Design. Break-down of #4861; the child tickets are listed at the end |
| First hardware | ASRock X99M Extreme4, Intel SATA at 00:1f.2 (`docs/hardware/asrock-x99m-extreme4/`) |
| First CI | QEMU q35's built-in `ich9-ahci` [8086:2922] at 00:1f.2 |

## Summary

Harland drives SATA disks through an AHCI host bus adapter (HBA), as block
devices beside virtio-blk and NVMe. The driver runs **in the kernel**, behind
the block interface in `kernel/src/drivers/virtio/blk.ritz` that the kernel
filesystem (`fs/kfs.ritz`, goliath) and the initramfs loader already use. It
does not move to a CPL-3 process under D8: no block driver has, and the block
interface's only consumer is the kernel (see "Where it runs").

A controller in **RAID mode** (class 01:04, the X99's state today) is not
driven. Harland logs it and leaves it exactly as the firmware left it. Its
disks do not appear (see "RAID-mode controllers").

The epic is done when a q35 boot with an `ich9-ahci` disk reads and writes
it through the block layer and a second boot finds the first boot's data,
and Aaron has confirmed the same on the X99 with the firmware set to AHCI.

## What exists

- **Block interface.** `drivers/virtio/blk.ritz` is the kernel's block
  interface despite its name. `virtio_blk_init_nth(n)` hands out block device
  `n`: the virtio disks first, then NVMe namespaces (`blk_init_nvme`, #1850)
  in PCI and namespace order. A `VirtioBlkDevice` carries `capacity` in
  512-byte sectors and, for NVMe, a non-null `nvme` pointer;
  `virtio_blk_rw` dispatches on that pointer. Callers speak 512-byte sectors
  and pass a kernel buffer.
- **Consumers.** `fs/kfs.ritz` binds goliath's `BlockDevice` to
  `virtio_blk_read` / `virtio_blk_write` on block device
  `STORAGE_BLK_INDEX` = 1 (`main.ritz`); `fs/initramfs.ritz` reads a TAR from
  block device 0 when the ESP or GRUB gave no initramfs. Both are in the
  kernel.
- **NVMe** (`drivers/nvme/nvme.ritz`) is the model to copy: probe early and
  polled with IF=0, bounce pages from `pmm_alloc_page` reached through the
  physmap, a TSC deadline on every command, a per-queue `busy` owner and the
  kernel wait queue (`proc/waitq.ritz`) once interrupts are up, and
  512-byte-sector translation at the interface.
- **Interrupts.** `drivers/msix.ritz` programs MSI-X only, through interrupt
  remapping when it is on (`ir_set`, `ir_msi_addr`, `ir_msi_data`). There is
  **no plain MSI** support. INTx is not used by any storage driver.
- **IOMMU.** On a translating boot (#4723) `vtd_dma_init` gives every
  requester on a segment an identity domain over all RAM before setting TE,
  so in-kernel bus masters (virtio-blk, NVMe) keep working. An AHCI HBA gets
  the same, with no new code.
- **Persistence check.** `tools/test_tier1_boot.sh` boots the same storage
  disk twice and checks `/var/boots` went from 1 to 2 (`persisted ... 1`,
  `persisted ... 2`). `tools/test_nvme_boot.sh` is the NVMe-only boot with a
  patterned data disk. The AHCI boot test copies both.

## The hardware

### QEMU q35

`ich9-ahci` is part of q35, at 00:1f.2, [8086:2922], class 01:06:01, 6
ports, ABAR in BAR5. It offers a single-message MSI capability (no MSI-X),
sets `CAP.S64A` (64-bit DMA) and `CAP.SNCQ`. Disks attach with
`-drive file=<img>,if=none,id=dN -device ide-hd,drive=dN,bus=ide.<port>`.

Every q35 boot already has this controller with its ports empty, so every
existing q35 test runs the probe. An empty controller must cost the boot
well under a second and log one line.

### X99 (from `hwinv/pci.bin`, decoded for this doc)

| | |
|---|---|
| Function | 00:1f.2, [8086:2822], class **01:04:00** (RAID), subsystem 1849:2822 |
| ABAR | BAR5 = 0xfb236000 (BAR0-4 are the legacy I/O ports) |
| Capabilities | MSI at 0x80 (message control 0x0000: 1 message, 32-bit address), PM at 0x70, SATA config at 0xa8. No MSI-X |
| `MAP` (0x90) | 0xa0: SATA mode select = RAID |
| `PCS` (0x92) | 0x8303: ports 0 and 1 enabled and a device present on each |
| Interrupt pin | INTA |

So the X99 has two SATA disks, on ports 0 and 1. With the firmware's SATA
mode set to AHCI the function becomes class 01:06:01 with a different device
ID ([8086:8d02], the C610/X99 AHCI ID); the driver matches the class, not the
ID, so it needs no ID table. There is no sSATA controller on this board's
inventory.

## Where it runs (D8)

**Decision: the AHCI driver runs in the kernel, at CPL 0, like virtio-blk and
NVMe.** D8 (`RING1_DRIVER.md`) decides that a driver *moved out of the
kernel* runs at CPL 3, in its own PML4, with its DMA in a translated IOMMU
domain and its authority from capabilities. It does not require every driver
to move, and none of the block drivers has. The reasons AHCI stays with them:

1. **The consumer is the kernel.** goliath (`fs/kfs.ritz`) and the initramfs
   loader call the block interface directly. A CPL-3 AHCI driver needs a
   block request ring between the kernel and the driver process, which does
   not exist. Building it is the block equivalent of the frame rings
   (`RING1_DRIVER.md` §6), and it should move all three block drivers at
   once, not one of them.
2. **The D9 measurement.** #4768 measured about 300 µs added per ICMP echo
   with the driver in a separate CPL-3 process, about half of it from
   address-space switches. Putting a driver at CPL 3 while its only consumer
   stays in the kernel pays a switch pair on every disk request for no
   isolation the kernel consumer can use.
3. **The IOMMU rule.** No driver DMA without a translated domain. QEMU CI
   boots without an IOMMU by default, so a CPL-3 AHCI driver could not run
   on the CI boot that the epic's "done when" names.

When the block drivers do move (a block-ring design, not filed here), AHCI
moves with virtio-blk and NVMe and gets the grants `RING1_DRIVER.md`
describes: `CAP_TYPE_MMIO` for the ABAR, `CAP_TYPE_IRQ` for its MSI, and a
translated DMA domain. Nothing in this design makes that harder: the driver
keeps its hardware state (command lists, FIS areas, bounce pages) per port
and touches the kernel only through the block interface, the PMM, MSI setup
and the wait queue.

## The block interface

AHCI disks are block devices after the virtio disks and the NVMe namespaces:
block device `n` is AHCI disk `n - virtio_count - nvme_count`, in PCI order
and then port order. `VirtioBlkDevice` gains an `ahci: *AhciDisk` pointer
beside `nvme`; `virtio_blk_rw` dispatches on it the same way. `capacity` is
in 512-byte sectors. Nothing above the interface changes: kfs, initramfs and
goliath see one more kind of disk. Renaming `VirtioBlkDevice` to a neutral
name is not part of this epic.

`MAX_BLK_DEVICES` stays 4: the CI boot uses two AHCI disks and the X99 has
two.

## Driver design

Source: `kernel/src/drivers/ahci/` (registers and FIS layouts in one file,
the HBA and port logic in another), host-testable pieces (IDENTIFY parsing,
FIS and PRDT encoding) under `projects/harland/test/` like `test_dma.ritz`.

### Probe and HBA init

Run from the same place as `nvme_probe`, early, with IF=0, polled.

1. Match every function with class 01, subclass 06, prog-if 01. A function
   with class 01:04 is handled by "RAID-mode controllers" and nothing else
   here runs.
2. Map BAR5 (ABAR) uncached with `vmm_map_mmio`, enable memory space and bus
   master, set INTx-disable in the command register.
3. Set `GHC.AE`. Read `CAP`, `CAP2`, `PI` (ports implemented) and `VS`.
4. **BIOS/OS handoff.** If `CAP2.BOH` is set: set `BOHC.OOS`, wait up to
   25 ms for `BOHC.BOS` to clear, and if `BOHC.BB` is set by then, wait up
   to 2 s more (AHCI 1.3.1 §10.6.3). A firmware that keeps ownership is
   logged and the controller is not driven. q35 and Intel PCH HBAs normally
   clear `BOH`; the path is written to the spec and covered by a host test
   of the sequence, not by CI.
5. **Quiesce what the firmware left running.** OVMF's and AMI's UEFI AHCI
   drivers leave ports started, with command lists and FIS areas in
   boot-services memory the PMM now owns. For every port in `PI`: clear
   `PxCMD.ST`, wait for `PxCMD.CR` to clear (500 ms), clear `PxCMD.FRE`,
   wait for `PxCMD.FR` to clear (500 ms). Then reset the HBA (`GHC.HR`, wait
   up to 1 s for it to clear) and set `GHC.AE` again.
6. **DMA width.** If `CAP.S64A` is clear every DMA page must be below 4 GiB.
   `pmm_alloc_page` searches up from low memory, so at probe time it gives
   low pages; the driver checks each address and refuses the controller (one
   log line) if one is not below 4 GiB. Both q35 and the X99 set `S64A`.

### Ports and devices

For each port in `PI`, with **one shared deadline** for all of them (1 s
from the HBA reset, so six empty q35 ports cost one wait, not six):

1. Give the port its DMA memory: one page, holding the command list at 0
   (32 headers x 32 B, 1 KiB aligned), the received-FIS area at 1024
   (256 B aligned) and command table 0 at 2048 (128 B aligned: the 64 B
   command FIS, ATAPI area, then the PRDT). Write `PxCLB`/`PxCLBU` and
   `PxFB`/`PxFBU`, set `PxCMD.FRE`.
2. If `CAP.SSS` (staggered spin-up), set `PxCMD.SUD`. Clear `PxSERR`
   (write all ones) and `PxIS`.
3. Wait (shared deadline) for `PxSSTS.DET` = 3 (device present, PHY up).
   A port that never gets there is empty: no log line per empty port, one
   summary line per controller.
4. Wait for `PxTFD` BSY and DRQ to clear, then read `PxSIG`. 0x00000101 is
   an ATA disk and is driven. ATAPI (0xEB140101), port multipliers
   (0x96690101) and SEMB are out of scope: logged by kind and skipped.
5. Set `PxCMD.ST`. Send **IDENTIFY DEVICE** (0xEC) as a PIO-in command
   through slot 0 with a one-entry PRDT on a bounce page.
6. From the 256 IDENTIFY words: model (27-46, byte-swapped pairs), serial
   (10-19), LBA48 support (83 bit 10, required), user capacity (100-103),
   logical sector size (106 bit 12 and 117-118; 512 B required: 4Kn
   drives are logged and skipped, 512e drives are fine), write cache
   enabled (85 bit 5), NCQ (76 bit 8, recorded only).
7. Log `[ahci] <bdf> port <p>: <model> <serial>, <sectors> sectors, 512-byte
   sectors[, write cache]`.

### Commands

One command in flight per port, in slot 0, owned by a per-port `busy` flag
as NVMe's queues are; a second caller waits on the kernel wait queue. NCQ is
not used.

- **Read**: READ DMA EXT (0x25). **Write**: WRITE DMA EXT (0x35). Both
  48-bit LBA in a Register H2D FIS (type 0x27, C bit set, device 0x40), at
  most 65536 sectors by the ATA count, and in practice
  `AHCI_BOUNCE_PAGES` pages: longer requests split.
- **PRDT**: one entry per 4 KiB bounce page (`DBC` = 4095, `I` clear except
  on the last entry). Bounce pages need not be contiguous. Data is copied
  between the caller's buffer and the bounce pages, as in NVMe.
- **Flush**: when IDENTIFY reports the write cache enabled, each block-layer
  write ends with FLUSH CACHE EXT (0xEA) before it returns. The block
  interface has no flush call, and goliath's save is a handful of writes,
  so this costs little and means a power-off after `kfs_save` cannot lose
  the image in the drive's cache. The trade-off is write latency; a
  block-layer flush operation (which NVMe would also want) replaces it if
  writes become hot.
- **Issue**: write the command header (CFL = 5, `W` for writes, PRDTL),
  clear `PxIS`, set bit 0 of `PxCI`.
- **Completion**: `PxCI` bit 0 clears and `PxTFD.STS.ERR` is clear. The TSC
  deadline is 10 s (spin-up from standby can take several).
- **Error or timeout** (`PxIS.TFES`, `PxTFD` ERR, or the deadline): stop the
  port (`ST` clear, wait `CR` clear: after that the HBA does no more DMA for
  it, so the bounce pages are free again, the lesson of #4139), clear
  `PxSERR` and `PxIS`, perform a COMRESET if `PxTFD` is still BSY or DRQ,
  restart the port, return -EIO. A port that fails its restart is marked
  dead and every later request on it returns -EIO at once.

### Interrupts

Polled first, then **MSI**, single message, once the APIC is up:

- `drivers/msix.ritz` gains plain MSI (capability 05h): find the
  capability, program address and data (32- or 64-bit per message control
  bit 7), through interrupt remapping when it is on (`ir_set` with the
  function's source ID, `ir_msi_addr`/`ir_msi_data`), enable with one
  message (`MME` = 0). The vector comes from `msix_vector_alloc` and
  dispatches through `msix_dispatch`, so `irq_wait_vector`, the wait queue
  and the counters work unchanged.
- The HBA has one vector for all ports. `PxIE` enables `DHRS` (D2H register
  FIS), `PSS` (PIO setup, for IDENTIFY), `TFES` and the error bits. The
  handler path is NVMe's: a command issued with IF=1 parks on the wait
  queue until the vector fires, then checks `PxCI`; `PxCI` stays the ground
  truth and a stale interrupt completes nothing. `IS` (global) and `PxIS`
  are cleared, port first.
- A controller with no MSI capability stays polled. INTx is not used.

## RAID-mode controllers

**What harland does with a SATA controller in RAID mode (class 01:04, such as
the X99's [8086:2822]): nothing, and it says so.** At the probe the driver
logs one line:

```
[ahci] 00:1f.2 [8086:2822] is a RAID-mode SATA controller (class 01:04): not driven. Set SATA mode to AHCI in firmware setup.
```

It does not map the BAR, change the command register, reset the HBA or
touch a port. The disks behind it are not block devices, and the boot goes
on (#4335: a storage controller harland cannot use must not stop init).

Why not bind it by ID, as Linux's `ahci` does for many Intel RAID IDs: the
register interface is AHCI, but the disks may be members of an Intel RST
(IMSM) volume whose metadata sits at the end of each disk. A RAID-1 member
written as a raw disk silently diverges from its mirror; a RAID-0 member is
a stripe, not a filesystem. Telling a pass-through disk from an array member
means parsing IMSM metadata, which is RAID support and out of scope. The
safe and honest behaviour is to leave it alone and say how to fix it.

A RAID-mode function with a non-Intel vendor is treated the same way: class
01:04 is never driven by this driver.

## Storage safety on real hardware

`kfs_init` treats a disk without a goliath image (`block_store_load` returns
`NotFound`) as blank and writes its image there on the first save. Block
device 1 is the storage disk. On the X99 with the firmware in AHCI mode and
no virtio or NVMe disks, block device 1 is **the second SATA disk**, which
holds whatever Aaron has on it. The first boot would overwrite its first
sectors.

So before the X99 boot, kfs only claims a disk that **already holds a
goliath image, or is blank** (its first 64 sectors, where the slot headers
go, are all zero). Any other disk is logged
(`kfs: block device 1 holds data that is not a goliath image; not using it`)
and the namespace runs without persistent storage. A `storage-format` boot
option (an ESP marker file, like `net-selftest`, and a GRUB cmdline word)
overrides that. The CI boot scripts whose data disks carry a sector pattern
(`test_nvme_boot.sh`, the AHCI boot test) set the option. The guard is
generic: it protects the Acer's and the ThinkPad's NVMe disks too.

## Tests

- **Host tests** (`projects/harland/test/`): IDENTIFY parsing (model and
  serial byte order, LBA48 capacity, sector size, write cache), H2D FIS
  encoding for READ/WRITE DMA EXT and FLUSH, PRDT building across a split,
  the BIOS-handoff sequence against a fake register file, and the
  storage-claim rule (image, blank, foreign, foreign with `storage-format`).
- **`tools/test_ahci_boot.sh`**, in CI beside `test_nvme_boot.sh`: q35
  under OVMF, no virtio-blk and no NVMe, two `ide-hd` disks on `ide.0`
  (root: the initramfs TAR) and `ide.1` (data: 4 MiB with a known sector
  pattern). It passes only if:
  - both disks log IDENTIFY with the expected sector counts;
  - the FNV-1a of a multi-page read of the data disk matches the pattern
    the script wrote (read path, split requests);
  - init's Tier-1 suite passes with the initramfs read from AHCI;
  - persistent storage comes up on the data disk (`/var/boots` = 1), and a
    second boot of the same disks reports `/var/boots` = 2 (the data
    survives a reboot), with the sectors around the image still holding
    the pattern;
  - once MSI is in, the log shows AHCI commands that waited on the vector
    and interrupts counted, on both an untranslated boot and an
    `intel-iommu,intremap=on` boot (interrupt remapping);
  - no exception.
- **Existing q35 boots** prove the empty-controller path: they must not get
  slower by more than the shared port deadline, and must log the one
  summary line.
- **X99**, by Aaron: firmware SATA mode set to AHCI, a scratch or blank disk
  as the second SATA disk (or the guard above confirmed on a disk with
  data), boot from the stick, both disks identified, the storage disk
  persisted across a reboot. Before the firmware switch, the RAID-mode log
  line is the expected result.

## Risks

- **DMA by the firmware's driver before the HBA reset.** Until step 5 of the
  probe, a port the firmware left running can DMA a received FIS into memory
  the PMM has already reused. NVMe has the same window. The probe runs early
  and quiesces first; the window is the time between PMM init and the probe.
- **Real-drive timing.** QEMU's PHY is up at once and its disks never spin.
  A real drive can take seconds after COMRESET and longer from standby. The
  shared 1 s port deadline may need raising on the X99; the X99 ticket owns
  that tuning.
- **Write cache and power-off.** Covered by flushing each write when the
  cache is on. NVMe's volatile write cache has the same exposure and no
  flush today.
- **Wrong disk.** Covered by the storage-claim guard. Without it the X99
  boot is destructive.

## Out of scope

ATAPI and optical drives, port multipliers, hot-plug, Intel RST and any
RAID, TRIM, NCQ (recorded from IDENTIFY, not used), 4Kn drives, a CPL-3 AHCI
driver (moves with the other block drivers), multiple commands in flight per
port.

## Child tickets

Filed under #4861. 1 and 4 can start at once:

1. **#4882 AHCI HBA init, port detection and IDENTIFY (polled), RAID-mode refusal.**
   Probe, handoff, quiesce and reset, ports with the shared deadline,
   IDENTIFY and its log line, the RAID-mode log line, host tests, and
   `tools/test_ahci_boot.sh` checking IDENTIFY on two q35 disks, in CI.
2. **#4884 AHCI read/write DMA behind the block interface, persistence across a
   reboot.** Depends on 1. READ/WRITE DMA EXT, PRDT bounce pages, split
   requests, FLUSH CACHE EXT, error and timeout recovery, the `ahci` field
   in `VirtioBlkDevice` and block-device numbering after NVMe. Extends the
   boot test to the pattern read, the initramfs from AHCI, Tier-1, and the
   second boot's `/var/boots` = 2. This is the epic's CI "done when".
3. **#4885 Plain MSI in `drivers/msix.ritz`, and AHCI completions on it.** Depends
   on 2. Single-message MSI with interrupt remapping; AHCI waits on the
   wait queue. The boot test checks waits and interrupts, plain and with
   `intel-iommu`.
4. **#4883 kfs never formats a foreign disk.** Independent of 1-3. The
   storage-claim rule and the `storage-format` boot option; the patterned
   CI boots set it.
5. **#4886 X99 AHCI bring-up, confirmed by Aaron.** Depends on 2, 3 and 4.
   Firmware set to AHCI, real-drive timing fixes, the X99 README's SATA row
   updated from "gap" to the driver.
