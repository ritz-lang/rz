# Review of the Harland ring-1 driver and ring-2 network designs

This review covers the working-tree revisions of [RING1_DRIVER.md](RING1_DRIVER.md) and [RING2_NET.md](RING2_NET.md) after they absorbed [RING1_DRIVER_FEEDBACK.md](RING1_DRIVER_FEEDBACK.md) and [RING2_NET_FEEDBACK.md](RING2_NET_FEEDBACK.md). Those two reviews are now largely addressed. This one checks the drafts against the existing kernel, the Harland roadmap, and idiomatic Ritz, and against each other. Line numbers refer to the reviewed revisions.

Keep the ownership split. The driver owns the queues and the link record, the service owns the protocols and the lease, and apps use their own exchange. The findings below are about how the drafts fit the tree around them.

## Fit with the existing kernel

### 1. Use the capability system for driver and service authority

Harland already gates device access with capabilities. `cap/types.ritz` defines `CAP_TYPE_MEMORY`, `CAP_TYPE_IRQ`, `CAP_TYPE_MMIO` and `CAP_TYPE_SHM`, and `FbMap` refuses a caller without `CAP_TYPE_DISPLAY`. Ring 1 instead adds `Proc.driver: u8`, set only for the kernel's spawn of the fixed path `/bin/virtio-net`. Ring 2 then needs a second, unspecified mark for the process allowed to take the frame seat. [Capability types](../kernel/src/cap/types.ritz#L10) · [FbMap check](../kernel/src/syscall/runtime/framebuffer.ritz#L134) · [Driver mark](RING1_DRIVER.md#2-process-entry-and-the-driver-mark)

The alternatives section rejects capabilities because "a capability word is only as honest as every syscall that remembers to check it". That is equally true of `Proc.driver`, which every driver syscall must also check. The CPL choice and the authorization choice are independent. Keep CPL 1 for the driver and CPL 2 for the service, and authorize through capabilities.

- Express MMIO grants as `CAP_TYPE_MMIO` entries for the recorded windows, and the device wait as `CAP_TYPE_IRQ`. `DrvMmioMap` and `DrvIrqWait` then check a right on a handle, not a process-wide bit.
- Grant the frame-ring region, the app-exchange rings and the address page as `CAP_TYPE_SHM`. See item 2.
- Drop the hardcoded `/bin/virtio-net` path. The kernel grants the capabilities to the process it spawns for the device, which works unchanged for ENA, NVMe and the ring-2 service.
- Store the return CS/SS pair or the CPL in `Proc`, not a `driver` bit. A third CPL makes a boolean the wrong shape.

### 2. Give ring 0 a runtime grant path before ring 2 depends on it

Ring 1 withdraws shared memory: the region is "granted at spawn, not by a shm syscall". Ring 2 relies on a grant at runtime. "Ring 0 grants the shared pages" to ring-3 apps that attach after boot, and a restarted app gets "a new attachment". No spawn-time grant can serve an app that attaches later. Neither draft names the syscall, the capability, or the mapping window for an attachment. [Ring-1 OS table](RING1_DRIVER.md#6-portable-spsc-ring) · [App exchange](RING2_NET.md#ring-3-app-exchange)

Define one grant path, preferably `CAP_TYPE_SHM` with grant, map and revoke, and use it for the frame region too. The spawn-time grant then becomes the kernel exercising that path on the driver's behalf. Neither draft should reach the TCP milestone with two sharing mechanisms.

### 3. Syscall 60 contradicts the numbering policy

`numbers.ritz` records 4, 29, 32, 60 and 61 as free, and keeps them free for their Linux meanings. AGAST #4321 chose 162 for `Sync` specifically to avoid them. Ring 1 calls 60 and 61 "reserved" for `net_info` and `net_ping`. Key decision 8 says "4, 29, and 32 stay free for their Linux meanings" and drops 60 and 61 without discussion. Ring 2 repeats the reservation. [Header](../kernel/src/syscall/numbers.ritz#L15) · [Sync rationale](../kernel/src/syscall/numbers.ritz#L96) · [Key decision 8](RING1_DRIVER.md#key-decisions)

Put `NetInfo` in the new 220s group, beside `DrvRingKick`, and add the address-snapshot read there too (see item 11). If 60 is kept, overturn the policy explicitly and update the `numbers.ritz` comment in the same PR.

### 4. Name the userspace home and the shared virtio code

Userspace programs are built in `projects/indium` (`harland/ritz.toml`: "Userspace programs are in the indium project"). Ring 1 refers only to "an initramfs package". More importantly, `drivers/virtio/common.ritz` is shared with `blk.ritz` and `input.ritz`, which stay in the kernel, and it imports `klog`, `io` port I/O, `pmm`, `heap` and `vmm_map_mmio`. A CPL-1 binary cannot import any of those. [common.ritz imports](../kernel/src/drivers/virtio/common.ritz#L8)

Without a plan, the `vq_*` and `vio_*` code is copied into the driver. Factor the transport-independent virtqueue and feature-negotiation code into a leaf package on the `boot_abi` / `driver_abi` pattern, taking allocation and register access as parameters. The kernel's blk and input drivers and the ring-1 net driver then share it. Add that package and the indium binary to the PR 7 file list.

### 5. The PR 7 file list and the no-IOMMU path disagree

Section 9 and key decision 12 keep `virtio_net_init` on every boot without DMA translation, including today's QEMU self-test. The PR 7 file list still says `drivers/virtio/net.ritz` is "deleted or reduced to the status-reset and MSI-X mask". It has to stay whole. Say so, and state that both virtio-net owners are maintained for as long as untranslated boots are supported. [PR 7](RING1_DRIVER.md#pr-7-virtio-net-cutover-and-syscall-60)

### 6. Make QEMU's virtio-net actually use the vIOMMU, and run that boot in CI

Under QEMU, a virtio device bypasses an `intel-iommu` unless the device is created with `iommu_platform=on`. The driver must then negotiate `VIRTIO_F_ACCESS_PLATFORM` (feature bit 33). Without both, the device DMAs to guest-physical addresses, and the "domain walk" acceptance check passes while proving nothing. `intel-iommu` also requires the q35 machine, and `intremap=on` requires `kernel-irqchip=split`. [DMA domain](RING1_DRIVER.md#dma-domain)

- Specify the QEMU flags, and negotiate bit 33 in the ring-1 driver.
- Add an acceptance check that the device's DMA faults on an IOVA outside the domain. Seeing the framebuffer unmapped in the domain is not enough.
- Add the translating boot to `test_msix_boot.sh` as a second run in CI, in PR 5b or PR 7. As drafted, the default self-test keeps the in-kernel path, so nothing automated exercises the ring-1 driver.

### 7. Departure from the IPC model in ARCHITECTURE.md

ARCHITECTURE.md describes IPC as "the kernel flips page table bits … no data copying", with an app's buffer made readable to ring 2 per call. Both drafts use persistent shared SPSC rings instead. That is the better design, since it avoids per-message page-table edits and TLB shootdowns. Ring 2 already lists what it does not follow in NETWORK_DESIGN.md. Add this departure to that list, and to the ARCHITECTURE.md corrections in ring 1's PR 1. [ARCHITECTURE.md IPC](ARCHITECTURE.md#ipc-ring-buffers-zeusvalet-style)

## Ring 1: open items in the revised text

### 8. The quarantine has no mechanism

`vmm_free_pml4` frees every user leaf without `PTE_DEVICE`. The draft says pages whose reset or IOTLB invalidation did not complete are "not returned to the PMM" and are "appended to `dma_quarantine`". It also says `vmm_free_user_pt` frees "only the runs whose reset finished". Nothing in the exit path makes that conditional. Specify the step: before `vmm_free_pml4`, either unmap the quarantined leaves from the user tables or set `PTE_DEVICE` on them, then record the frames on the list. [Death path](RING1_DRIVER.md#driver-death) · [sys_exit_impl](../kernel/src/syscall/runtime/process.ritz#L337)

### 9. The seqlock needs fences in Ritz

Ritz atomics are `seq_cst` loads and stores (§18.5). The `NetInfo` bytes are plain memory. A `seq_cst` load does not stop earlier plain loads from moving after it, and a `seq_cst` store does not stop later plain stores from moving before it.

- Reader: the plain copy can sink below the second `atomic_load(link_seq)`, so a torn copy validates. Put `fence()` between the copy and the second load.
- Writer: the plain writes can rise above the odd `atomic_store`, so a reader sees new bytes under the old even generation. Put `fence()` right after the odd store.

This applies to the ring-2 address seqlock, which reuses the protocol. The frame ring is already correct: its plain accesses sit on the correct side of each atomic. Add `fence()` to the numbered steps in both drafts, and a host test with a deliberately reordered writer if one can be built. [Syscall 60](RING1_DRIVER.md#7-syscall-60) · [LANGUAGE_SPEC §18.5](../../ritz/docs/LANGUAGE_SPEC.md#185-atomics-and-fences)

### 10. The spawn handoff is not read-only

The layout table puts the spawn handoff at `0x0300..0x1000` on page 0, "kernel-written and not written by the driver". Section 8 calls the MSI-X indexes "a read-only word of the shared region". Page 0 also holds both `SpscCtrl` blocks and `NetInfo`, which the driver must write, so the page is mapped writable. Page-granular mapping cannot make part of it read-only. [Region layout](RING1_DRIVER.md#6-portable-spsc-ring)

State that the handoff is advisory. The kernel keeps the authoritative window records and MSI-X indexes in kernel memory, and `DrvMmioMap` resolves a window index against that copy. It never reads a page base back from the shared page. Otherwise a driver that overwrites the record maps arbitrary physical memory. Alternatively, move the handoff to its own page, mapped without `PTE_WRITABLE`, which grows the region by one page.

### 11. Nothing triggers a snapshot refresh after boot

The kernel snapshot of `NetInfo` is "sampled when pid 1 runs again" during cutover. Section 8 says the kernel "reads the shared page to refresh that snapshot", but no event triggers that refresh. A link that goes down or up after the self-test never reaches syscall 60 or the ring-2 service's "link snapshot generation" wake source. Name the trigger. Either the driver calls a publish syscall after it changes the record, or `DrvRingKick` takes a flag. The kernel then refreshes, and wakes the frame endpoint so ring 2's wait sees the new generation.

### 12. Smaller ring-1 items

- **Reset timeout.** The virtio reset is bounded by `VTD_TIMEOUT_US`, a private constant in `vtd.ritz`. Give the reset its own named bound. [vtd.ritz](../kernel/src/drivers/iommu/vtd.ritz#L54)
- **Full RX ring.** The driver spins until the timer preempts it. Before `sched_start`, nothing preempts. Call `Yield` (24), which exists, in the loop. [numbers.ritz](../kernel/src/syscall/numbers.ritz#L48)
- **Malformed occupancy.** An occupancy above 256 returns an error and does not advance `read_idx`, so the ring is wedged permanently. Treat it as a driver fault: kill the driver, which runs `driver_quiesce`.
- **The wait snippet's `return 1`.** It follows a "validate" step that can reject the slot. Say what a rejected slot returns.

## Ring 2: open items in the revised text

### 13. The service never parks on an idle link

The park condition requires "the TX ring has no free slot **and** the pending-TX queue is empty". On an idle link the TX ring has free slots, so the condition is false and the service never sleeps. The TX side is idle when the pending queue is empty, or when it is non-empty and the TX ring is full. Write the bullet as "the pending-TX queue is empty, or the TX ring has no free slot". [Service wait](RING2_NET.md#service-wait)

### 14. The attachment cap counts five apps, not six

The service is a process too. With init, the ring-1 driver and the service each holding a slot of `MAX_PROCS` (8), at most five apps attach. [App exchange](RING2_NET.md#ring-3-app-exchange)

### 15. Apps have no way to read the address snapshot

"An app that wants the lease reads the address snapshot." Syscall 60 is the link record only, and no syscall, number or mapping is given for the address snapshot. Add one, in the 220s group per item 3, with the same `Errno.NoDev`-before-publish rule as syscall 60. Alternatively, map the kernel snapshot read-only into each attached app.

### 16. "The kernel fails those requests" means the kernel parses app requests

When an app exits with requests pending, the draft has the kernel fail them. Failing a request means reading the slot layout, which the draft leaves unfrozen, and it conflicts with "ring 0 does not parse". The kernel should only mark the attachment closed and wake the service. The service drains and discards that attachment's requests. [App exchange](RING2_NET.md#ring-3-app-exchange)

### 17. The frame-seat handoff is circular as written

"The kernel holds both [roles] until the service has published a ready generation." If "ready generation" means a configured address record, the service cannot reach it: DHCP needs the frame seat the kernel is still holding. Define "ready" as a separate state of the service, published before DHCP. Also state what happens to the kernel's own lease at handoff. The service starts its own DHCP client, so the kernel's lease is either released with a DHCPRELEASE or handed over. [Frame seat](RING2_NET.md#frame-seat)

## Idiomatic Ritz

- **Atomics take pointers.** §18.5 defines `atomic_load(p)`. The consumer snippet's `atomic_load(write_idx)` should be `atomic_load(@ctrl.write_idx)`, and likewise for `read_idx`. [RX consumer](RING1_DRIVER.md#6-portable-spsc-ring)
- **`null`, not `0 as *NetDevice`.** The spec has `null`, which fits any pointer. The tree's casts are older style, so new code should not copy them. [net_stack_init sketch](RING1_DRIVER.md#8-virtio-net-move)
- **Cache-line alignment.** Under the No Concessions doctrine in AGENT.md, `SpscCtrl`'s `[56]u8` / `[60]u8` pads are C in Ritz clothing. Propose `[[align(64)]]` per field or per struct as a language change, or record why hand padding is acceptable for an ABI struct.
- **ABI layout.** `FrameDesc`, `SpscCtrl` and `NetInfo` are shared with Linux and Win64 ports. `[[repr_c]]` is a compile error (§17). State the guarantee the default layout gives, or use `[[packed]]` with explicit pads. Add a host test in `driver_abi` that asserts each `sizeof` and field offset against the layout table.
- **Tri-state returns.** `net_wait_rx` returns 1, 0 or -1. An enum, such as `Frame`, `Timeout` or `NoDriver`, reads better and cannot be confused with an errno.
- **Flags.** New globals such as `net_via_ring` and `driver_registered` should be `bool`. The cap table already uses `bool`, and the `u8` flags in `Proc` predate it.

## Suggested order

Items 1–3 change the ABI, so settle them before PR 4 adds numbers. Items 9 and 10 are correctness bugs in text the PRs will copy. Item 6 decides whether the cutover has any CI coverage. The rest can be folded in as the PRs are written.
