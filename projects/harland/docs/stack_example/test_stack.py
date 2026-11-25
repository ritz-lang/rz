"""Drive the host stack traversal, the eight re-review behaviors, and the
round-2 interleavings.

The log names each behavior and prints the datagram and stream bytes at the
userspace calls and inside the device frame on send.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stack

DATAGRAM = b"datagram-payload-9c1e"
STREAM = b"stream-payload-4ab0"
PENDING = b"pending-datagram-space"
OUR_MAC = bytes.fromhex("525400123456")
PEER_MAC = bytes.fromhex("525400aabbcc")
OUR_IP = bytes((10, 0, 2, 15))
PEER_IP = bytes((10, 0, 2, 2))


def udp_device_frame(payload, destination_port):
    udp = stack.build_udp(44000, destination_port, payload)
    ip = stack.build_ipv4(17, PEER_IP, OUR_IP, udp)
    ethernet = stack.build_ethernet(OUR_MAC, PEER_MAC, ip)
    return stack.device_frame(ethernet)


def tcp_device_frame(payload, sequence):
    tcp = stack.build_tcp(80, 40000, sequence, payload)
    ip = stack.build_ipv4(6, PEER_IP, OUR_IP, tcp)
    ethernet = stack.build_ethernet(OUR_MAC, PEER_MAC, ip)
    return stack.device_frame(ethernet)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def frame_protocol(frame):
    parsed = stack.parse_ipv4(frame[stack.VIRTIO_HDR:])
    if parsed is None:
        return None
    return parsed[0]


def udp_payload_of(frame):
    """Parse a device frame with the shipped IPv4 and UDP readers."""
    ethernet = frame[stack.VIRTIO_HDR:]
    parsed = stack.parse_ipv4(ethernet)
    if parsed is None:
        return None
    protocol, source, destination, body = parsed
    if protocol != 17:
        return None
    return stack.parse_udp(body, source, destination)


def run():
    host = stack.Stack()
    bound = host.net_bind(9999)
    require(isinstance(bound, int) and bound > 0, "net_bind did not return a handle")
    require(host.handle_ports[bound] == 9999, "bind did not record the requested port")
    again = host.net_bind(9999)
    require(again == stack.ERRNO_EXIST, "second bind of a live port returned %s" % again)
    require(host.next_handle == 2, "the refused bind allocated a handle")
    host.deliver_device_frame(udp_device_frame(DATAGRAM, 9999))
    received = host.net_recv_from(bound)
    require(received is not None, "net_recv_from returned nothing")
    payload, source, source_port = received
    require(payload == DATAGRAM, "datagram bytes changed in the stack")
    require(source == PEER_IP, "datagram source address was not parsed")
    require(source_port == 44000, "datagram source port was not parsed")
    print("net_recv_from datagram bytes: %s" % payload.decode())

    host.net_connect(PEER_IP, 80)
    host.deliver_device_frame(tcp_device_frame(STREAM, 1000))
    stream_bytes = host.net_read(("stream", PEER_IP, 80))
    require(stream_bytes == STREAM, "stream bytes changed in the stack")
    print("net_read stream bytes: %s" % stream_bytes.decode())

    writes_before_oversize = host.exchange.req_write
    require(
        host.net_send_to(bound, b"x" * (stack.APP_SLOT + 1), PEER_IP, 44000) == stack.ERRNO_INVAL,
        "an oversize send was published",
    )
    require(host.exchange.req_write == writes_before_oversize, "an oversize send advanced the request index")
    host.net_send_to(bound, DATAGRAM, PEER_IP, 44000)
    require(host.device_tx, "datagram send produced no device frame")
    datagram_frame = host.device_tx[-1]
    send_seq = host.exchange.req_write - 1
    raw = host.exchange.request_desc_bytes(send_seq)
    require(struct.unpack("<H", raw[0:2])[0] == stack.APP_SEND_TO, "send kind is not at byte 0")
    require(raw[12:14] == struct.pack("<H", 44000), "port is not host-endian at byte 12")
    require(raw[12:14] != struct.pack(">H", 44000), "port was stored in wire order")
    require(raw[16:20] == PEER_IP, "address is not at byte 16")
    require(struct.unpack("<I", raw[20:24])[0] == len(DATAGRAM), "length is not at byte 20")
    desc = stack.decode_app_desc(raw, send_seq)
    require(desc is not None, "published send did not decode")
    require(host.exchange.request_payload(desc) == DATAGRAM, "request arena payload ignored length")
    poison_at = stack.REQ_ARENA + desc["arena_off"] + desc["length"]
    require(host.exchange.region[poison_at] == 0xFF, "bytes past length were not left unread")
    mutated = bytearray(raw)
    mutated[24:28] = struct.pack("<I", desc["arena_off"] + 1)
    require(stack.decode_app_desc(bytes(mutated), send_seq) is None, "a bad arena_off decoded")
    udp = udp_payload_of(datagram_frame)
    require(udp is not None and udp[2] == DATAGRAM, "device frame UDP payload is not the datagram")
    require(udp[0] == 9999, "device frame source port is not the bound port")
    print("net_send_to device frame contains datagram bytes: %s" % DATAGRAM.decode())

    host.net_write(("stream", PEER_IP, 80), STREAM)
    stream_frame = host.device_tx[-1]
    require(STREAM in stream_frame, "device frame does not carry the stream bytes")
    print("net_write device frame contains stream bytes: %s" % STREAM.decode())

    driver_first = stack.death_order("driver-first")
    service_first = stack.death_order("service-first")
    require(driver_first == [True, True, False], "driver-first death freed pages too early: %s" % driver_first)
    require(service_first == [True, True, False], "service-first death freed pages too early: %s" % service_first)
    print(
        "behavior: backing pages stay allocated while the other mapping is live, "
        "driver-first observed=%s service-first observed=%s" % (driver_first, service_first)
    )

    link = stack.ShmObject(7, ["link-page"])
    exchange = stack.ShmObject(8, ["exchange-page"])
    link_handle = stack.Handle(link, stack.CAP_RIGHT_PUBLISH, "driver")
    exchange_handle = stack.Handle(exchange, stack.DATA | stack.SPACE, "app")
    require(stack.net_publish(link_handle, {7}) == "ok", "link publish right was refused")
    require(stack.net_publish(exchange_handle, {7, 8}) == "perm", "exchange handle was allowed to publish")
    print("behavior: generic exchange handle cannot publish")

    space = stack.Stack()
    space_handle = space.net_bind(9999)
    require(isinstance(space_handle, int) and space_handle > 0, "pending send had no binding")
    filled = space.fill_tx()
    require(filled == stack.DEPTH, "TX ring did not fill")
    require(
        space.net_send_to(space_handle, PENDING, PEER_IP, 44000) == "queued",
        "full ring did not queue the send",
    )
    before = len(space.device_tx)
    rx_before = space.rx_notifies
    moved = space.release_tx_space()
    require(moved, "TX-space notify did not move the pending send")
    require(space.rx_notifies == rx_before, "TX-space wake was accompanied by an incoming frame")
    new_frames = space.device_tx[before:]
    require(any(PENDING in frame for frame in new_frames), "pending send did not reach a device frame")
    print("behavior: TX-space-only wake delivered a pending send with no incoming frame")

    replacement = stack.replacement_generation()
    require(replacement["old_id"] != replacement["new_id"], "replacement reused the object id")
    require(replacement["new_generation"] == 2, "replacement did not publish generation 2")
    require(replacement["old_has_driver_gone"], "retired object did not latch driver death")
    require(
        replacement["old_still_gone_after_new_publish"],
        "replacement generation 2 cleared the previous object's death",
    )
    print("behavior: replacement generation 2 is not the previous object")

    try:
        stack.occupancy(0, stack.U64_MAX)
    except stack.BackwardsIndex:
        backwards_rejected = True
    else:
        backwards_rejected = False
    require(backwards_rejected, "backwards index was accepted")
    near_wrap = stack.occupancy(stack.U64_MAX, stack.U64_MAX - 1)
    require(near_wrap == 1, "near-wrap distance was %s" % near_wrap)
    print("behavior: backwards occupancy index rejected without subtraction")

    client = stack.DhcpClient()
    require(client.discover(True), "discover did not enter SELECTING")
    require(client.offer("server-a", True), "SELECTING refused the first server")
    require(client.ack("server-a", 3600, 1800, 3150, True), "initial ACK did not commit the lease")
    client.state = "REBINDING"
    require(client.ack("server-b", 7200, 3600, 6300, True), "rebind ACK from a second server was refused")
    require(client.server == "server-b", "selected server did not change on rebind")
    require(client.lease == 7200 and client.t1 == 3600 and client.t2 == 6300, "rebind did not refresh the timers")
    print("behavior: rebind ACK from a second server refreshed the lease")

    result = stack.handoff(lambda: False)
    require(result["publish_returned"], "snapshot call did not return")
    require(result["released"] is False, "failed release was reported as sent")
    require(result["seat"] == "service", "seat did not switch after a failed release")
    print("behavior: seat handoff completed when release did not succeed")

    nic = stack.IrqObject("virtio-net")
    nvme = stack.IrqObject("nvme")
    nvme.interrupt()
    require(nic.drv_irq_wait() == "parked", "NVMe interrupt completed the NIC wait")
    nic.interrupt()
    require(nic.drv_irq_wait() == "ready", "the NIC's own interrupt did not complete its wait")
    print("behavior: unrelated interrupt did not satisfy the device wait")

    parked = stack.IrqObject("virtio-net")
    require(parked.return_from_park() == "deadline", "an empty latch returned an interrupt")
    parked.interrupt()
    require(parked.return_from_park() == "irq", "a parked return did not consume the latch")
    require(parked.return_from_park() == "deadline", "the same latch completed a second wait")
    print("behavior: a park return consumes the interrupt, and the next call is the deadline")

    require(stack.tx_publish_races_park(), "TX publish before the park was treated as a deadline")
    print("behavior: TX data latched on the driver mapping is a shm event, not the deadline")

    require(
        stack.service_wait_returns_every_hot_source(),
        "one wait returned only the first hot source",
    )
    print("behavior: one service wait returns the frame object and a later exchange")

    require(stack.idle_service_attaches(), "an idle service missed a pending attach")
    print("behavior: a service with no exchanges receives every pending attach")

    require(stack.replacement_handle_for_driver(), "the surviving driver did not receive the new handle")
    print("behavior: the driver inbox delivers the replacement frame handle")

    require(stack.user_lifecycle_bit_refused(), "an app PEER_CLOSE detached the service")
    print("behavior: userspace cannot post PEER_CLOSE")

    require(stack.empty_wake_reparks(), "an empty wake before the deadline returned the deadline")
    print("behavior: an empty wake reparks until the deadline")

    require(stack.partial_wait_keeps_the_tail(), "a short wait overwrote its tail or dropped the IRQ")
    print("behavior: out_count is the copied prefix, and the IRQ record uses one slot")

    require(stack.out_cap_zero_consumes_nothing(), "out_cap 0 consumed a latch")
    print("behavior: out_cap 0 is Inval and consumes nothing")

    require(stack.reap_skips_repark(), "a reaped process parked again with no event")
    print("behavior: PROC_REAP returns toward exit instead of parking")

    shared = {"length": 64}
    require(stack.copy_desc_once(shared) == 64, "the private descriptor copy was not the original length")
    require(shared["length"] == 2098, "the shared descriptor was not changed after the copy")
    require(stack.copy_desc_once({"length": 3000}) is None, "a length above FRAME_MAX was accepted")
    print("behavior: the consumer validates one private descriptor copy")

    side = stack.IndexSide()
    side.peer_rewrites_our_index(100)
    require(side.shared_read == 100 and side.private_read == 4, "the private index moved with the shared word")
    require(side.distance() == 2, "occupancy followed the rewritten shared index")
    print("behavior: occupancy uses the private index after the peer rewrites the shared word")

    hung = stack.hung_peer_timeout()
    require(hung["held_until_unmap"], "pages were freed while the hung peer was still mapped")
    require(hung["reclaimed"], "unmap of the hung peer did not reclaim the object")
    require(hung["replacement_id"] == 2, "the replacement did not exist before the hung peer detached")
    print("behavior: a replacement exists before the hung peer is unmapped")

    raw = stack.build_udp(44000, 9999, b"udp-csum-7f3a")
    good = stack.udp_checksum(PEER_IP, OUR_IP, raw)
    require(good != 0, "the checksum fixture folded to zero")
    bad = 1 if good != 1 else 2
    host.deliver_device_frame(udp_frame_with_checksum(b"udp-csum-bad", 9999, bad))
    require(host.net_recv_from(bound) is None, "a mismatched UDP checksum was delivered")
    host.deliver_device_frame(udp_frame_with_checksum(b"udp-csum-7f3a", 9999, good))
    checked = host.net_recv_from(bound)
    require(checked is not None and checked[0] == b"udp-csum-7f3a", "a valid UDP checksum was dropped")
    print("behavior: a non-zero UDP checksum is checked, and zero stayed legal on the first datagram")

    cache = {}
    pending = set()
    other = bytes((10, 0, 2, 99))
    require(
        stack.arp_observe(cache, "request", PEER_IP, PEER_MAC, other, OUR_IP, pending) == "ignored",
        "ARP learned a request for someone else",
    )
    require(
        stack.arp_observe(cache, "reply", PEER_IP, PEER_MAC, OUR_IP, OUR_IP, pending) == "ignored",
        "an unsolicited ARP reply created an entry",
    )
    require(PEER_IP not in cache, "an ignored ARP packet created a cache entry")
    require(
        stack.arp_observe(cache, "request", PEER_IP, PEER_MAC, OUR_IP, OUR_IP, pending) == "added",
        "ARP did not learn a request that targets us",
    )
    pending.add(other)
    reply_mac = bytes.fromhex("525400ddeeff")
    require(
        stack.arp_observe(cache, "reply", other, reply_mac, OUR_IP, OUR_IP, pending) == "added",
        "a reply for an outstanding request was ignored",
    )
    updated_mac = bytes.fromhex("525400112233")
    require(
        stack.arp_observe(cache, "reply", PEER_IP, updated_mac, other, OUR_IP, pending) == "updated",
        "an existing ARP entry was not updated",
    )
    require(cache[PEER_IP] == updated_mac, "the ARP update did not store the new MAC")
    print("behavior: ARP updates an existing entry, adds a request that targets us, and ignores an unsolicited reply")

    broadcast_ip = bytes((255, 255, 255, 255))
    broadcast_mac = b"\xff" * 6
    require(not stack.icmp_echo_answered(broadcast_ip, OUR_MAC, True), "a broadcast IPv4 echo was answered")
    require(not stack.icmp_echo_answered(OUR_IP, broadcast_mac, True), "a broadcast Ethernet echo was answered")
    require(not stack.icmp_echo_answered(OUR_IP, OUR_MAC, False), "a bad ICMP checksum was answered")
    require(stack.icmp_echo_answered(OUR_IP, OUR_MAC, True), "a unicast echo with a good checksum was dropped")
    print("behavior: broadcast echo requests and a bad ICMP checksum are not answered")

    inside = b"inside-ip"
    udp = stack.build_udp(44000, 9999, inside)
    ip = stack.build_ipv4(17, PEER_IP, OUR_IP, udp)
    padded = stack.build_ethernet(OUR_MAC, PEER_MAC, ip) + b"OUTSIDE!"
    host.deliver_device_frame(stack.device_frame(padded))
    bounded = host.net_recv_from(bound)
    require(bounded is not None and bounded[0] == inside, "IPv4 padding was delivered as payload")
    overclaim = bytearray(stack.device_frame(padded))
    length_at = stack.VIRTIO_HDR + 14 + 20 + 4
    claim = len(udp) + len(b"OUTSIDE!")
    overclaim[length_at] = (claim >> 8) & 0xFF
    overclaim[length_at + 1] = claim & 0xFF
    host.deliver_device_frame(bytes(overclaim))
    require(host.net_recv_from(bound) is None, "UDP consumed bytes past the IPv4 total length")
    print("behavior: IPv4 total length bounds the UDP parse, including padding past that length")

    echo = b"ping-body-3c91"
    reply = host.net_ping(PEER_IP, echo)
    ping_seq = host.exchange.ev_write - 1
    ping_raw = host.exchange.event_desc_bytes(ping_seq)
    ping_desc = stack.decode_app_desc(ping_raw, ping_seq)
    require(ping_desc is not None and ping_desc["kind"] == stack.EV_PING_REPLY, "ping reply did not decode")
    arena_echo = host.exchange.event_payload(ping_desc)
    require(arena_echo == echo, "ping event payload is not the request bytes")
    require(reply == arena_echo, "net_ping did not return the event payload")
    print("net_ping reply bytes: %s" % reply.decode())

    require(host.submit_kind(stack.APP_CONNECT) == stack.ERRNO_NOSYS, "APP_CONNECT opened a stream")
    require(host.submit_kind(stack.APP_WRITE) == stack.ERRNO_NOSYS, "APP_WRITE queued stream bytes")
    print("behavior: reserved stream requests return NoSys and publish no retransmission")

    sender = stack.Stack()
    require(stack.tool_udp_send(sender, DATAGRAM, PEER_IP, 44000) == "sent", "udp-send did not send")
    sent_udp = udp_payload_of(sender.device_tx[-1])
    require(sent_udp is not None and sent_udp[2] == DATAGRAM, "udp-send payload changed")
    require(stack.EPHEMERAL_MIN <= sent_udp[0] <= stack.EPHEMERAL_MAX, "udp-send did not bind an ephemeral port")
    print("udp-send datagram bytes: %s" % sent_udp[2].decode())

    quiet = stack.Stack()
    quiet.address_published = False
    require(stack.tool_udp_send(quiet, DATAGRAM, PEER_IP, 44000) == stack.ERRNO_NODEV, "unpublished NetAddr sent")
    require(quiet.exchange.req_write == 0 and quiet.device_tx == [], "NoDev still published a request")
    absent = stack.Stack()
    absent.service_present = False
    require(stack.tool_ping(absent, PEER_IP, echo) == stack.ERRNO_NODEV, "a missing service answered ping")
    require(absent.exchange.req_write == 0, "NoDev from NetAttach published a ping")

    receiver = stack.Stack()
    got = stack.tool_udp_recv_once(receiver, 9999, udp_device_frame(DATAGRAM, 9999))
    require(got is not None and got[0] == DATAGRAM and got[1] == PEER_IP and got[2] == 44000, "udp-recv changed the datagram")
    print("udp-recv datagram bytes: %s" % got[0].decode())

    pinger = stack.Stack()
    tool_reply = stack.tool_ping(pinger, PEER_IP, echo)
    require(tool_reply == echo, "ping tool reply was not the request payload")
    frames_after_echo = len(pinger.device_tx)
    require(
        stack.tool_ping(pinger, bytes((255, 255, 255, 255)), echo) == stack.ERRNO_INVAL,
        "ping tool answered a broadcast",
    )
    require(len(pinger.device_tx) == frames_after_echo, "broadcast ping transmitted an echo")
    print("ping tool reply bytes: %s" % tool_reply.decode())

    queued = stack.Stack()
    first = queued.net_bind(9999)
    require(first == 1, "first bind handle was %s" % first)
    queued.deliver_device_frame(udp_device_frame(DATAGRAM, 9999))
    second = queued.net_bind(9998)
    require(second == 2, "bind behind a datagram returned %s" % second)
    require(queued.handle_ports.get(second) == 9998, "the returned handle is not port 9998")
    kept = queued.net_recv_from(first)
    require(
        kept is not None and kept[0] == DATAGRAM and kept[1] == PEER_IP and kept[2] == 44000,
        "a datagram queued ahead of bind was dropped",
    )
    print("behavior: a datagram stays queued across a later bind, bytes: %s" % kept[0].decode())

    limited = stack.Stack()
    first_port = limited.net_bind(9999)
    require(first_port == 1, "limited stack's first handle was %s" % first_port)
    sent_before = limited.exchange.req_write
    events_before = limited.exchange.ev_write
    oversize = b"x" * (limited.mtu - stack.IPV4_HDR - stack.UDP_HDR + 1)
    for _ in range(33):
        refused = limited.net_send_to(first_port, oversize, PEER_IP, 44000)
        require(refused == stack.ERRNO_INVAL, "an oversize send returned %s" % refused)
    require(limited.exchange.req_write == sent_before, "oversize sends were published")
    require(limited.exchange.ev_write == events_before, "oversize sends posted an event")
    rebound = limited.net_bind(9998)
    require(rebound == 2, "bind after 33 oversize sends returned %s" % rebound)
    after_bind = limited.exchange.ev_write
    limited.drop_unanswered_sends()
    require(limited.send_drops == 1, "an unanswered send was not counted")
    require(limited.exchange.ev_write == after_bind, "send_drops posted an event")
    print("behavior: 33 oversize sends publish nothing, and the next bind returns handle 2")

    flooded = stack.Stack()
    flood_handle = flooded.net_bind(9999)
    require(flood_handle == 1, "flood handle was %s" % flood_handle)
    flood_body = b"flood-datagram"
    for _ in range(33):
        flooded.deliver_device_frame(udp_device_frame(flood_body, 9999))
    posted = stack.APP_DEPTH - stack.REPLY_RESERVE
    require(flooded.service_datagram_drops == 33 - posted, "the reply slot was filled with datagrams")
    require(flooded.exchange.event_occupancy() == posted, "the event ring did not keep the reply slot")
    other = flooded.net_bind(9998)
    require(other == 2, "bind behind a full datagram ring returned %s" % other)
    require(len(flooded.exchange.datagram_queue[flood_handle]) == posted, "the library queue did not keep the posted datagrams")
    require(flooded.exchange.datagram_drops.get(flood_handle, 0) == 0, "the library dropped a datagram that fit")
    flood_got = flooded.net_recv_from(flood_handle)
    require(flood_got is not None and flood_got[0] == flood_body, "a queued datagram was not returned")
    require(flooded.exchange.held == [], "a datagram was left in the reply queue")
    print("behavior: datagrams leave a reply slot, and a later bind still returns handle 2")

    dhcp_ports = stack.Stack()
    require(dhcp_ports.net_bind(stack.DHCP_CLIENT_PORT) == stack.ERRNO_EXIST, "port 68 was bound")
    require(dhcp_ports.net_bind(stack.DHCP_SERVER_PORT) == stack.ERRNO_EXIST, "port 67 was bound")
    require(dhcp_ports.next_handle == 1, "a DHCP port allocated a handle")
    print("behavior: ports 67 and 68 stay with the DHCP client")

    latches = stack.HandleLatches()
    latches.insert(1, 9)
    latches.insert(2, 9)
    require(latches.notify(2, 9, stack.DATA) == 0, "a notify before ShmMap was refused")
    require(latches.latch(1, 9) & stack.DATA, "the unmapped peer did not latch DATA")
    require(not latches.is_mapped(1, 9), "insert mapped the object")
    latches.retire(9)
    require(latches.shm_map(1, 9) == stack.ERRNO_NODEV, "a retired object mapped")
    print("behavior: the latch exists before ShmMap, and a retired object does not map")

    exchanges = stack.ExchangeTable()
    first = exchanges.attach(4)
    retired_id = exchanges.live[4]
    require(isinstance(first, int) and first > 0, "the first attach on a slot failed")
    exchanges.exit_process(4)
    require(retired_id not in exchanges.pages, "exit left the retired object's pages")
    _copied, released = exchanges.dequeue()
    require(released == [retired_id], "dequeue did not drop the retired service capability")
    require(retired_id not in exchanges.service_caps, "the retired service handle survived dequeue")
    require(exchanges.shm_map(retired_id) == stack.ERRNO_BADF, "a dropped handle mapped")
    second = exchanges.attach(4)
    require(isinstance(second, int) and second > 0, "the reused slot could not attach")
    require(exchanges.live[4] != retired_id, "the reused slot resumed the retired object")
    living = stack.ExchangeTable()
    live_handle = living.attach(5)
    require(isinstance(live_handle, int) and live_handle > 0, "a living app could not attach")
    require(living.attach(5) == stack.ERRNO_EXIST, "a second attach from one process created an exchange")
    require(len(living.inbox) == 1, "the refused attach enqueued a record")
    live_id = living.live[5]
    _copied, released = living.dequeue()
    require(released == [], "a live dequeue dropped the service capability")
    living.exit_process(5)
    require(living.shm_map(live_id) == stack.ERRNO_NODEV, "ShmMap of an unmapped retired exchange did not return NoDev")
    require(live_id not in living.service_caps, "NoDev left the service capability")
    require(living.shm_map(live_id) == stack.ERRNO_BADF, "a second map detached an object the service never mapped")
    print("behavior: one exchange per process, and a retired attach drops the service capability")

    capped = stack.Stack()
    live_handles = []
    for _ in range(stack.MAX_ENDPOINTS):
        got = capped.net_bind(0)
        require(isinstance(got, int) and got > 0, "a bind inside the endpoint cap failed")
        live_handles.append(got)
    handle_after_cap = capped.next_handle
    require(capped.net_bind(0) == stack.ERRNO_NFILE, "bind past the endpoint cap allocated a handle")
    require(capped.next_handle == handle_after_cap, "the refused bind advanced the handle")
    require(capped.net_close(live_handles[0]) == 0, "closing one endpoint failed")
    rebound = capped.net_bind(0)
    require(rebound == handle_after_cap, "a bind after close did not take the next handle")
    print("behavior: one exchange keeps at most 16 live endpoints")

    stale = stack.Stack()
    stale_handle = stale.net_bind(9999)
    other_handle = stale.net_bind(9998)
    stale.deliver_device_frame(udp_device_frame(b"stale-after-close", 9999))
    stale.deliver_device_frame(udp_device_frame(b"kept-for-other", 9998))
    stale.exchange.drain_events()
    stale.exchange.datagram_drops[stale_handle] = 3
    require(stale.exchange.datagram_queue[stale_handle], "the closing handle had no queued datagram")
    require(stale.net_close(stale_handle) == 0, "net_close failed")
    require(stale_handle not in stale.exchange.datagram_queue, "close kept the datagram queue")
    require(stale_handle not in stale.exchange.datagram_drops, "close kept the drop counter")
    require(stale.net_recv_from(stale_handle) == stack.ERRNO_BADF, "a closed handle still received")
    require(
        stale.net_send_to(stale_handle, b"x", PEER_IP, 1) == stack.ERRNO_BADF,
        "a closed handle still sent",
    )
    kept = stale.net_recv_from(other_handle)
    require(kept is not None and kept[0] == b"kept-for-other", "close discarded another handle's datagram")
    rebound_same_port = stale.net_bind(9999)
    require(rebound_same_port == stale_handle + 2, "rebind reused a closed handle number")
    require(stale.net_recv_from(rebound_same_port) is None, "rebind delivered a discarded datagram")
    print("behavior: net_close discards that handle's datagrams and its drop counter")

    lost = stack.Stack()
    lost.arp_unresolved = True
    frames_before_lost = len(lost.device_tx)
    require(lost.net_ping(PEER_IP, b"no-arp") == stack.ERRNO_IO, "unresolved ARP did not end the ping")
    require(len(lost.device_tx) == frames_before_lost, "unresolved ARP transmitted an echo")
    require(lost.ping_wait is None, "the failed ping stayed in flight")
    require(isinstance(lost.net_bind(9999), int), "a bind after ARP failure did not proceed")
    print("behavior: ARP giving up is one EV_ERROR and no echo")

    quiet_call = stack.Stack()
    quiet_call.peer_quiet = True
    frames_before_quiet = len(quiet_call.device_tx)
    require(quiet_call.net_ping(PEER_IP, b"quiet-body") == stack.ERRNO_IO, "a quiet peer did not time out")
    quiet_echoes = [frame for frame in quiet_call.device_tx if frame_protocol(frame) == 1]
    require(len(quiet_echoes) == frames_before_quiet + 1, "the quiet ping did not send one echo")
    require(quiet_call.ping_wait is None, "the timed-out ping stayed owed")
    require(quiet_call.expire_pings() == 0, "the ping deadline posted a second event")
    require(quiet_call.exchange.ev_write == 1, "the quiet ping posted more than one event")
    print("behavior: a quiet peer is one echo and one Errno.Io")

    quiet = stack.Stack()
    quiet.peer_quiet = True
    quiet_handle = quiet.net_bind(9999)
    ping_id = quiet.exchange.publish_request(stack.APP_PING, 0, 0, PEER_IP, b"quiet-body")
    quiet._drain_requests()
    require(quiet.exchange.req_read == quiet.exchange.req_write, "the ping stayed at the request head")
    require(quiet.ping_wait is not None and quiet.ping_wait["id"] == ping_id, "the echo was not in flight")
    during = quiet.net_send_to(quiet_handle, b"during-ping", PEER_IP, 44000)
    require(during == "sent", "a send behind a ping did not reach the TX ring")
    require(quiet.ping_wait is not None, "the send completed the ping")
    sent_udp = udp_payload_of(quiet.device_tx[-1])
    require(sent_udp is not None and sent_udp[2] == b"during-ping", "the TX frame was not the send behind the ping")
    require(quiet.expire_pings() == 1, "the deadline did not post the terminal event")
    require(quiet.expire_pings() == 0, "the deadline posted twice")
    events_after = quiet.exchange.ev_write
    require(quiet.note_ping_reply() is False, "a late echo reply was accepted")
    require(quiet.exchange.ev_write == events_after, "a late reply posted a second event")
    timed_out = quiet._take_id(ping_id)
    require(
        timed_out is not None
        and timed_out["kind"] == stack.EV_ERROR
        and timed_out["status"] == stack.ERRNO_IO,
        "the quiet ping's terminal event was not EV_ERROR / Errno.Io",
    )
    require(isinstance(quiet.net_bind(9998), int), "the next control request did not proceed")
    print("behavior: a send behind a ping reaches TX before the ping deadline")

    answered = stack.Stack()
    answered.peer_quiet = True
    answer_id = answered.exchange.publish_request(stack.APP_PING, 0, 0, PEER_IP, b"quiet-body")
    answered._drain_requests()
    require(answered.note_ping_reply() is True, "the in-flight echo was not matched")
    require(answered.note_ping_reply() is False, "a second reply was matched")
    require(answered.expire_pings() == 0, "a matched ping also timed out")
    answer = answered._take_id(answer_id)
    require(
        answer is not None and answer["kind"] == stack.EV_PING_REPLY and answer["payload"] == b"quiet-body",
        "the matched echo was not the one terminal reply",
    )
    require(answered.exchange.ev_write == 1, "success posted more than one event")
    print("behavior: one echo reply is the only terminal event")


def udp_frame_with_checksum(payload, destination_port, checksum):
    udp = bytearray(stack.build_udp(44000, destination_port, payload))
    udp[6] = (checksum >> 8) & 0xFF
    udp[7] = checksum & 0xFF
    ip = stack.build_ipv4(17, PEER_IP, OUR_IP, bytes(udp))
    ethernet = stack.build_ethernet(OUR_MAC, PEER_MAC, ip)
    return stack.device_frame(ethernet)


if __name__ == "__main__":
    run()
