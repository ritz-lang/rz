#!/usr/bin/env python3
"""The host end of Harland's ICMP latency gate (AGAST #4768).

tools/net_latency.sh puts the guest's virtio-net on a QEMU hub with slirp
(the guest's DHCP server) and a `-netdev dgram` port whose other end is this
process: every Ethernet frame on the hub arrives here as one UDP datagram,
and every datagram sent to QEMU's end goes onto the hub. That needs no root
and no tap, and slirp, which never forwards ICMP from the host, stays out of
the measured path.

    net_latency_wire.py --serial LOG --owner O --listen PORT --qemu PORT

waits for the kernel's "[net-latency] ready owner=O ip=A ..." line in LOG,
then sends WARMUP + COUNT ICMP echo requests to A, one at a time, each after
the previous one's reply (or its timeout) and INTERVAL later. It answers the
guest's ARP requests for the host's address while it waits. The RTT is
host-measured (time.perf_counter_ns from send to reply), so it includes
QEMU's hub and dgram hops: the same on every owner, so the gap between
owners is the guest's. It prints one JSON object: the owner, the counts and
min / median / p99 in microseconds over the COUNT timed echoes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import select
import socket
import struct
import sys
import time

ETH_IPV4 = 0x0800
ETH_ARP = 0x0806
ICMP_ECHO_REPLY = 0
ICMP_ECHO_REQUEST = 8
BROADCAST = b"\xff" * 6

# The host's identity on the guest's link: a locally administered MAC and an
# address in slirp's 10.0.2.0/24 that slirp hands to nobody.
HOST_MAC = bytes.fromhex("525400aa0001")
HOST_IP = bytes([10, 0, 2, 200])
ECHO_ID = 0x4C54

READY_RE = re.compile(
    rb"\[net-latency\] ready owner=(\S+) ip=(\d+\.\d+\.\d+\.\d+) window_ms=(\d+)"
)
DONE_RE = re.compile(
    rb"\[net-latency\] done owner=(\S+) switches=(\d+) cr3=(\d+) syscalls=(\d+)"
)
ECHOES_RE = re.compile(
    rb"\[net-latency\] echoes owner=(\S+) requests=(\d+) replies=(\d+)"
)


def checksum(data: bytes) -> int:
    """The Internet checksum (RFC 1071) of `data`."""
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def echo_request(
    src_mac: bytes,
    dst_mac: bytes,
    src_ip: bytes,
    dst_ip: bytes,
    id_: int,
    seq: int,
    body: bytes,
) -> bytes:
    """An Ethernet frame holding one ICMP echo request."""
    icmp = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, id_, seq) + body
    icmp = icmp[:2] + struct.pack("!H", checksum(icmp)) + icmp[4:]
    ip = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, 20 + len(icmp), seq, 0, 64, 1, 0, src_ip, dst_ip
    )
    ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
    return dst_mac + src_mac + struct.pack("!H", ETH_IPV4) + ip + icmp


def echo_reply_of(frame: bytes, our_ip: bytes) -> tuple[int, int] | None:
    """(identifier, sequence) if `frame` is an ICMP echo reply to `our_ip`."""
    if len(frame) < 14 + 20 + 8 or struct.unpack("!H", frame[12:14])[0] != ETH_IPV4:
        return None
    ip = frame[14:]
    ihl = (ip[0] & 0x0F) * 4
    if ip[0] >> 4 != 4 or ip[9] != 1 or ip[16:20] != our_ip or len(ip) < ihl + 8:
        return None
    icmp = ip[ihl:]
    if icmp[0] != ICMP_ECHO_REPLY:
        return None
    return struct.unpack("!HH", icmp[4:8])


def arp_reply_to(frame: bytes, our_mac: bytes, our_ip: bytes) -> bytes | None:
    """The ARP reply for `frame` if it asks who has `our_ip`, else None."""
    if len(frame) < 42 or struct.unpack("!H", frame[12:14])[0] != ETH_ARP:
        return None
    htype, ptype, hlen, plen, op, sha, spa, _tha, tpa = struct.unpack(
        "!HHBBH6s4s6s4s", frame[14:42]
    )
    if (htype, ptype, hlen, plen, op) != (1, ETH_IPV4, 6, 4, 1) or tpa != our_ip:
        return None
    arp = struct.pack("!HHBBH6s4s6s4s", 1, ETH_IPV4, 6, 4, 2, our_mac, our_ip, sha, spa)
    return sha + our_mac + struct.pack("!H", ETH_ARP) + arp


# An echo slower than this is in the tail a missed wakeup leaves (a timer
# tick, 10 ms at SCHED_HZ = 100, recovers it), not in the stack's cost.
SLOW_US = 10000.0


def summarize(rtts_us: list[float], sent: int) -> dict:
    """Counts, min / median / p99 (nearest rank) of `rtts_us`, and how many
    took longer than SLOW_US."""
    out = {"sent": sent, "received": len(rtts_us), "lost": sent - len(rtts_us)}
    if not rtts_us:
        return out
    s = sorted(rtts_us)
    n = len(s)
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    out.update(
        min_us=s[0],
        median_us=median,
        p99_us=s[math.ceil(0.99 * n) - 1],
        over_10ms=sum(1 for v in s if v > SLOW_US),
    )
    return out


def ready_lines(serial: bytes) -> list[tuple[str, str, int]]:
    """Every "[net-latency] ready" line in `serial`: (owner, ip, window_ms)."""
    return [(o.decode(), ip.decode(), int(w)) for o, ip, w in READY_RE.findall(serial)]


def done_counts(serial: bytes) -> dict[str, dict[str, int]]:
    """Each owner's window counters from the done and echoes lines."""
    out: dict[str, dict[str, int]] = {}
    for owner, sw, cr3, sc in DONE_RE.findall(serial):
        out.setdefault(owner.decode(), {}).update(
            switches=int(sw), cr3=int(cr3), syscalls=int(sc)
        )
    for owner, req, rep in ECHOES_RE.findall(serial):
        out.setdefault(owner.decode(), {}).update(requests=int(req), replies=int(rep))
    return out


class Wire:
    """One end of QEMU's dgram netdev: a UDP socket, a datagram a frame."""

    def __init__(self, listen_port: int, qemu_port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", listen_port))
        self.peer = ("127.0.0.1", qemu_port)
        self.guest_mac: bytes | None = None

    def send(self, frame: bytes) -> None:
        self.sock.sendto(frame, self.peer)

    def recv_until(self, deadline_ns: int, want: tuple[int, int] | None) -> int | None:
        """Read frames until `want`'s echo reply (its arrival time) or the
        deadline (None), answering ARP for the host on the way."""
        while True:
            left = (deadline_ns - time.perf_counter_ns()) / 1e9
            if left <= 0:
                return None
            ready, _, _ = select.select([self.sock], [], [], left)
            if not ready:
                return None
            frame = self.sock.recv(2048)
            at = time.perf_counter_ns()
            arp = arp_reply_to(frame, HOST_MAC, HOST_IP)
            if arp is not None:
                self.send(arp)
                continue
            if want is not None and echo_reply_of(frame, HOST_IP) == want:
                return at


def wait_ready(serial_path: str, owner: str, timeout_s: float) -> str | None:
    """The guest address on `owner`'s ready line, once it is in the log."""
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        with open(serial_path, "rb") as f:
            for o, ip, _w in ready_lines(f.read()):
                if o == owner:
                    return ip
        time.sleep(0.05)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--serial", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--listen", type=int, required=True)
    ap.add_argument("--qemu", type=int, required=True)
    ap.add_argument("--guest-mac", default="52:54:00:12:34:56")
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--interval-ms", type=float, default=10.0)
    ap.add_argument("--reply-timeout-ms", type=float, default=200.0)
    ap.add_argument("--ready-timeout", type=float, default=300.0)
    # The wire floor: ping this address (slirp's gateway) at once, with no
    # ready line, so the same hub and dgram hops are measured without the
    # guest in them.
    ap.add_argument(
        "--target",
        help="ping this IPv4 address now, not the owner's ready-line address",
    )
    ap.add_argument(
        "--dump", help="write each timed echo's RTT (us, send order) here, one per line"
    )
    args = ap.parse_args()

    wire = Wire(args.listen, args.qemu)
    ip = args.target or wait_ready(args.serial, args.owner, args.ready_timeout)
    if ip is None:
        print(json.dumps({"owner": args.owner, "error": "no ready line"}))
        return 1
    guest_ip = socket.inet_aton(ip)
    guest_mac = bytes.fromhex(args.guest_mac.replace(":", ""))
    body = bytes(range(56))
    rtts: list[float] = []
    for seq in range(args.warmup + args.count):
        frame = echo_request(HOST_MAC, guest_mac, HOST_IP, guest_ip, ECHO_ID, seq, body)
        sent_at = time.perf_counter_ns()
        wire.send(frame)
        got = wire.recv_until(
            sent_at + int(args.reply_timeout_ms * 1e6), (ECHO_ID, seq)
        )
        if got is not None and seq >= args.warmup:
            rtts.append((got - sent_at) / 1000.0)
        # Pace from the send, and keep answering ARP while idle.
        wire.recv_until(sent_at + int(args.interval_ms * 1e6), None)
    if args.dump:
        with open(args.dump, "w") as f:
            f.writelines(f"{v:.1f}\n" for v in rtts)
    out = {"owner": args.owner, "ip": ip, "warmup": args.warmup}
    out.update(summarize(rtts, args.count))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
