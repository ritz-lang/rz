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
    require(host.net_send_to(bound, b"x" * (stack.APP_SLOT + 1), PEER_IP, 44000) is None, "an oversize send was published")
    require(host.exchange.req_write == writes_before_oversize, "an oversize send advanced the request index")
    host.net_send_to(bound, DATAGRAM, PEER_IP, 44000)
    require(host.device_tx, "datagram send produced no device frame")
    datagram_frame = host.device_tx[-1]
    send_seq = host.exchange.req_write - 1
    raw = host.exchange.request_desc_bytes(send_seq)
    require(struct.unpack("<H", raw[0:2])[0] == stack.APP_SEND_TO, "send kind is not at byte 0")
    require(struct.unpack("<H", raw[12:14])[0] == 44000, "remote port is not at byte 12")
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


def udp_frame_with_checksum(payload, destination_port, checksum):
    udp = bytearray(stack.build_udp(44000, destination_port, payload))
    udp[6] = (checksum >> 8) & 0xFF
    udp[7] = checksum & 0xFF
    ip = stack.build_ipv4(17, PEER_IP, OUR_IP, bytes(udp))
    ethernet = stack.build_ethernet(OUR_MAC, PEER_MAC, ip)
    return stack.device_frame(ethernet)


if __name__ == "__main__":
    run()
