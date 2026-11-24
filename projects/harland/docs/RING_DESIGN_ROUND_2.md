# Round-2 review of the Harland ring-1 and ring-2 designs

Reviewed [RING1_DRIVER.md](RING1_DRIVER.md) and [RING2_NET.md](RING2_NET.md) at `c3062f7d`, after they absorbed [RING1_RING2_REREVIEW.md](RING1_RING2_REREVIEW.md). The architecture is sound: CPL 1 for the driver and CPL 2 for the service, capability authority, a private IOMMU domain as the cutover gate, SPSC frame rings with `seq_cst` index publication, seqlocked snapshots, and the kernel as the first consumer. The claims checked against the tree hold: `sched_yield` and `sched_block` behave as described, `waitq_park` blocks on `BLOCK_IRQ`, `proc_wake` broadcasts, and VT-d interrupt remapping already blocks compatibility-format interrupts.

The design is not ready to freeze the ABI. The previous rounds fixed findings individually, and the wait/notify model is now inconsistent where those fixes meet. There are also two trust-boundary gaps in how the kernel reads shared memory.

## Resolve before freezing the ABI

### 1. The driver has no defined TX wake

Ring 2 says the service's TX `ShmNotify(DATA)` "is the driver's wake". Ring 1 says the frame object has one registered waiter, the RX consumer, and the driver only parks in `DrvIrqWait`. A TX notify from the service has no defined target. [Ring-2 service wait](RING2_NET.md#service-wait) · [Ring-1 frame waiter](RING1_DRIVER.md#6-portable-spsc-ring)

The kernel-seat path has a lost-wakeup race. The driver finds TX empty, the timer preempts it, pid 1 publishes and "wakes the driver pid", which is a no-op because the driver is still runnable, and the driver then enters `DrvIrqWait`. `latched == seen`, so it parks until its deadline. The burst assertion depends on that deadline being short, and the draft does not set it.

The retire request "latched on that peer's wait" has the same gap. The driver is not waiting on the shm object and never observes the request. [Wait and notify](RING1_DRIVER.md#wait-and-notify)

### 2. `ShmWait` cannot express the service's wait

`ShmWait` takes one handle, a mask, and a deadline. The service must wait on the frame object and up to five app exchanges at once. [Syscall table](RING1_DRIVER.md#5-mmio-and-dma-syscalls)

Items 1 and 2 share a root cause: each process needs one wait over several sources. Give each process a wait set. IRQ objects and shm objects post event bits to it under `cli`, and one wait call checks every source before parking. `DrvIrqWait` becomes that wait with the IRQ source included. `DrvRingKick` (223) then duplicates `ShmNotify(DATA)` and can be dropped before it is frozen. Test a TX publish that races the driver's park, and a service waiting on the frame object and two app exchanges.

### 3. The consumer reads shared descriptors twice

`take_rx` calls `check_slot` and then `copy_slot`, both against peer-writable memory. The driver can change `length` between the two, and the kernel copies past its buffer. Specify that the consumer loads the `FrameDesc` once into kernel memory, validates that copy, and copies the frame using only the validated values. Header parsing runs on the private copy, never in place in the arena. The same rule applies to the driver reading TX descriptors and to the service reading app requests. [RX wait sketch](RING1_DRIVER.md#6-portable-spsc-ring)

### 4. The consumer trusts its own index from shared memory

`take_rx` loads `read_idx` from the peer-writable page. The driver can rewind it to replay frames or advance it to skip them. Each side keeps a private copy of its own index, stores it to the shared page, and reads only the peer's index from shared memory. The occupancy check compares the peer's index with the private copy.

### 5. The link record is on a page the service can write

Page 0 holds both `SpscCtrl` blocks, which the service must write, as well as `NetInfo` at `0x200` and `link_seq` at `0x220`. Once the service is seated, "the driver is the only writer of shared `NetInfo`" is false. The service can corrupt the MAC that the driver's next `NetPublish` snapshots, or leave `link_seq` odd. Move the link record to its own object mapped only into the driver. [Region layout](RING1_DRIVER.md#6-portable-spsc-ring) · [Link snapshot](RING1_DRIVER.md#7-link-snapshot)

### 6. The PR plan omits work PR 7 depends on

`ShmWait` (229), `ShmNotify` (230), `NetAttach` (228), and the `ShmObject` lifecycle (mapping count, in-flight count, retire, reclaim) are not in any PR. PR 7's `driver_quiesce` already calls `ShmNotify(DRIVER_GONE)`. [PR plan](RING1_DRIVER.md#pr-plan) · [Shared object](RING1_DRIVER.md#shared-object)

`process_mark_exit` is described as an existing function. It does not exist: the kernel has `process_kill_current`, which exits the caller. The description also contradicts itself: "the scheduler does not resume a marked pid", yet teardown "runs later on the kernel stack as that pid's exit". A pid that never runs cannot run its own exit. Specify a reaper path, including a marked pid parked in `DrvIrqWait`, and place it in a PR. [Occupancy handling](RING1_DRIVER.md#6-portable-spsc-ring) · [Current kill path](../kernel/src/syscall/runtime/process.ritz#L384)

## Resolve before the cutover

### 7. The slot-boundary ACK is probably unnecessary

The object owns its pages, a retired object id is never reused, and a replacement is a new object at a new address. A peer that keeps writing into a retired object therefore cannot harm anyone. Let peers detach themselves when they observe `DRIVER_GONE` or `PEER_CLOSE`, with a timeout after which the kernel unmaps the peer. As drafted, a hung driver that never ACKs blocks every service restart, because no replacement is created before the ACK. [Frame seat](RING2_NET.md#frame-seat) · [Shared object](RING1_DRIVER.md#shared-object)

### 8. `DrvIrqWait` never consumes the wake

The pseudocode does not set `seen = latched` after a park returns, so every interrupt costs one extra syscall that returns at once. The return value also does not distinguish an interrupt from the deadline. [One waitable interrupt](RING1_DRIVER.md#4-one-waitable-interrupt)

### 9. Make interrupt remapping a cutover precondition

DMA translation does not stop the NIC from forging MSIs by writing to the `0xFEE00000` range. `vtd.ritz` already blocks compatibility-format interrupts when remapping is on. The cutover gate should require remapping, not only the QEMU `intremap=on` flag. The AMD-Vi path has no CI run. [DMA domain](RING1_DRIVER.md#dma-domain) · [VT-d interrupt remapping](../kernel/src/drivers/iommu/vtd.ritz)

### 10. Trim and bound `NetInfo` before 224 is frozen

`ipv4`, `gateway`, `netmask`, `dns`, and `configured` are documented as zero "for the life of this design", and `NetAddr` (225) carries that data. Drop them from the frozen struct. Clamp the published `mtu` to `FRAME_MAX` minus the Ethernet header, because the service sizes packets from it.

### 11. Smaller ring-2 protocol points

- Do not answer an echo request addressed to a broadcast destination.
- Learning from every ARP packet invites cache poisoning. RFC 826 updates an existing entry, or adds one only when we are the target.
- UDP and ICMP checksum validation on receive is not specified.
- `DrvDmaAlloc` has no free and bumps a per-process cursor, so repeated device resets leak.

## Document hygiene

- Stale text: "220–227" in [section 5](RING1_DRIVER.md#5-mmio-and-dma-syscalls), the API section, and the risks table (the group now ends at 230). The tests section still says "`proc_free` clearing `driver`". The author field is still "placeholder".
- RING1 has grown into a log of review responses: many "Decided." paragraphs, and RING2 repeats "The first cutover is DHCP, ARP, ping, and a ring-3 UDP bind…" about six times. At 915 lines, inconsistencies like items 1, 2, and 6 are hard to see. Fold the decisions into the body text before PR 1 lands.
- [stack_example](stack_example/) runs as a script (`python3 test_stack.py`) and prints all eight behaviors. It is a sequential model, so it cannot exercise the preemption or double-read problems above. Add an interleaving test if it is meant to back the race claims.

## Verification

Kernel claims were spot-checked against `proc/sched.ritz`, `proc/table.ritz`, `proc/waitq.ritz`, `syscall/runtime/process.ritz`, and `drivers/iommu/vtd.ritz`. `process_mark_exit` is absent from the tree. The host stack example ran to completion. The branch changes documents only, so no kernel tests were rerun.
