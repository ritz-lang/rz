# Review feedback for the Harland ring-2 network service

This review covers [RING2_NET.md](RING2_NET.md) at `9cd22556`. Keep the ownership split. The ring-1 driver owns device queues and link metadata, the ring-2 service owns protocol and lease state, and apps use a separate exchange.

At this revision, [RING1_DRIVER.md](RING1_DRIVER.md) is unchanged from `a92ac7d2`. The ring-2 draft carries the [ring-1 review findings](RING1_DRIVER_FEEDBACK.md) as dependencies. Per-device DMA domains remain a prerequisite for the first virtio-net cutover, along with the mapping, teardown, scheduling, MMIO, and syscall-return fixes identified in that review.

## Service and kernel contracts

### Wait for all work and preserve progress under backpressure

The service needs to wake for NIC RX, TX space, requests on every app attachment, link and peer changes, and protocol deadlines. Parking on an empty app request ring can strand work on another source. Define a kernel wait that atomically rechecks all relevant sources before parking, including the earliest timer deadline.

A full TX ring cannot suspend RX draining. If the driver waits for RX space while the service waits for TX space, scheduling both endpoints still leaves them stuck. Define how each endpoint continues draining the opposite direction, with bounded pending queues and an explicit policy when those queues fill. Test simultaneous full RX and TX and a protocol timer expiring on an idle link. [Ethernet send](RING2_NET.md#ethernet-demux) · [App exchange](RING2_NET.md#ring-3-app-exchange)

### Specify app attachment isolation and teardown

Keep the two SPSC rings per app. Define which side can write each control and payload region, validate descriptors before consuming them, and scope request IDs and socket handles to the attachment. Specify behavior when an app stops consuming events, exits with pending requests, or restarts into a reused process slot. One stalled app must leave NIC RX, DHCP, and other apps able to make progress. The existing `proc_wake(reason)` broadcasts to all processes waiting for that reason, so the exchange needs its own endpoint identity and peer-close semantics. [App exchange](RING2_NET.md#ring-3-app-exchange) · [Current kernel wake implementation](../kernel/src/proc/table.ritz#L203)

### Define exclusive frame ownership and restart

Specify when the kernel relinquishes the RX consumer and TX producer roles, what happens to in-flight slots, and how the driver and apps wake when the service exits or faults. Define how a replacement acquires the rings and how readers detect that a previous lease snapshot is stale. Publish a consistent read-only address snapshot and make invalidation part of the service lifecycle, since a faulting service cannot clear its own published page.

The CPL-2 service uses the stack in its `iretq` frame. `TSS.rsp2` applies to an entry whose target is CPL 2, so ordinary syscall and interrupt entry into CPL 0 does not require it. [Placement](RING2_NET.md#placement) · [Address publication](RING2_NET.md#address-publication) · [CPL-2 entry note](RING2_NET.md#what-this-draft-leaves-in-place)

## Protocol corrections

- **Validate nested lengths and honor the link MTU.** Use IPv4 total length to bound transport parsing independently of Ethernet padding. Check UDP length, TCP data offset, and DHCP option lengths against their enclosing payloads. The current DHCP option walker reads length and data without first establishing that they fit. Drop fragments before transport dispatch. The 2048-byte ring slot is storage capacity. Use link MTU and, for TCP, peer MSS to size outgoing packets. [IPv4 draft](RING2_NET.md#ipv4) · [DHCP option parser](../kernel/src/net/dhcp.ritz#L257) · [TCP specification](https://www.rfc-editor.org/rfc/rfc9293.html)
- **Constrain DHCP bootstrap and define lease lifetime.** While unconfigured, admit matching DHCP traffic through a dedicated bootstrap path. Define transaction and server matching, retry, renewal, rebinding, expiry, and link-loss behavior. Move the `10.0.2.2` and `/24` defaults into the QEMU fixture. If a lease omits a router, leave off-link routing unavailable. [DHCP draft](RING2_NET.md#udp-and-dhcp) · [DHCP specification](https://www.rfc-editor.org/rfc/rfc2131.html)
- **Bound ARP pending sends and route ICMP replies.** Limit queued sends awaiting neighbor resolution and expire them with a defined result. Use the usual IPv4 next-hop lookup for echo replies so a remote requester is reached through the gateway. [ARP draft](RING2_NET.md#arp) · [ICMP draft](RING2_NET.md#icmp)
- **Treat TCP as a separate milestone.** Add receipt of `SYN-ACK` for active connects and give an invalid segment and a valid reset separate handling. Define sequence and ACK validation, receive flow control tied to application consumption, retransmission and congestion behavior, and half-close and TIME-WAIT semantics before exposing TCP streams. The initial ring-2 cutover can prove ownership and progress with DHCP, ARP, and ping. [TCP draft](RING2_NET.md#tcp) · [TCP state machine](https://www.rfc-editor.org/rfc/rfc9293.html) · [Congestion control](https://www.rfc-editor.org/rfc/rfc5681.html)

The 21 existing per-CPU and syscall-stack checks passed during review. They exercise the current kernel. The service and its handoff remain design work at the reviewed revision.
