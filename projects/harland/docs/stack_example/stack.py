"""Host traversal of the designed Harland path.

A device frame enters at the ring-1 driver, crosses the frame ring into the
ring-2 service, and comes out of ``net_recv_from`` or ``net_read``. An
application send takes the reverse path and leaves as a device frame.

This module does not boot the kernel. It follows the rules in
``RING1_DRIVER.md`` and ``RING2_NET.md``. The wait-set, private-index, and
one-copy descriptor helpers are explicit interleavings of those rules. This
process has one thread, so the ordering is written out rather than raced.
"""

import struct

VIRTIO_HDR = 12
DEPTH = 256
DATA = 1
SPACE = 2
PEER_CLOSE = 4
DRIVER_GONE = 8
LINK = 16
ATTACH = 64
USER_EVENT_BITS = DATA | SPACE
CAP_RIGHT_PUBLISH = 4096
INBOX_DEPTH = 8
U64_MAX = (1 << 64) - 1
APP_DEPTH = 32
APP_SLOT = 2048
APP_REGION = 0x23000
APP_DESC_SIZE = 32
REQ_DESC = 0x1000
EV_DESC = 0x2000
REQ_ARENA = 0x3000
EV_ARENA = 0x13000
REQ_WRITE_AT = 0x00
REQ_READ_AT = 0x40
REQ_WAKE_AT = 0x80
EV_WRITE_AT = 0x100
EV_READ_AT = 0x140
EV_WAKE_AT = 0x180
APP_BIND = 1
APP_SEND_TO = 2
APP_PING = 4
APP_CLOSE = 5
APP_CONNECT = 6
APP_WRITE = 7
EV_DATAGRAM = 16
EV_PING_REPLY = 17
EV_BOUND = 18
EV_CLOSED = 19
EV_ERROR = 20
EV_STREAM = 21
REQUEST_KINDS = {APP_BIND, APP_SEND_TO, APP_PING, APP_CLOSE, APP_CONNECT, APP_WRITE}
EVENT_KINDS = {EV_DATAGRAM, EV_PING_REPLY, EV_BOUND, EV_CLOSED, EV_ERROR, EV_STREAM}
ERRNO_AGAIN = -11
ERRNO_EXIST = -17
ERRNO_NODEV = -19
ERRNO_INVAL = -22
ERRNO_NOSYS = -38
EPHEMERAL_MIN = 49152
EPHEMERAL_MAX = 65535
APP_DESC_FMT = "<HHIIHh4sIII"


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

    def _try_reclaim(self):
        if self.retired and not self.mappings:
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

    def return_from_park(self):
        """The park return consumes the latch. The next call is not the same interrupt."""
        if self.latched != self.seen:
            self.seen = self.latched
            return "irq"
        return "deadline"


class PeerEnd:
    """One mapping's latch. A notify posts to the other mapping, not to a wait call."""

    def __init__(self, handle):
        self.handle = handle
        self.latch = 0
        self.peer = None
        self.attached = True


def bind_peers(left, right):
    left.peer = right
    right.peer = left


def shm_notify(end, bits):
    """Userspace may post DATA and SPACE onto the peer mapping. Kernel bits are refused."""
    if bits == 0 or (bits & ~USER_EVENT_BITS) != 0:
        return "inval"
    if end.peer is None or not end.peer.attached:
        return "nodev"
    end.peer.latch |= bits
    return "ok"


def kernel_post(end, bits):
    end.latch |= bits


class ProcessWait:
    """Listed sources plus an inbox that is scanned even when the list is empty."""

    def __init__(self, irq=None):
        self.irq = irq
        self.inbox = []
        self.reap = False

    def post_inbox(self, handle, bits):
        if len(self.inbox) >= INBOX_DEPTH:
            return False
        self.inbox.append((handle, bits))
        return True

    def wait(self, sources, out_cap, deadline_passed):
        """Return ``(code, events)``. ``sources`` is ``(handle, mask, end)``.

        Code 0 includes the IRQ. Code 2 is shm or inbox events and no IRQ.
        Code 1 is the deadline. ``repark`` means a wake matched nothing and
        the deadline has not passed. ``reap`` does not park again.
        """
        events = []
        irq_hit = False
        if self.irq is not None and self.irq.latched != self.irq.seen and len(events) < out_cap:
            self.irq.seen = self.irq.latched
            events.append((self.irq.name, DATA))
            irq_hit = True
        for handle, mask, end in sources:
            if len(events) >= out_cap:
                break
            bits = end.latch & mask
            if bits:
                end.latch &= ~bits
                events.append((handle, bits))
        while self.inbox and len(events) < out_cap:
            events.append(self.inbox.pop(0))
        if events:
            return (0 if irq_hit else 2, events)
        if self.reap:
            return ("reap", [])
        if deadline_passed:
            return (1, [])
        return ("repark", [])


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
    total = (ip_header[2] << 8) | ip_header[3]
    if header_len < 20 or total < header_len or len(ip_header) < total:
        return None
    if ip_checksum(ip_header[:header_len]) != ip_header[10:12]:
        return None
    protocol = ip_header[9]
    source = ip_header[12:16]
    destination = ip_header[16:20]
    body = ip_header[header_len:total]
    return protocol, source, destination, body


def inet_checksum(data):
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for index in range(0, len(data), 2):
        total += (data[index] << 8) + data[index + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def udp_checksum(source, destination, udp):
    """Checksum of one UDP datagram. A zero field means the sender sent none."""
    header = bytearray(udp)
    header[6] = 0
    header[7] = 0
    pseudo = source + destination + bytes((0, 17)) + struct.pack("!H", len(udp))
    return inet_checksum(pseudo + bytes(header))


def parse_udp(body, source=None, destination=None):
    if len(body) < 8:
        return None
    source_port, destination_port, length, checksum = struct.unpack("!HHHH", body[:8])
    if length < 8 or len(body) < length:
        return None
    datagram = body[:length]
    if checksum != 0:
        if source is None or destination is None:
            return None
        if udp_checksum(source, destination, datagram) != checksum:
            return None
    return source_port, destination_port, datagram[8:]


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
    """Pages stay while the other mapping is live. A replacement does not wait for an ack."""
    obj = ShmObject(1, ["frame-pages"])
    obj.map("driver", 0x1000)
    obj.map("service", 0x2000)
    observed = []
    if which == "driver-first":
        dying, survivor = "driver", "service"
    elif which == "service-first":
        dying, survivor = "service", "driver"
    else:
        raise ValueError(which)
    obj.detach(dying)
    obj.retire()
    observed.append(obj.pages_allocated)
    replacement = ShmObject(obj.object_id + 1, ["replacement"])
    observed.append(obj.pages_allocated and replacement.object_id != obj.object_id)
    obj.detach(survivor)
    observed.append(obj.pages_allocated)
    return observed


def hung_peer_timeout():
    """A peer that never detaches is unmapped, and the replacement already exists."""
    old = ShmObject(1, ["old-pages"])
    old.map("driver", 0x1000)
    old.map("service", 0x2000)
    old.detach("service")
    old.retire()
    replacement = ShmObject(2, ["new-pages"])
    still_held = old.pages_allocated
    old.detach("driver")
    return {
        "held_until_unmap": still_held,
        "reclaimed": not old.pages_allocated,
        "replacement_id": replacement.object_id,
    }


class IndexSide:
    """The consumer's own index is private. The shared copy is what the peer can rewrite."""

    def __init__(self):
        self.private_read = 4
        self.shared_read = 4
        self.peer_write = 6

    def peer_rewrites_our_index(self, value):
        self.shared_read = value

    def distance(self):
        return occupancy(self.peer_write, self.private_read)


def copy_desc_once(shared):
    """Validate the private copy. A later store to the shared descriptor does not change it."""
    copied_length = shared["length"]
    shared["length"] = 2048 + 50
    if copied_length < 1 or copied_length > 2048:
        return None
    return copied_length


def tx_publish_races_park():
    """The notify lands on the driver's mapping before the park, so the wait does not use the deadline."""
    ring = FrameRing()
    if ring.take() is not None:
        raise RuntimeError("a new ring was not empty")
    driver = PeerEnd(1)
    service = PeerEnd(1)
    bind_peers(driver, service)
    wait = ProcessWait()
    if not ring.publish(b"tx-race"):
        return False
    if shm_notify(service, DATA) != "ok" or driver.latch != DATA:
        return False
    code, events = wait.wait([(1, DATA, driver)], 8, False)
    return code == 2 and events == [(1, DATA)] and driver.latch == 0 and ring.take() == b"tx-race"


def service_wait_returns_every_hot_source():
    """One call copies the frame object and a later exchange. It does not stop at the first."""
    frame = PeerEnd(1)
    quiet = PeerEnd(10)
    hot = PeerEnd(11)
    bind_peers(frame, PeerEnd(101))
    bind_peers(quiet, PeerEnd(110))
    bind_peers(hot, PeerEnd(111))
    if shm_notify(frame.peer, DATA) != "ok" or shm_notify(hot.peer, DATA) != "ok":
        return False
    wait = ProcessWait()
    code, events = wait.wait([(1, DATA, frame), (10, DATA, quiet), (11, DATA, hot)], 8, False)
    return code == 2 and events == [(1, DATA), (11, DATA)]


def idle_service_attaches():
    """A service with no exchanges still receives every pending attach."""
    wait = ProcessWait()
    if not wait.post_inbox(10, ATTACH) or not wait.post_inbox(11, ATTACH):
        return False
    code, events = wait.wait([], 8, False)
    return code == 2 and events == [(10, ATTACH), (11, ATTACH)]


def replacement_handle_for_driver():
    """After PEER_CLOSE, the next wait delivers the new frame handle from the inbox."""
    old = PeerEnd(1)
    kernel_post(old, PEER_CLOSE)
    wait = ProcessWait()
    code, events = wait.wait([(1, PEER_CLOSE, old)], 8, False)
    if code != 2 or events != [(1, PEER_CLOSE)]:
        return False
    if not wait.post_inbox(2, ATTACH):
        return False
    code, events = wait.wait([], 8, False)
    return code == 2 and events == [(2, ATTACH)]


def user_lifecycle_bit_refused():
    """An app cannot post PEER_CLOSE. The service stays attached."""
    service = PeerEnd(8)
    app = PeerEnd(8)
    bind_peers(service, app)
    if shm_notify(app, PEER_CLOSE) != "inval":
        return False
    return service.latch == 0 and service.attached


def empty_wake_reparks():
    """A wake that matches nothing is not the deadline while the deadline is still ahead."""
    end = PeerEnd(1)
    wait = ProcessWait()
    early, early_events = wait.wait([(1, DATA, end)], 8, False)
    late, late_events = wait.wait([(1, DATA, end)], 8, True)
    return early == "repark" and early_events == [] and late == 1 and late_events == []


def reap_skips_repark():
    """PROC_REAP returns toward the iret tail instead of parking with no event."""
    wait = ProcessWait()
    wait.reap = True
    code, events = wait.wait([], 8, False)
    return code == "reap" and events == []


def arp_observe(cache, opcode, sender_ip, sender_mac, target_ip, our_ip, pending):
    """Update an existing entry. A request adds only when we are the target.

    A reply adds only when a request for that sender is outstanding. An
    unsolicited reply does not create an entry.
    """
    if sender_ip in cache:
        cache[sender_ip] = sender_mac
        return "updated"
    if opcode == "request" and target_ip == our_ip:
        cache[sender_ip] = sender_mac
        return "added"
    if opcode == "reply" and sender_ip in pending:
        cache[sender_ip] = sender_mac
        return "added"
    return "ignored"


def icmp_echo_answered(dest_ip, dest_mac, checksum_ok):
    if not checksum_ok:
        return False
    if dest_ip == bytes((255, 255, 255, 255)) or dest_mac == (b"\xff" * 6):
        return False
    return True


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


def encode_app_desc(kind, req_id, handle, port, status, addr, length, arena_off):
    """One AppDesc. flags and _pad are zero. addr is four IPv4 bytes."""
    if addr is None:
        addr = b"\x00\x00\x00\x00"
    return struct.pack(
        APP_DESC_FMT,
        kind,
        0,
        req_id,
        handle,
        port,
        status,
        bytes(addr),
        length,
        arena_off,
        0,
    )


def decode_app_desc(raw, seq):
    """Private copy of one slot. A bad flags, pad, length, offset, or kind is None."""
    if len(raw) != APP_DESC_SIZE:
        return None
    kind, flags, req_id, handle, port, status, addr, length, arena_off, pad = struct.unpack(
        APP_DESC_FMT, raw
    )
    expected = (seq & (APP_DEPTH - 1)) * APP_SLOT
    if flags != 0 or pad != 0 or arena_off != expected or length > APP_SLOT:
        return None
    if kind not in REQUEST_KINDS and kind not in EVENT_KINDS:
        return None
    return {
        "kind": kind,
        "flags": flags,
        "id": req_id,
        "handle": handle,
        "port": port,
        "status": status,
        "addr": addr,
        "length": length,
        "arena_off": arena_off,
    }


def build_icmp_echo(payload):
    header = bytearray(8)
    header[0] = 8
    body = bytes(header) + payload
    folded = inet_checksum(body)
    header[2] = (folded >> 8) & 0xFF
    header[3] = folded & 0xFF
    return bytes(header) + payload


class AppExchange:
    """The 0x23000 app region. Each side keeps the index it owns in private fields."""

    def __init__(self):
        self.region = bytearray(APP_REGION)
        self.req_write = 0
        self.req_read = 0
        self.ev_write = 0
        self.ev_read = 0
        self.next_id = 1
        self.closed = False

    def _store_u64(self, offset, value):
        self.region[offset:offset + 8] = struct.pack("<Q", value)

    def _store_u32(self, offset, value):
        self.region[offset:offset + 4] = struct.pack("<I", value & 0xFFFFFFFF)

    def publish_request(self, kind, handle, port, addr, payload):
        if self.closed:
            return None
        if payload is None:
            payload = b""
        if len(payload) > APP_SLOT:
            return None
        distance = self.req_write - self.req_read
        if distance > APP_DEPTH:
            self.closed = True
            return None
        if distance == APP_DEPTH:
            return "full"
        seq = self.req_write
        slot = seq & (APP_DEPTH - 1)
        arena_off = slot * APP_SLOT
        start = REQ_ARENA + arena_off
        self.region[start:start + APP_SLOT] = b"\xff" * APP_SLOT
        if payload:
            self.region[start:start + len(payload)] = payload
        req_id = self.next_id
        self.next_id += 1
        desc = encode_app_desc(kind, req_id, handle, port, 0, addr, len(payload), arena_off)
        at = REQ_DESC + slot * APP_DESC_SIZE
        self.region[at:at + APP_DESC_SIZE] = desc
        self.req_write += 1
        self._store_u64(REQ_WRITE_AT, self.req_write)
        self._store_u32(REQ_WAKE_AT, self.req_write)
        return req_id

    def take_request(self):
        if self.req_read == self.req_write:
            return None
        seq = self.req_read
        raw = self.request_desc_bytes(seq)
        self.req_read += 1
        self._store_u64(REQ_READ_AT, self.req_read)
        desc = decode_app_desc(raw, seq)
        if desc is None:
            return ("bad", None, b"")
        return ("ok", desc, self.request_payload(desc))

    def publish_event(self, kind, req_id, handle, port, addr, status, payload):
        if self.closed:
            return None
        if payload is None:
            payload = b""
        if len(payload) > APP_SLOT:
            return None
        distance = self.ev_write - self.ev_read
        if distance > APP_DEPTH:
            self.closed = True
            return None
        if distance == APP_DEPTH:
            return "full"
        seq = self.ev_write
        slot = seq & (APP_DEPTH - 1)
        arena_off = slot * APP_SLOT
        start = EV_ARENA + arena_off
        self.region[start:start + APP_SLOT] = b"\xff" * APP_SLOT
        if payload:
            self.region[start:start + len(payload)] = payload
        desc = encode_app_desc(kind, req_id, handle, port, status, addr, len(payload), arena_off)
        at = EV_DESC + slot * APP_DESC_SIZE
        self.region[at:at + APP_DESC_SIZE] = desc
        self.ev_write += 1
        self._store_u64(EV_WRITE_AT, self.ev_write)
        self._store_u32(EV_WAKE_AT, self.ev_write)
        return req_id

    def take_event(self):
        if self.ev_read == self.ev_write:
            return None
        seq = self.ev_read
        raw = self.event_desc_bytes(seq)
        self.ev_read += 1
        self._store_u64(EV_READ_AT, self.ev_read)
        desc = decode_app_desc(raw, seq)
        if desc is None:
            return ("bad", None, b"")
        return ("ok", desc, self.event_payload(desc))

    def request_desc_bytes(self, seq):
        slot = seq & (APP_DEPTH - 1)
        at = REQ_DESC + slot * APP_DESC_SIZE
        return bytes(self.region[at:at + APP_DESC_SIZE])

    def event_desc_bytes(self, seq):
        slot = seq & (APP_DEPTH - 1)
        at = EV_DESC + slot * APP_DESC_SIZE
        return bytes(self.region[at:at + APP_DESC_SIZE])

    def request_payload(self, desc):
        start = REQ_ARENA + desc["arena_off"]
        return bytes(self.region[start:start + desc["length"]])

    def event_payload(self, desc):
        start = EV_ARENA + desc["arena_off"]
        return bytes(self.region[start:start + desc["length"]])


class Stack:
    """One NIC, one service, one app. Frames are Ethernet after the virtio header."""

    def __init__(self):
        self.rx = FrameRing()
        self.tx = FrameRing()
        self.pending_tx = []
        self.device_tx = []
        self.stream_inbox = []
        self.stream_expected = 1000
        self.stream_send_seq = 1000
        self.established = False
        self.our_mac = bytes.fromhex("525400123456")
        self.peer_mac = bytes.fromhex("525400aabbcc")
        self.our_ip = bytes((10, 0, 2, 15))
        self.rx_notifies = 0
        self.space_notifies = 0
        self.exchange = AppExchange()
        self.port_handles = {}
        self.handle_ports = {}
        self.next_handle = 1
        self.ephemeral_next = EPHEMERAL_MIN
        self.attached = False
        self.mapped = False
        self.address_published = True
        self.service_present = True
        self.attach_handle = 0
        self.tx_result = None

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
            protocol, source, destination_ip, body = parsed
            if protocol == 17:
                udp = parse_udp(body, source, destination_ip)
                if udp is None:
                    continue
                source_port, destination_port, payload = udp
                handle = self.port_handles.get(destination_port)
                if handle is not None:
                    self.exchange.publish_event(
                        EV_DATAGRAM, 0, handle, source_port, source, 0, payload
                    )
            elif protocol == 6 and self.established:
                tcp = parse_tcp(body, self.stream_expected)
                if tcp is None:
                    continue
                _source_port, _destination_port, payload = tcp
                if payload:
                    self.stream_inbox.append(payload)
                    self.stream_expected += len(payload)

    def net_attach(self):
        """Syscall 228. NoDev when the service is not there. One app in this host."""
        if not self.service_present:
            return ERRNO_NODEV
        self.attached = True
        self.attach_handle = 1
        return self.attach_handle

    def shm_map(self, handle):
        """Syscall 227. Maps this app's exchange and nothing else."""
        if not self.attached or handle != self.attach_handle:
            return ERRNO_NODEV
        self.mapped = True
        return self.exchange.region

    def net_addr(self):
        """Syscall 225. NoDev while the address generation is unpublished."""
        if not self.address_published or not self.service_present:
            return ERRNO_NODEV
        return {"address": self.our_ip, "configured": 1}

    def net_bind(self, port):
        req_id = self.exchange.publish_request(APP_BIND, 0, port, b"\x00\x00\x00\x00", b"")
        if req_id is None or req_id == "full":
            return ERRNO_AGAIN if req_id == "full" else ERRNO_INVAL
        self._drain_requests()
        event = self._take_id(req_id)
        if event is None or event["kind"] != EV_BOUND or event["status"] != 0:
            if event is not None and event["status"] != 0:
                return event["status"]
            return ERRNO_INVAL
        return event["handle"]

    def net_recv_from(self, handle):
        while True:
            item = self.exchange.take_event()
            if item is None:
                return None
            if item[0] != "ok":
                continue
            desc, payload = item[1], item[2]
            if desc["handle"] != handle:
                continue
            if desc["kind"] == EV_DATAGRAM and desc["status"] == 0:
                return (payload, desc["addr"], desc["port"])
            if desc["kind"] == EV_ERROR:
                return None

    def net_send_to(self, handle, payload, address, port):
        if len(payload) > APP_SLOT:
            return None
        req_id = self.exchange.publish_request(APP_SEND_TO, handle, port, address, payload)
        if req_id is None:
            return None
        if req_id == "full":
            return "full"
        self.tx_result = None
        self._drain_requests()
        if self.tx_result is None:
            return ERRNO_INVAL
        return self.tx_result

    def net_ping(self, address, payload):
        req_id = self.exchange.publish_request(APP_PING, 0, 0, address, payload)
        if not isinstance(req_id, int):
            return ERRNO_INVAL
        self._drain_requests()
        event = self._take_id(req_id)
        if event is None:
            return ERRNO_INVAL
        if event["kind"] == EV_PING_REPLY and event["status"] == 0:
            return event["payload"]
        return event["status"]

    def net_close(self, handle):
        req_id = self.exchange.publish_request(APP_CLOSE, handle, 0, b"\x00\x00\x00\x00", b"")
        if not isinstance(req_id, int):
            return ERRNO_INVAL
        self._drain_requests()
        event = self._take_id(req_id)
        if event is None or event["kind"] != EV_CLOSED or event["status"] != 0:
            if event is not None and event["status"] != 0:
                return event["status"]
            return ERRNO_INVAL
        return 0

    def submit_kind(self, kind):
        """Publish one request kind and return the status the service posts."""
        req_id = self.exchange.publish_request(kind, 0, 0, b"\x00\x00\x00\x00", b"")
        if not isinstance(req_id, int):
            return ERRNO_INVAL
        self._drain_requests()
        event = self._take_id(req_id)
        if event is None:
            return ERRNO_INVAL
        return event["status"]

    def _take_id(self, req_id):
        item = self.exchange.take_event()
        if item is None or item[0] != "ok":
            return None
        desc, payload = item[1], item[2]
        if desc["id"] != req_id:
            return None
        desc["payload"] = payload
        return desc

    def _drain_requests(self):
        while True:
            item = self.exchange.take_request()
            if item is None:
                return
            if item[0] != "ok":
                continue
            self._dispatch(item[1], item[2])

    def _error(self, desc, status):
        handle = 0 if desc["kind"] == APP_BIND else desc["handle"]
        self.exchange.publish_event(
            EV_ERROR, desc["id"], handle, desc["port"], desc["addr"], status, b""
        )

    def _assign_port(self, requested):
        if requested != 0:
            if requested in self.port_handles:
                return None
            return requested
        port = self.ephemeral_next
        while port <= EPHEMERAL_MAX:
            if port not in self.port_handles:
                self.ephemeral_next = port + 1
                return port
            port += 1
        return None

    def _dispatch(self, desc, payload):
        if desc["id"] == 0 or desc["status"] != 0:
            return
        kind = desc["kind"]
        if kind in (APP_CONNECT, APP_WRITE):
            self._error(desc, ERRNO_NOSYS)
            return
        if kind == APP_BIND:
            port = self._assign_port(desc["port"])
            if port is None:
                status = ERRNO_AGAIN if desc["port"] == 0 else ERRNO_EXIST
                self._error(desc, status)
                return
            handle = self.next_handle
            self.next_handle += 1
            self.port_handles[port] = handle
            self.handle_ports[handle] = port
            self.exchange.publish_event(
                EV_BOUND, desc["id"], handle, port, b"\x00\x00\x00\x00", 0, b""
            )
            return
        if kind == APP_SEND_TO:
            source_port = self.handle_ports.get(desc["handle"])
            if source_port is None or desc["handle"] == 0:
                self._error(desc, ERRNO_INVAL)
                return
            ethernet = build_ethernet(
                self.peer_mac,
                self.our_mac,
                build_ipv4(
                    17,
                    self.our_ip,
                    desc["addr"],
                    build_udp(source_port, desc["port"], payload),
                ),
            )
            self.tx_result = self._transmit(ethernet)
            return
        if kind == APP_PING:
            if not icmp_echo_answered(desc["addr"], self.peer_mac, True):
                self._error(desc, ERRNO_INVAL)
                return
            echo = build_icmp_echo(payload)
            ethernet = build_ethernet(
                self.peer_mac,
                self.our_mac,
                build_ipv4(1, self.our_ip, desc["addr"], echo),
            )
            self._transmit(ethernet)
            self.exchange.publish_event(
                EV_PING_REPLY, desc["id"], 0, 0, desc["addr"], 0, payload
            )
            return
        if kind == APP_CLOSE:
            port = self.handle_ports.pop(desc["handle"], None)
            if port is None or desc["handle"] == 0:
                self._error(desc, ERRNO_INVAL)
                return
            self.port_handles.pop(port, None)
            self.exchange.publish_event(
                EV_CLOSED, desc["id"], desc["handle"], port, b"\x00\x00\x00\x00", 0, b""
            )

    def _tool_ready(self):
        attached = self.net_attach()
        if attached == ERRNO_NODEV:
            return ERRNO_NODEV
        mapped = self.shm_map(attached)
        if mapped == ERRNO_NODEV:
            return ERRNO_NODEV
        if self.net_addr() == ERRNO_NODEV:
            return ERRNO_NODEV
        return None

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


def tool_udp_send(host, payload, address, port):
    """udp-send: attach, map, read the address, bind port 0, send once, close."""
    ready = host._tool_ready()
    if ready is not None:
        return ready
    handle = host.net_bind(0)
    if not isinstance(handle, int) or handle <= 0:
        return handle
    result = host.net_send_to(handle, payload, address, port)
    closed = host.net_close(handle)
    if closed != 0:
        return closed
    return result


def tool_udp_recv_once(host, local_port, frame):
    """udp-recv: bind the given port, take one datagram, close."""
    ready = host._tool_ready()
    if ready is not None:
        return ready
    handle = host.net_bind(local_port)
    if not isinstance(handle, int) or handle <= 0:
        return handle
    host.deliver_device_frame(frame)
    got = host.net_recv_from(handle)
    closed = host.net_close(handle)
    if closed != 0:
        return closed
    return got


def tool_ping(host, address, payload):
    """ping: one echo. The reply bytes are the EV_PING_REPLY payload."""
    ready = host._tool_ready()
    if ready is not None:
        return ready
    return host.net_ping(address, payload)
