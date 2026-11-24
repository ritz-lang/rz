# Re-review of the Harland ring-1 and ring-2 designs

Reviewed [RING1_DRIVER.md](RING1_DRIVER.md) and [RING2_NET.md](RING2_NET.md) at `3d453d7f`. The drafts now require a translated DMA domain for the userspace driver, provide reset readback and quarantine, protect reserved windows from ordinary unmap, keep syscall return frames on the kernel stack, and address the earlier self-test scheduling failures. Ring 2 has a multi-source wait, bounded TX backlog, a distinct ready state, and a separate TCP milestone. The remaining blockers are where these contracts meet.

## Resolve before freezing the ABI

### 1. Give shared mappings an owner independent of either process

Ring 1 says the driver's PML4 owns the frame pages and frees them at driver exit. Ring 2 maps those same pages in a second PML4. Today `vmm_free_user_pt` frees every present RAM leaf without `PTE_DEVICE`, so neither teardown order is safe if both leaves use that rule. A service can also be suspended midway through a ring operation when the driver dies. Clearing the kernel's pointer does not resolve a saved userspace pointer.

Make the shared object own its backing pages. Track mappings separately, with explicit non-owning leaves and lifetime rules. Define detach, invalidation, wake, and reclaim in both death orders. Keep backing memory alive until every live mapping or in-flight operation has released it, or revoke those mappings and define the resulting fault behavior. Apply the same rules to app exchanges and duplicate `ShmMap` calls. Test driver-first and service-first exit, including a peer preempted while using the mapping. [Frame allocation](RING1_DRIVER.md#dma-domain) · [Share and wake rules](RING1_DRIVER.md#6-portable-spsc-ring) · [VMM free walk](../kernel/src/mm/vmm.ritz#L1022)

### 2. Specify what a capability grants, who can transfer it, and what revoke actually does

`CapGrant` currently copies an existing handle into another process, subject to its grant right. It does not create a region or deliver the handle to its new holder. `CapRevoke` removes a handle from the caller's table. It does not remove mappings, invalidate other copies, or close a peer attachment. The drafts rely on all of those missing operations.

Specify who creates and offers an attachment, how the app discovers or receives its handle, and whether device grants and publish rights may be transferred. Make `NetPublish` require an explicit publish right on the exact registered link or address object, bound to its designated publisher. A generic app-exchange SHM handle must confer no publish or frame-seat authority. Define what happens to already-mapped MMIO on revocation and who retains responsibility for quiescing the device. Where writer permissions matter, lay out producer-written and consumer-written words on separately protectable pages or describe the entire page as peer-writable and validate accordingly. The current ring-2 text assigns the whole control block to one writer and then has the other side write its read index. [Grant and revoke](../kernel/src/cap/syscall.ritz#L30) · [Device authority plan](RING1_DRIVER.md#pr-3b-capabilities-for-device-authority) · [Ring-2 app exchange](RING2_NET.md#ring-3-app-exchange)

### 3. Specify both directions of the wait and notification ABI

The ring-2 service can park while it has pending TX and the TX ring is full. Ring 1 never specifies waking the service when the driver releases TX space. It also only describes the kernel waking the driver for new TX. The service has SHM authority, while the named `DrvRingKick` requires an IRQ handle and wakes the RX consumer. Ring-3 apps similarly have no defined capability-scoped kick. The kernel's wait predicate also refers to the service's private pending queue.

Add a capability-scoped wait and notification contract that defines the target, event mask and deadline. Let the service declare interest in TX space when it has pending work. Specify publish-before-wake for both new data and newly available space. Cover driver invalidation as a distinct observed event and use kernel-owned change counters or object identities so a replacement publishing generation 2 cannot look like the previous instance. Test a TX-space-only wake with no incoming frames, app request and event wakes, and driver death while the service is parked. [Ring-1 kick](RING1_DRIVER.md#6-portable-spsc-ring) · [Ring-2 wait](RING2_NET.md#service-wait)

### 4. Make frame reset and remote process teardown explicit

The BSP scheduler can preempt the driver between copying a slot and committing its index. The service can then exit and reset both indexes, after which the driver resumes and publishes an index from the old ring state. Waking the driver does not prove that it has reached a safe point, and a plain index read cannot tell whether the driver is mid-slot. Require a pause and acknowledgement at a slot boundary before reset, or hand a replacement a fresh region with a new identity while retiring the old object.

The bad-occupancy path also asks the kernel consumer to kill the driver and the driver to cause service teardown. Harland currently has `process_kill_current`, which exits the calling process. Specify how a different process is marked for teardown, how it is prevented from resuming, and when its mappings and DMA resources are revoked. Until that exists, close the compromised endpoint and stop using it. A ring-validation handler must never exit pid 1 by calling the current-process helper. [Ring-1 occupancy handling](RING1_DRIVER.md#6-portable-spsc-ring) · [Current kill path](../kernel/src/syscall/runtime/process.ritz#L384) · [Ring-2 frame handoff](RING2_NET.md#frame-seat)

The occupancy check also needs an arithmetic contract. Ritz traps on integer overflow, so the literal `w - r > 256` can trap before it reaches the bad-ring branch when the peer supplies `w < r`. Choose checked monotonic counters with an explicit rollover policy, or deliberate modular arithmetic with a bounded distance check. Test backwards and near-wrap counters. [RX validation sketch](RING1_DRIVER.md#6-portable-spsc-ring)

## Resolve before the translated boot and service cutover

### 5. Design the IOMMU transition for the entire affected remapping unit

The private NIC domain is the right requirement. VT-d translation enable applies to a remapping unit, so PR 5b also needs a policy for its other requesters. The translating MSI-X test boots with virtio-blk and NVMe on the same platform, and the current virtio probe enables bus mastering before it discovers modern capabilities. Define how the kernel establishes contexts for the other devices that must keep performing DMA, preserves firmware-required mappings where applicable, and keeps the NIC blocked until the private context is live. Gate both queue-register grants and bus mastering on confirmed isolation, including requester aliases. Keep the existing storage and NIC assertions on the translating boot.

On partial `DrvDmaAlloc` failure, treat any IOVA already installed as potentially reachable even if the syscall never copied it out. Remove it and confirm invalidation before returning that backing page to the PMM, or quarantine it under the same rule as exit. Unify the two acceptance descriptions in the draft. Require a successful DMA into a granted page and a fault attributed to the NIC for an unmapped IOVA. A page-table walk alone is supplementary. [DMA allocation and domain](RING1_DRIVER.md#5-mmio-and-dma-syscalls) · [Current virtio probe](../kernel/src/drivers/virtio/common.ritz#L628) · [MSI-X boot fixture](../tools/test_msix_boot.sh#L171) · [Linux x86 IOMMU documentation](https://docs.kernel.org/arch/x86/iommu.html)

### 6. Make DHCP server selection state-dependent

The draft requires every OFFER, ACK, and NAK to name the server the client already selected. In SELECTING, receiving valid offers is how the client chooses the server. In REBINDING, a valid response may come from a different server. Spell out which states pin the selected server, which can accept a new server, and how a valid renewal or rebind ACK refreshes the lease and timers. Keep transaction, client identity, and packet validation in every state. Test initial acquisition and rebinding from a second server. [DHCP draft](RING2_NET.md#udp-and-dhcp) · [RFC 2131 §§4.3.2 and 4.4.5](https://www.rfc-editor.org/rfc/rfc2131.html)

### 7. Make lease release best-effort and define who drives the handoff

The ready publish currently has the kernel send DHCPRELEASE before switching frame ownership. The current DHCP client has no release path, and release can require neighbor resolution or TX space. Keep it best-effort with a bounded budget while the kernel still owns TX, or let the old lease expire. Commit the frame-seat transition separately so service startup cannot stall inside a snapshot syscall. Clarify the first ring-2 milestone. The TCP section says DHCP, ARP, and ping, while the app section includes UDP bind and send. The test plan should name the same required operations in both places. [Frame handoff](RING2_NET.md#frame-seat) · [App operations](RING2_NET.md#ring-3-app-exchange) · [Current DHCP client](../kernel/src/net/dhcp.ritz)

### 8. Scope IRQ readiness and timeout to the device wait

`DrvIrqWait` authorizes a specific device but then parks on global `BLOCK_IRQ` and arms a shared LAPIC watchdog. That can wake the NIC for unrelated interrupts, and an overlapping wait can stop or replace another wait's timeout. The translating test retains NVMe, so one userspace driver does not imply one device waiter. Keep the existing kernel IRQ wait behavior where needed and define device-scoped IRQ readiness and deadlines for the new endpoint. A latched event or generation also closes the window where an IRQ arrives before park. [Proposed IRQ wait](RING1_DRIVER.md#4-one-waitable-interrupt) · [Current wait queue](../kernel/src/proc/waitq.ritz#L31)

## Verification

The Nevelis virtualenv ran 46 existing Harland per-CPU, syscall-stack, syscall-dispatch, and process-model checks successfully. Four Ritz 1 variants were deselected because their compiler binaries are absent from this checkout. The branch adds design documents, so these results cover the current implementation.
