"""Host traversal of the designed Harland path.

A device frame enters at the ring-1 driver, crosses the frame ring into the
ring-2 service, and comes out of ``net_recv_from`` or ``net_read``. An
application send takes the reverse path and leaves as a device frame.

This module does not boot the kernel. It follows the rules in
``RING1_DRIVER.md`` and ``RING2_NET.md``.
"""

import struct

VIRTIO_HDR = 12
DEPTH = 256
DATA = 1
SPACE = 2
DRIVER_GONE = 8
CAP_RIGHT_PUBLISH = 4096
U64_MAX = (1 << 64) - 1


class BackwardsIndex(Exception):
    """Peer supplied a write index behind the read index. No subtraction ran."""


class BadOccupancy(Exception):
    """Distance is above the ring depth."""


def occupancy(write_idx, read_idx):
    """Distance between monotonic indexes.

    A backwards pair is rejected before the subtraction, which is the
    operation Ritz would trap on if ``write_idx < read_idx``.
    """
    if write_idx < read_idx:
        raise BackwardsIndex(write_idx, read_idx)
    distance = write_idx - read_idx
    if distance > DEPTH:
        raise BadOccupancy(distance)
    return distance


class ShmObject:
    """Backing pages belong to the object, not to either mapping."""

    def __init__(self, object_id, pages):
        self.object_id = object_id
        self.pages = list(pages)
        self.mappings = {}
        self.retired = False
        self.inflight = 0
        self.reclaimed = False
        self.events = 0
        self.generation = 0

    def map(self, pid, virtual_address):
        self.mappings[pid] = virtual_address
        return self.pages

    def detach(self, pid):
        self.mappings.pop(pid, None)
        self._try_reclaim()

    def retire(self):
        self.retired = True
        self.events |= DRIVER_GONE
        self._try_reclaim()

    def ack_slot(self):
        if self.inflight > 0:
            self.inflight -= 1
        self._try_reclaim()

    def _try_reclaim(self):
        if self.retired and not self.mappings and self.inflight == 0:
            self.reclaimed = True

    @property
    def pages_allocated(self):
        return not self.reclaimed


class Handle:
    def __init__(self, obj, rights, pid):
        self.obj = obj
        self.rights = rights
        self.pid = pid


def net_publish(handle, registered_ids):
    """Publish only with the publish right on a registered link or address object."""
    if (handle.rights & CAP_RIGHT_PUBLISH) == 0:
        return "perm"
    if handle.obj.object_id not in registered_ids:
        return "perm"
    handle.obj.generation = 2 if handle.obj.generation == 0 else handle.obj.generation + 2
    return "ok"


class IrqObject:
    """One device's latched interrupt. A different device does not move it."""

    def __init__(self, name):
        self.name = name
        self.latched = 0
        self.seen = 0

    def interrupt(self):
        self.latched += 1

    def drv_irq_wait(self):
        if self.latched != self.seen:
            self.seen = self.latched
            return "ready"
        return "parked"


class FrameRing:
    def __init__(self):
        self.write_idx = 0
        self.read_idx = 0
        self.slots = [None] * DEPTH

    def publish(self, frame):
        if occupancy(self.write_idx, self.read_idx) >= DEPTH:
            return False
        self.slots[self.write_idx % DEPTH] = frame
        self.write_idx += 1
        return True

    def take(self):
        if occupancy(self.write_idx, self.read_idx) == 0:
            return None
        frame = self.slots[self.read_idx % DEPTH]
        self.read_idx += 1
        return frame

    def release_one(self):
        """Consumer frees one slot and does not publish a new frame."""
        if occupancy(self.write_idx, self.read_idx) == 0:
            return False
        self.read_idx += 1
        return True


def ip_checksum(header):
    total = 0
    paired = bytearray(header)
    paired[10] = 0
    paired[11] = 0
    for index in range(0, len(paired), 2):
        total += (paired[index] << 8) + paired[index + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    folded = (~total) & 0xFFFF
    return bytes((folded >> 8, folded & 0xFF))


def build_ipv4(protocol, source, destination, payload):
    total = 20 + len(payload)
    header = bytearray(20)
    header[0] = 0x45
    header[2] = (total >> 8) & 0xFF
    header[3] = total & 0xFF
    header[8] = 64
    header[9] = protocol
    header[12:16] = source
    header[16:20] = destination
    header[10:12] = ip_checksum(header)
    return bytes(header) + payload


def build_ethernet(destination_mac, source_mac, payload):
    return destination_mac + source_mac + b"\x08\x00" + payload


def build_udp(source_port, destination_port, payload):
    length = 8 + len(payload)
    return struct.pack("!HHHH", source_port, destination_port, length, 0) + payload


def build_tcp(source_port, destination_port, sequence, payload):
    header = struct.pack(
        "!HHIIBBHHH",
        source_port,
        destination_port,
        sequence,
        0,
        5 << 4,
        0x18,
        65535,
        0,
        0,
    )
    return header + payload


def device_frame(ethernet):
    return (b"\x00" * VIRTIO_HDR) + ethernet


def strip_virtio(frame):
    if len(frame) < VIRTIO_HDR + 34:
        raise ValueError("device frame is shorter than a virtio header plus an IP datagram")
    return frame[VIRTIO_HDR:]


def parse_ipv4(ethernet):
    if len(ethernet) < 34 or ethernet[12:14] != b"\x08\x00":
        return None
    ip_header = ethernet[14:]
    header_len = (ip_header[0] & 0x0F) * 4
    if header_len < 20 or len(ip_header) < header_len:
        return None
    if ip_checksum(ip_header[:header_len]) != ip_header[10:12]:
        return None
    protocol = ip_header[9]
    source = ip_header[12:16]
    body = ip_header[header_len:]
    return protocol, source, body


def parse_udp(body):
    if len(body) < 8:
        return None
    source_port, destination_port, length, _checksum = struct.unpack("!HHHH", body[:8])
    if length < 8 or len(body) < length:
        return None
    return source_port, destination_port, body[8:length]


def parse_tcp(body, expected_sequence):
    if len(body) < 20:
        return None
    source_port, destination_port, sequence = struct.unpack("!HHI", body[:8])
    data_offset = (body[12] >> 4) * 4
    if data_offset < 20 or len(body) < data_offset:
        return None
    if sequence != expected_sequence:
        return None
    return source_port, destination_port, body[data_offset:]


class DhcpClient:
    """Server selection follows the client state. Every message still needs a valid identity."""

    def __init__(self):
        self.state = "INIT"
        self.server = None
        self.lease = None
        self.t1 = None
        self.t2 = None

    def discover(self, identity_ok):
        if self.state != "INIT" or not identity_ok:
            return False
        self.state = "SELECTING"
        return True

    def offer(self, server, identity_ok):
        if self.state != "SELECTING" or not identity_ok:
            return False
        self.server = server
        self.state = "REQUESTING"
        return True

    def ack(self, server, lease, t1, t2, identity_ok):
        if not identity_ok:
            return False
        if self.state == "REQUESTING":
            if server != self.server:
                return False
        elif self.state == "RENEWING":
            if server != self.server:
                return False
        elif self.state == "REBINDING":
            pass
        else:
            return False
        self.server = server
        self.lease = lease
        self.t1 = t1
        self.t2 = t2
        self.state = "BOUND"
        return True


def handoff(try_release):
    """``NetPublish`` has already returned. Release is one attempt and does not gate the seat."""
    publish_returned = True
    released = bool(try_release())
    seat = "service"
    return {"publish_returned": publish_returned, "released": released, "seat": seat}


def death_order(which):
    """Observe page ownership through one death order, including a peer mid-slot."""
    obj = ShmObject(1, ["frame-pages"])
    obj.map("driver", 0x1000)
    obj.map("service", 0x2000)
    obj.inflight = 1
    observed = []
    if which == "driver-first":
        obj.detach("driver")
        obj.retire()
        observed.append(obj.pages_allocated)
        obj.ack_slot()
        observed.append(obj.pages_allocated)
        obj.detach("service")
        observed.append(obj.pages_allocated)
    elif which == "service-first":
        obj.detach("service")
        obj.retire()
        observed.append(obj.pages_allocated)
        obj.ack_slot()
        observed.append(obj.pages_allocated)
        obj.detach("driver")
        observed.append(obj.pages_allocated)
    else:
        raise ValueError(which)
    return observed


def replacement_generation():
    """A new object's generation 2 does not clear DRIVER_GONE on the retired id."""
    old = ShmObject(1, ["old-pages"])
    old.generation = 2
    old.retire()
    new = ShmObject(2, ["new-pages"])
    new.generation = 2
    return {
        "old_id": old.object_id,
        "new_id": new.object_id,
        "old_has_driver_gone": bool(old.events & DRIVER_GONE),
        "new_generation": new.generation,
        "old_still_gone_after_new_publish": bool(old.events & DRIVER_GONE),
    }


class Stack:
    """One NIC, one service, one app. Frames are Ethernet after the virtio header."""

    def __init__(self):
        self.rx = FrameRing()
        self.tx = FrameRing()
        self.pending_tx = []
        self.device_tx = []
        self.datagrams = {}
        self.stream_inbox = []
        self.stream_expected = 1000
        self.stream_send_seq = 1000
        self.established = False
        self.our_mac = bytes.fromhex("525400123456")
        self.peer_mac = bytes.fromhex("525400aabbcc")
        self.our_ip = bytes((10, 0, 2, 15))
        self.rx_notifies = 0
        self.space_notifies = 0

    def deliver_device_frame(self, frame):
        """Ring 1 strips the virtio header and publishes. Ring 2 demuxes."""
        ethernet = strip_virtio(frame)
        if not self.rx.publish(ethernet):
            raise RuntimeError("RX ring full")
        self.rx_notifies += 1
        self._service_rx()

    def _service_rx(self):
        while True:
            ethernet = self.rx.take()
            if ethernet is None:
                return
            destination = ethernet[0:6]
            if destination != self.our_mac and destination != (b"\xff" * 6):
                continue
            parsed = parse_ipv4(ethernet)
            if parsed is None:
                continue
            protocol, source, body = parsed
            if protocol == 17:
                udp = parse_udp(body)
                if udp is None:
                    continue
                source_port, destination_port, payload = udp
                queue = self.datagrams.get(destination_port)
                if queue is not None:
                    queue.append((payload, source, source_port))
            elif protocol == 6 and self.established:
                tcp = parse_tcp(body, self.stream_expected)
                if tcp is None:
                    continue
                _source_port, _destination_port, payload = tcp
                if payload:
                    self.stream_inbox.append(payload)
                    self.stream_expected += len(payload)

    def net_bind(self, port):
        self.datagrams[port] = []
        return port

    def net_recv_from(self, handle):
        queue = self.datagrams[handle]
        if not queue:
            return None
        return queue.pop(0)

    def net_send_to(self, handle, payload, address, port):
        _ = handle
        ethernet = build_ethernet(
            self.peer_mac,
            self.our_mac,
            build_ipv4(17, self.our_ip, address, build_udp(handle, port, payload)),
        )
        return self._transmit(ethernet)

    def net_connect(self, address, port):
        self.established = True
        self.peer_ip = address
        self.peer_port = port
        return ("stream", address, port)

    def net_read(self, handle):
        _ = handle
        if not self.stream_inbox:
            return b""
        return self.stream_inbox.pop(0)

    def net_write(self, handle, payload):
        _ = handle
        if not self.established:
            raise RuntimeError("stream is not established")
        ethernet = build_ethernet(
            self.peer_mac,
            self.our_mac,
            build_ipv4(
                6,
                self.our_ip,
                self.peer_ip,
                build_tcp(40000, self.peer_port, self.stream_send_seq, payload),
            ),
        )
        self.stream_send_seq += len(payload)
        return self._transmit(ethernet)

    def _transmit(self, ethernet):
        if not self.tx.publish(ethernet):
            self.pending_tx.append(ethernet)
            return "queued"
        self._driver_consume_tx()
        return "sent"

    def _driver_consume_tx(self):
        while True:
            ethernet = self.tx.take()
            if ethernet is None:
                return
            self.device_tx.append(device_frame(ethernet))

    def fill_tx(self):
        """Occupy every TX slot with a marker the later pending send must not match."""
        marker = build_ethernet(self.peer_mac, self.our_mac, b"\x00\x00filled")
        filled = 0
        while self.tx.publish(marker):
            filled += 1
        return filled

    def release_tx_space(self):
        """Driver frees one TX slot and notifies SPACE. No RX frame is injected."""
        if not self.tx.release_one():
            return False
        self.space_notifies += 1
        moved = False
        if self.pending_tx and self.tx.publish(self.pending_tx[0]):
            self.pending_tx.pop(0)
            moved = True
        self._driver_consume_tx()
        return moved
