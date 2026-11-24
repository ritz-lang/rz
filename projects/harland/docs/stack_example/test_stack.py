"""Drive the host stack traversal and the eight re-review behaviors.

The log names each behavior and prints the datagram and stream bytes at the
userspace calls and inside the device frame on send.
"""

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


def run():
    host = stack.Stack()
    host.net_bind(9999)
    host.deliver_device_frame(udp_device_frame(DATAGRAM, 9999))
    received = host.net_recv_from(9999)
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

    host.net_send_to(9999, DATAGRAM, PEER_IP, 44000)
    require(host.device_tx, "datagram send produced no device frame")
    datagram_frame = host.device_tx[-1]
    require(DATAGRAM in datagram_frame, "device frame does not carry the datagram bytes")
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
    filled = space.fill_tx()
    require(filled == stack.DEPTH, "TX ring did not fill")
    require(space.net_send_to(9999, PENDING, PEER_IP, 44000) == "queued", "full ring did not queue the send")
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


if __name__ == "__main__":
    run()
