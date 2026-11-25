# Harland Ring 1 and Ring 2 approval review

Reviewed the working tree on top of `176325305`, including the changes and responses in [round 3](RING_DESIGN_ROUND_3.md). The architecture and PR sequencing are ready to start. Hold final approval of the wait ABI and Ring 2 cutover until the contracts below are explicit.

## Before final approval

1. **[P1] A wait caller cannot tell how many records were copied.** `WaitRequest` supplies an output capacity, and the syscall return is a reason code. There is no returned count or defined sentinel for the unwritten tail. The IRQ record also has no defined encoding, and zero output capacity currently passes the documented bounds checks. Define the count and IRQ encoding, reject zero capacity, and test a partial batch with prepopulated output memory and a mixed IRQ, SHM, and inbox batch. Resolve the related promise that eight slots cover eight sources plus an IRQ. [Wait ABI](RING1_DRIVER.md#wait-and-notify)

2. **[P1] Attachment lifetime needs a cap per app and a handle cleanup rule.** The five live exchanges assumed by the service wait follow from five app process slots only if `NetAttach` permits one live exchange per process. The documented syscall creates one on every call and the inbox cap only bounds records awaiting delivery. Specify duplicate attach behavior and release the service-side capability when a retired attachment is dequeued, including when `ShmMap` returns `Errno.NoDev` before the service ever maps it. Reclaiming the pages and dropping an inbox record leave capability cleanup unspecified. Test repeated attach and exit on the same process slot and repeated attach from one living app. [Grants](RING1_DRIVER.md#grants) · [Service wait](RING2_NET.md#service-wait)

3. **[P1] A quiet peer can leave a ping request and its attachment blocked.** The service holds a reply-producing request at the request head until its event is published. `APP_PING` defines a matching echo reply but gives no deadline or terminal result if ARP resolves and the peer never answers. Define a deadline that starts once, one in-flight operation for that request, and exactly one terminal event on success or failure. Test on a quiet link and confirm that the next control request can proceed after timeout. [ICMP](RING2_NET.md#icmp) · [App exchange](RING2_NET.md#ring-3-app-exchange)

4. **[P2] Per-handle datagram queues need a close rule and an aggregate bound.** The design bounds each queue, but it leaves the number of live endpoint handles and disposal of queued datagrams on close unspecified. The model keeps both the queue and its drop counter after `net_close`. Repeated bind, receive, and close can accumulate payloads and queue entries for dead handles. Define the live endpoint cap, discard that handle's private state on close, and test repeated close and rebind. [App exchange](RING2_NET.md#ring-3-app-exchange) · [Host model](stack_example/stack.py)

## Round 3 decisions

The inbox covers first attach and driver rebind. Latches start at handle insertion, so a first request can notify before the service maps. The revised DMA free text describes range reuse and quarantine. The bounded datagram queue and reserved reply slot address reply starvation by ordinary UDP traffic. Keeping post-publication send failures in `send_drops` is consistent with the asynchronous send contract. Limiting `PROC_REAP` wake handling to the two network waits is consistent with the stated cutover scope. Preserve that scope when wiring call sites.

## Final pass (Claude)

**Round 3 pushback.** Both declined items are accepted.
- **Item 12.** Reporting a failed UDP send as a `send_drops` count matches ordinary socket behavior, where a finished `sendto` does not report a later ARP failure. The MTU check in the library catches the failure an app can act on before the request is published.
- **Item 15.** Limiting `PROC_REAP` to `DrvIrqWait` and `ShmWait` is sound for this cutover, as long as the driver and the service really block nowhere else. A lint or a test that the two binaries make no other blocking syscall would hold that line when the call sites are wired.

**Round 3 fixes.** Items 13, 14, and 16 landed as written:
- The latch is keyed by `(object, pid)` and is created when the handle is inserted.
- `ShmNotify` returns `Errno.NoDev` only when no peer holds a handle.
- The replacement path inserts the handle and no longer maps the object twice.
- A second `ShmMap` returns the existing address.
- The service drains each newly mapped exchange before it parks.
- `ShmMap` of a retired object returns `Errno.NoDev`, and an inbox record counts against the cap until it is copied out.
- Ports 67 and 68 return `Errno.Exist`, `port` is host endian, and the library rejects a payload above `mtu - 28`.

**Items 1–4 above.** All four are still open in the working tree, and I agree with each. The wait return has no count, `NetAttach` has no per-process cap, `APP_PING` has no deadline, and per-handle state is not discarded on close.

One addition, related to item 3:

5. **[P2] The reserved reply slot makes holding a request at the head unnecessary, and holding it blocks sends.** Requests are FIFO. While an `APP_PING` waits at the head for its reply, every `APP_SEND_TO` the app publishes behind it waits too, for a full round trip or, after item 3, the whole ping deadline. Two invariants already guarantee that a reply always fits:
    - Datagrams leave one event slot free.
    - The library allows only one outstanding reply per attachment.

    The service can therefore consume a control request immediately, store `read_idx`, keep the owed reply in private per-attachment state, and post it into the reserved slot when it is ready. Drop "stores `read_idx` only after the reply is in an event slot" and state the invariant instead. Item 3's deadline then bounds only the owed reply, not the request ring. Test a ping to a quiet peer followed by a `net_send_to` that reaches the TX ring before the ping times out. [App exchange](RING2_NET.md#ring-3-app-exchange)

**Verdict.** The architecture, the trust boundaries, and the PR sequence are sound. PRs 1–5b can start now, because none of them touch the wait ABI or the app exchange. Freeze PR 6b's wait ABI only after item 1. Freeze the ring-2 app exchange only after items 2–5. None of the open items changes the overall shape of either design. Each one tightens a contract that already exists.

## Response

Items 1–5 are taken.

1. **The wait writes `out_count`.** Returns 0, 1, and 2 store how many `WaitEvent` records were copied. Return 1 stores 0 and does not touch `out`. An errno writes neither. The unwritten tail is left as the caller filled it. `out_cap` 0 is `Errno.Inval`. The IRQ record's handle is the `CAP_TYPE_IRQ` handle and its bits are `DATA`. Eight slots hold eight records, so a hot IRQ uses one of them. They do not cover eight listed sources plus an IRQ.

2. **One live exchange per app process.** A second `NetAttach` returns `Errno.Exist` and creates nothing. The inbox depth is not that cap. Copying out an already-retired attach drops the service handle before the wait returns. `ShmMap` of a retired object the caller still holds returns `Errno.NoDev` and drops that handle. The service does not detach an object it never mapped.

3. **`PING_DEADLINE_MS` is 1000.** It starts once, when the echo is published, and it is not restarted. One echo is in flight. Success is one `EV_PING_REPLY`. Failure is one `EV_ERROR` with `Errno.Io` (-5), including ARP giving up before an echo is sent. A late reply after that error is dropped. The kernel errno set has no timed-out discriminant, and this cutover does not add one, so the terminal failure is `Errno.Io`.

4. **Close drops that handle's private state.** `MAX_ENDPOINTS` is 16. `net_close` discards the handle's queued datagrams and its drop counter. A later call on that handle is `Errno.BadF`.

5. **The request is consumed when it is read.** The owed reply sits in private per-attachment state and is posted into the reserved event slot. An `APP_SEND_TO` behind a ping reaches the TX ring while the echo is still in flight. The round-3 hold at the request head is withdrawn. The reserved slot stays, because a published datagram still cannot be dropped.

## Verification

The review aligned Ring 2's latch description with Ring 1 and moved the host event payload copy before the read-index store, so the model releases the slot after the copy. The host script passed and the tracked diff passed `git diff --check`. The script exercises sequential interleavings and packet traversal. Scheduler parks, forced unmapping, and translated DMA remain boot acceptance checks. Harland was not booted for this review.

For the final pass, the round-3 response and the working-tree text of both designs were read on top of `176325305`. The host script was rerun and exited 0.
