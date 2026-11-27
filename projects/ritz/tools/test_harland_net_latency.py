"""The ICMP latency gate's host side (AGAST #4768).

projects/harland/tools/net_latency.sh boots Harland twice (the in-kernel
stack, then the CPL-3 driver and netd) and runs net_latency_wire.py, which
speaks raw Ethernet to the guest over QEMU's dgram netdev: it answers the
guest's ARP for the host's address, sends ICMP echo requests and times the
matching replies. The script is local-only (not CI); these tests pin the
pieces a wrong number would come from, without QEMU:

  * the frames: a valid IPv4 + ICMP checksum on every echo request, an ARP
    reply only for the host's own address, and only a reply with the sent
    identifier and sequence counts as one;
  * the statistics: min / median / p99 by nearest rank, warm-up excluded;
  * the serial log: the kernel's [net-latency] ready / done / echoes lines;
  * the tail: how many timed echoes took longer than a threshold.

Runs in `make tools-unit`.
"""

import importlib.util
import struct
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

WIRE = Path(__file__).resolve().parents[2] / "harland" / "tools" / "net_latency_wire.py"


@pytest.fixture(scope="module")
def wire():
    spec = importlib.util.spec_from_file_location("harland_net_latency_wire", WIRE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


HOST_MAC = bytes.fromhex("525400aa0001")
GUEST_MAC = bytes.fromhex("525400123456")
HOST_IP = bytes([10, 0, 2, 200])
GUEST_IP = bytes([10, 0, 2, 15])


def _sum16(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return total


def test_echo_request_has_valid_checksums(wire):
    frame = wire.echo_request(
        HOST_MAC, GUEST_MAC, HOST_IP, GUEST_IP, 0x4C54, 7, b"x" * 56
    )
    assert frame[0:6] == GUEST_MAC and frame[6:12] == HOST_MAC
    assert frame[12:14] == b"\x08\x00"
    ip = frame[14:34]
    assert ip[9] == 1 and ip[12:16] == HOST_IP and ip[16:20] == GUEST_IP
    assert struct.unpack("!H", ip[2:4])[0] == 20 + 8 + 56
    assert _sum16(ip) == 0xFFFF
    icmp = frame[34:]
    assert icmp[0] == 8 and struct.unpack("!HH", icmp[4:8]) == (0x4C54, 7)
    assert _sum16(icmp) == 0xFFFF


def _reply(id_, seq, src=GUEST_IP, dst=HOST_IP, kind=0):
    icmp = struct.pack("!BBHHH", kind, 0, 0, id_, seq) + b"x" * 8
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(icmp), 0, 0, 64, 1, 0, src, dst)
    return HOST_MAC + GUEST_MAC + b"\x08\x00" + ip + icmp


def test_echo_reply_matches_only_its_echo(wire):
    assert wire.echo_reply_of(_reply(0x4C54, 7), HOST_IP) == (0x4C54, 7)
    # An echo request (type 8), or a reply to someone else, is not ours.
    assert wire.echo_reply_of(_reply(0x4C54, 7, kind=8), HOST_IP) is None
    assert (
        wire.echo_reply_of(_reply(0x4C54, 7, dst=bytes([10, 0, 2, 2])), HOST_IP) is None
    )
    assert wire.echo_reply_of(b"\0" * 20, HOST_IP) is None


def _arp_request(target):
    arp = struct.pack(
        "!HHBBH6s4s6s4s", 1, 0x0800, 6, 4, 1, GUEST_MAC, GUEST_IP, b"\0" * 6, target
    )
    return b"\xff" * 6 + GUEST_MAC + b"\x08\x06" + arp


def test_arp_reply_only_for_the_hosts_address(wire):
    reply = wire.arp_reply_to(_arp_request(HOST_IP), HOST_MAC, HOST_IP)
    assert reply is not None
    assert reply[0:6] == GUEST_MAC and reply[12:14] == b"\x08\x06"
    op, sha, spa, tha, tpa = struct.unpack("!6xH6s4s6s4s", reply[14:42])
    assert (op, sha, spa, tha, tpa) == (2, HOST_MAC, HOST_IP, GUEST_MAC, GUEST_IP)
    # slirp's gateway answers for itself; the wire must not.
    assert (
        wire.arp_reply_to(_arp_request(bytes([10, 0, 2, 2])), HOST_MAC, HOST_IP) is None
    )


def test_summary_nearest_rank(wire):
    rtts = [float(v) for v in range(1, 201)]  # 1..200 us
    s = wire.summarize(rtts, sent=200)
    assert (s["min_us"], s["median_us"], s["p99_us"]) == (1.0, 100.5, 198.0)
    assert s["received"] == 200 and s["lost"] == 0
    lossy = wire.summarize([5.0, 1.0, 3.0], sent=4)
    assert (lossy["min_us"], lossy["median_us"], lossy["p99_us"], lossy["lost"]) == (
        1.0,
        3.0,
        5.0,
        1,
    )
    assert wire.summarize([], sent=3)["received"] == 0


def test_summary_counts_the_slow_tail(wire):
    s = wire.summarize(
        [100.0] * 195 + [12000.0, 25000.0, 9999.0, 10000.0, 30000.0], sent=200
    )
    assert s["over_10ms"] == 3


SERIAL = b"""\
[net-latency] ready owner=kernel-ring ip=10.0.2.15 window_ms=10000
[net-latency] done owner=kernel-ring switches=12 cr3=6 syscalls=40
[net-latency] echoes owner=kernel-ring requests=220 replies=220
[net] seat -> netd pid 3
[net-latency] ready owner=netd ip=10.0.2.16 window_ms=10000
[net-latency] done owner=netd switches=900 cr3=880 syscalls=2000
"""


def test_serial_lines_parse(wire):
    assert wire.ready_lines(SERIAL) == [
        ("kernel-ring", "10.0.2.15", 10000),
        ("netd", "10.0.2.16", 10000),
    ]
    assert wire.done_counts(SERIAL) == {
        "kernel-ring": {
            "switches": 12,
            "cr3": 6,
            "syscalls": 40,
            "requests": 220,
            "replies": 220,
        },
        "netd": {"switches": 900, "cr3": 880, "syscalls": 2000},
    }
