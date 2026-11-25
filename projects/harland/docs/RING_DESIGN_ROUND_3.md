# Round 3 review of the Harland Ring 1 and Ring 2 designs

Reviewed the working-tree revisions to [Ring 1](RING1_DRIVER.md), [Ring 2](RING2_NET.md), and the [host stack example](stack_example/) following [round 2](RING_DESIGN_ROUND_2.md). Keep the wait-set ABI open until attach discovery, replacement handoff, and result delivery are specified.

## Findings

1. **[P1] `NetAttach` can leave an idle service asleep.** The kernel promises to deliver the new service-side handle in an attach event. `ShmWait` only returns matching bits for handles the caller already listed, so a service parked with zero apps cannot discover its first exchange. Define a service control source that exists before any attachment and a way to retrieve every pending handle when several apps attach before the service runs. [Attach contract](RING1_DRIVER.md#grants) · [Service wait](RING2_NET.md#service-wait)

2. **[P1] The surviving driver needs a replacement handoff.** On service exit, the driver learns to detach from the old frame object. The replacement has a new ID and address, and publication on it leaves a wait on the old handle untouched. Define how the surviving driver receives the new handle, wakes after detaching, and agrees with the new service on when to start using the rings. Specify what happens if the forced-unmap timeout expires while the driver's saved instruction still accesses the old mapping. [Shared object](RING1_DRIVER.md#shared-object) · [Wait and notify](RING1_DRIVER.md#wait-and-notify)

3. **[P1] `DrvDmaFree` needs explicit address reuse rules.** The draft says freeing all runs on reset prevents cursor exhaustion, but it specifies neither range reuse nor a cursor reset. Define when the VA and IOVA ranges become reusable, what happens to a quarantined IOVA after failed invalidation, and when a run is safe to free while the device is active. [MMIO and DMA syscalls](RING1_DRIVER.md#5-mmio-and-dma-syscalls)

4. **[P2] The wait ABI needs explicit copy-out and deadline semantics.** Both wait calls promise to copy out a handle and event bits. The argument table supplies only a source-array pointer, leaving the result layout and whether the input array is overwritten implicit. Define where the result goes, which errors preserve the latch, and when the kernel snapshots and validates the source list. The `DrvIrqWait` sketch also returns deadline on any empty post-wake poll. Check the original deadline and repark if the wake leaves no matching event. [Interrupt wait](RING1_DRIVER.md#4-one-waitable-interrupt) · [Syscall table](RING1_DRIVER.md#5-mmio-and-dma-syscalls)

5. **[P2] The host traversal ignores IPv4 total length.** `parse_ipv4` passes every byte after the header into `parse_udp`, so UDP can consume bytes beyond the declared IPv4 packet, including Ethernet padding. Bound the payload by IPv4 total length and add a fixture that would only pass if the parser read beyond that boundary. [Host parser](stack_example/stack.py) · [Ring 2 design](RING2_NET.md)

### Additional findings (Claude)

These don't repeat items 1–5. The revision fixes everything round 2 raised: one wait set per process, `DrvRingKick` removed, private indexes, a single descriptor copy, the link record moved to its own object, PR 6b, `process_mark_exit` specified, the ACK protocol dropped, interrupt remapping as a gate, `NetInfo` trimmed, and the ring-2 protocol points. The findings below are about the new wait-set contract.

6. **[P1] Define where `ShmNotify` lands, and therefore where `LINK` lands.** `ShmNotify` takes a handle and an event, but the frame object has two ends. The driver's `DATA` must reach the service, and the service's `DATA` must reach the driver. The draft says a notify "posts to the wait set of the process that included that object", but membership only exists for the duration of a `ShmWait` call. A notify that arrives before the peer calls `ShmWait`, which is exactly the race round 2 asked to close, then has no defined set to post to. Latch the bits on the *peer's end* of the object, one latch word per mapping, and have the wait check the ends it lists. The host model sidesteps this: `WaitSet.notify` is called on the target set directly, which the syscall cannot do. A related problem: `NetPublish` "posts `LINK` to the consumer's wait set", but the link object is mapped only into the driver, and the service's wait lists only the frame object and its exchanges. Say that `LINK` is latched on the service's end of the frame object. [Wait and notify](RING1_DRIVER.md#wait-and-notify) · [Link snapshot](RING1_DRIVER.md#7-link-snapshot) · [Host model](stack_example/stack.py)

7. **[P1] Lifecycle bits must be kernel-only.** Nothing restricts which bits a holder may pass to `ShmNotify`. An app can `ShmNotify(PEER_CLOSE)` or `ShmNotify(DRIVER_GONE)` on its own exchange, and the driver can do the same on the frame object. The service then detaches from a live object. Allow userspace to post only `DATA` and `SPACE`. `PEER_CLOSE`, `DRIVER_GONE`, and `LINK` are posted by the kernel (death, retire, `NetPublish`) and are `Errno.Inval` from a syscall. Add a test where an app posts `PEER_CLOSE` and the service stays attached.

8. **[P2] Return every hot source, not the first one.** Both waits consume and return the first listed source whose bits match. Under load the frame object, listed first, is always hot, so an app exchange later in the list only surfaces when RX goes idle. In `DrvIrqWait` the IRQ source is checked first, so during an RX flood a TX `DATA` latch is never the value returned. The driver drains TX on every return anyway, so that case survives, but the latch stays set and causes a spurious return 2 later. Copy out every matching `{handle, bits}` pair in one call, or rotate the scan start. This also simplifies item 4's copy-out layout to an array of results.

9. **[P2] Check `PROC_REAP` on the return-to-user path, not in the scheduler.** The draft says that selecting a `PROC_REAP` pid "enters `sys_exit_impl` on that pid's kernel stack". The scheduler can't redirect a switched-to pid, because `sched_switch` resumes it where it left off: inside `sched_block` in some syscall, or in the timer stub's frame. That code runs on until it returns to CPL 1. Put the check where the pid would go back to userspace, in the `syscall_entry` iret tail and the non-zero-RPL interrupt return. Every blocking point then has to tolerate being woken without its event, which the wait-set returns already allow (1 or 2). [Occupancy handling](RING1_DRIVER.md#6-portable-spsc-ring) · [PR 3](RING1_DRIVER.md#pr-3-ring-1-entry-preempt-fault)

10. **[P2] Specify the mirror of item 2: the service surviving a driver restart.** Driver death leaves `NetInfo` at `Errno.NoDev` and the service holding a retired frame object. Neither design says who respawns the driver, whether the kernel creates a new frame object for it, or how the surviving service receives that handle and the new link generation. If restart is out of scope for the first cutover, say so: a driver death ends networking until reboot, and the service exits or idles on `DRIVER_GONE`. The "Driver exit first" paragraph's sentence about "a replacement for a restarted service" reads as if it covers this case, but it describes the other direction. [Shared object](RING1_DRIVER.md#shared-object)

11. **[P3] ARP still learns from unsolicited replies.** The RFC 826 rule now gates entries on "the target is ours", but any unsolicited reply addressed to us still creates an entry. Add an entry from a reply only when a request for that IP is outstanding. Requests that target us may still add the sender, as now. [ARP](RING2_NET.md#arp)

### Second pass (Claude), after `f30696ae3`

Items 1–11 are absorbed by `f29d8de77`:

| Item | Fix |
|---|---|
| 1 | The inbox delivers `ATTACH`, including to a service with an empty source list. |
| 2 | The surviving driver gets `ATTACH` for the replacement, and a stale access faults. |
| 3 | `DrvDmaFree` uses a free list, and a quarantined VA or IOVA is never reused. |
| 4 | `WaitRequest` and `WaitEvent` are defined, and an empty wake reparks. |
| 5 | `parse_ipv4` slices to the total length. |
| 6 | Latches live on the peer's mapping, and `LINK` goes to the consumer's frame latch. |
| 7 | Userspace may post only `DATA` and `SPACE`. |
| 8 | Every hot source is copied out, up to `out_cap`. |
| 9 | `PROC_REAP` is checked on the iret tail. |
| 10 | No driver respawn: networking stays down until reboot. |
| 11 | A reply is learned only for an outstanding request. |

The findings below are new. Most are in the app exchange that `35dd88dee` froze.

12. **[P1] Unmatched app events have no bound and no owner.** The rule that "an event with a different `id` stays queued for the call that owns it" holds the event in private library memory, because the event ring is FIFO and `read_idx` only moves forward. The host library does this with an unbounded `held` list (`take_matching`). The design text doesn't mention that queue at all. Three failures follow:
    - **Orphan errors.** `net_send_to` doesn't wait for an event, so an `EV_ERROR` for a send (MTU exceeded, ARP gave up after three retries) has no owning call. It sits in `held` forever, and every failed send adds one more.
    - **Unbounded datagrams.** An app that binds a port and never calls `net_recv_from` on it accumulates every datagram privately, without limit.
    - **Full ring.** If the library instead stops draining, the 32-slot event ring fills with datagrams. The service then "stops producing events for that attachment", so the `EV_BOUND`, `EV_CLOSED`, or `EV_PING_REPLY` a blocked call is waiting for never arrives.

    Treat datagrams as lossy and control replies as owed:
    - Bound the library's per-handle datagram queue and drop with a counter on overflow, which is UDP socket-buffer behavior.
    - Have the service hold a request unconsumed, by not advancing its private request `read_idx`, until it can post that request's reply. A full event ring then backpressures requests instead of losing replies.
    - Either make `net_send_to` errors non-events (count them in the service) or route them to a per-handle error the next call on that handle returns.

    Add a host test that sends 33 oversize datagrams and then binds. [App exchange](RING2_NET.md#ring-3-app-exchange) · [Host library](stack_example/stack.py)

13. **[P1] Latches need to exist before the mapping does.** Each latch is per mapping, and a notify with no live peer mapping returns `Errno.NoDev` and posts nothing. Two consequences:
    - **Lost first request.** After `NetAttach`, the service's handle sits in its inbox unmapped until the service wakes and calls `ShmMap`. An app that publishes `APP_BIND` immediately gets `Errno.NoDev` from `ShmNotify`, and no `DATA` is latched. When the service maps the exchange and lists it, the request is on the ring but its latch is clear, so the service parks on it. Either create the latch when the kernel inserts the handle, not when it maps, or require the service to drain each newly mapped exchange once before its next wait.
    - **Duplicate driver mapping.** For a replacement service, the kernel "maps a new virtual address into the surviving driver", and then the driver "calls `ShmMap` on the new handle". That is two mappings of one object in one process, with two latches, so the service's notify has no single "other mapping". Pick one: the kernel maps and the record carries the VA, or the kernel only inserts the handle and the driver maps. Keying the latch on (object, holding process) instead of on each mapping removes both problems. [Wait and notify](RING1_DRIVER.md#wait-and-notify) · [Shared object](RING1_DRIVER.md#shared-object)

14. **[P2] `ATTACH` for an exchange that has already closed.** An app can `NetAttach` and exit before the service reads the inbox record. The service then `ShmMap`s a retired object. Say whether `ShmMap` of a retired object returns `Errno.NoDev`, in which case the service drops the record, or maps it with `PEER_CLOSE` already latched. Also say whether that inbox record counts against the 8-record cap until it is read. [Grants](RING1_DRIVER.md#grants)

15. **[P3] `PROC_REAP` covers only wait-set blocks.** `process_mark_exit` wakes a pid parked in `DrvIrqWait` or `ShmWait`. A pid blocked elsewhere, such as `wait_for_child`, a tty read, or `BLOCK_IRQ`, re-blocks in that loop and never reaches the iret tail. Either have every blocking loop check `PROC_REAP`, or state that the driver and the service block only in their wait set and that `process_mark_exit` only targets them. [Occupancy handling](RING1_DRIVER.md#6-portable-spsc-ring)

16. **[P3] Small `AppDesc` points.**
    - `net_bind(68)` or `net_bind(67)` collides with the service's own DHCP client. Return `Errno.Exist` for ports the service holds, so an app can't send from 68 or shadow the bootstrap.
    - `AppDesc.port` doesn't state its byte order, while `addr` is wire order. Say that `port` is host order, as the little-endian sentence implies, and that the service swaps it.
    - The library rejects a `length` above 2048, but a UDP payload above `MTU - 28` (1472 at MTU 1500) also can't be sent. Reject it in the library from the `NetInfo` MTU, so the failure is synchronous rather than an orphan `EV_ERROR` (item 12).

## Response

Items 13, 14, and 16 are taken as written. The latch is created when the kernel inserts the handle and is keyed by `(object, pid)`. The replacement path inserts the driver's handle and does not also map a second virtual address. `ShmMap` of a retired object returns `Errno.NoDev`, and the inbox record counts against the cap of 8 until a wait copies it out. Ports 67 and 68 return `Errno.Exist`. `AppDesc.port` is host endian. A UDP payload above `mtu - 28` is rejected in the library.

Two offered alternatives are not taken.

12. **Send failures stay a `send_drops` count.** The bounded per-handle datagram queue and the reserved reply slot are in `RING2_NET.md`. `net_send_to` does not grow an `EV_ERROR`, and that failure is not saved for the next call on the handle. The call has already returned. A later `net_recv_from` is not where a finished send reports ARP loss. A length the link cannot carry is rejected before the request is published. Holding the request alone does not free a ring that is already full of datagrams, because the service cannot drop a slot it has published. Datagrams therefore leave one event slot free, and the waiting library call keeps copying the ring. The final review's item 5 withdraws the hold at the request head. The reserved slot and one outstanding reply are what make the reply fit, so the service consumes the request and keeps the owed reply privately. The `send_drops` half of this item stands.

15. **`PROC_REAP` is not added to every block loop.** The driver and the service block only in `DrvIrqWait` and `ShmWait`, and `process_mark_exit` wakes those waits. `wait_for_child`, a tty read, and in-kernel `BLOCK_IRQ` are outside this cutover.

## Verification

`python3 projects/harland/docs/stack_example/test_stack.py` passed, and `git diff --check` was clean. The host run covers the sequential traversal and scripted interleavings. The timeout helper directly detaches the peer, and the ARP and ICMP checks call standalone helpers. Scheduler timeouts, forced unmapping, and packet-level ARP and ICMP receive behavior remain unverified. Harland was not booted for this review.

For items 6–11, the wait-set, notify, reap, and ARP text was read against the working-tree revisions. `stack.py`'s `WaitSet` was checked against the `ShmNotify` signature. The host run was repeated and exited 0.

For items 12–16, the designs were read at `f30696ae3`. `take_matching` and `parse_ipv4` in `stack.py` were checked, and the host run exited 0.
