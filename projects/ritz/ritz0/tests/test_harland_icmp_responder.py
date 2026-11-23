"""An inbound ICMP echo request is answered, and counted (AGAST #1851).

The EC2 acceptance for #1851 is a peer instance pinging harland: the serial
log must show the request arriving from the peer's address and the reply
leaving. The stack already replied to echo requests; this test pins the two
counters the pre-init responder window (``network_wait_for_peer_ping``)
reads, so the window can tell "no peer yet" (keep polling) from "answered"
(stop), and the serial evidence reports totals rather than claims.

It compiles the real ``net/icmp.ritz`` against stubs for its neighbours and
a ``net_send`` that counts frames:

  * an echo request increments both counters and sends exactly one frame;
  * an echo reply (which the peer also sends back to us) increments neither
    request nor reply-sent, and sends nothing.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"

SERIAL_STUB = """\
pub struct StrView
    ptr: *u8
    len: i64
"""

# The kernel logs through klog (AGAST #1885); these have its signatures and
# do nothing.
KLOG_STUB = """\
import serial { StrView }

pub fn klog(s: StrView) -> i32
    return 0

pub fn klog_cstr(s: *u8) -> i32
    return 0

pub fn klog_dec(n: i64) -> i32
    return 0

pub fn klog_udec(n: u64) -> i32
    return 0

pub fn klog_hex(n: u64) -> i32
    return 0

pub fn klog_hex_width(n: u64, width: i32) -> i32
    return 0

pub fn klog_hex_prefix(n: u64) -> i32
    return 0
"""

TYPES_STUB = """\
pub const ETHERTYPE_IPV4: u16 = 0x0800
pub const IP_PROTO_ICMP: u8 = 1
pub const ICMP_ECHO_REPLY: u8 = 0
pub const ICMP_ECHO_REQUEST: u8 = 8
pub const ICMP_HEADER_SIZE: u32 = 8
"""

IP_STUB = """\
var g_ip: [4]u8

pub fn ip_checksum(buf: *u8, len: u32) -> u16
    return 0

pub fn ip_build_header(buf: *u8, dst_ip: *u8, protocol: u8, payload_len: u32) -> u32
    return 20

pub fn ip_get_gateway() -> *u8
    return @g_ip[0]

pub fn ip_is_local(dst_ip: *u8) -> bool
    return true

pub fn ip_get_next_hop(dst_ip: *u8) -> *u8
    return dst_ip
"""

ARP_STUB = """\
pub fn arp_cache_lookup(ip: *u8, mac_out: *u8) -> i32
    var i: i32 = 0
    while i < 6
        *(mac_out + i as i64) = 2
        i = i + 1
    return 0

pub fn arp_send_request(target_ip: *u8) -> i32
    return 0
"""

ETH_STUB = """\
var g_eth_calls: u32 = 0
var g_eth_payload_len: u32 = 0
var g_eth_dst0: u8 = 0
var g_eth_icmp_type: u8 = 0

pub fn eth_call_count() -> u32
    return g_eth_calls

pub fn eth_last_payload_len() -> u32
    return g_eth_payload_len

pub fn eth_last_dst0() -> u8
    return g_eth_dst0

pub fn eth_last_icmp_type() -> u8
    return g_eth_icmp_type

pub fn eth_build_frame(buf: *u8, dst_mac: *u8, ethertype: u16, payload: *u8, payload_len: u32) -> u32
    g_eth_calls = g_eth_calls + 1
    g_eth_payload_len = payload_len
    g_eth_dst0 = *(dst_mac + 0)
    g_eth_icmp_type = *((payload + 20) as *u8)
    return payload_len + 14
"""

PROGRAM = """\
import net.icmp { icmp_handle_packet, icmp_echo_request_count, icmp_echo_reply_sent_count }
import net.eth { eth_call_count, eth_last_payload_len, eth_last_dst0, eth_last_icmp_type }

var g_sent: u32 = 0

pub fn net_send(data: *u8, len: u32) -> i32
    g_sent = g_sent + 1
    return len as i32

var g_pkt: [192]u8
var g_src: [4]u8
var g_src_mac: [6]u8

fn main() -> i32
    g_src[0] = 172
    g_src[1] = 31
    g_src[2] = 13
    g_src[3] = 39
    g_src_mac[0] = 2
    g_src_mac[1] = 0xFF
    g_src_mac[2] = 0xE4
    g_src_mac[3] = 0x15
    g_src_mac[4] = 0xDA
    g_src_mac[5] = 0xED

    # A standard Linux ping request: 56-byte payload + 8-byte ICMP header =
    # 64 bytes. The reply must fit an IP header plus that whole message.
    var i: i32 = 0
    while i < 64
        g_pkt[i] = 0
        i = i + 1
    g_pkt[0] = 8
    g_pkt[6] = 0
    g_pkt[7] = 7
    icmp_handle_packet(@g_pkt[0], 64, @g_src[0], @g_src_mac[0])

    if icmp_echo_request_count() != 1
        return 10
    if icmp_echo_reply_sent_count() != 1
        return 11
    if g_sent != 1
        return 12
    # The L2 destination is the request's source MAC, and the IP payload is
    # the 20-byte header plus the whole 64-byte ICMP message (98 on the wire).
    if eth_call_count() != 1
        return 13
    if eth_last_dst0() != 2
        return 14
    if eth_last_payload_len() != 84
        return 15
    if eth_last_icmp_type() != 0
        return 16

    # An echo reply from the peer is not a request: neither counter moves,
    # and no frame is sent for it.
    g_pkt[0] = 0
    icmp_handle_packet(@g_pkt[0], 64, @g_src[0], @g_src_mac[0])

    if icmp_echo_request_count() != 1
        return 17
    if icmp_echo_reply_sent_count() != 1
        return 18
    if g_sent != 1
        return 19
    0
"""

STUBS = {
    "serial.ritz": SERIAL_STUB,
    "klog.ritz": KLOG_STUB,
    "net/types.ritz": TYPES_STUB,
    "net/ip.ritz": IP_STUB,
    "net/arp.ritz": ARP_STUB,
    "net/eth.ritz": ETH_STUB,
}
REAL = ["net/icmp.ritz"]
MODULES = list(STUBS) + REAL

CHECKS = {
    10: "an echo request was not counted",
    11: "an echo request did not produce a counted reply",
    12: "an echo request did not send exactly one frame",
    13: "no reply frame was built",
    14: "the reply's destination MAC was not the source MAC of the request",
    15: "the reply dropped ICMP payload bytes (a 64-byte echo did not fit)",
    16: "the reply was not an ICMP echo reply",
    17: "an echo reply was counted as a request",
    18: "an echo reply was counted as a reply sent",
    19: "an echo reply sent a frame",
}


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra],
                     cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), (
        f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    )
    return ll


def _run(tmp_path):
    tree = tmp_path / "tree"
    sources = dict(STUBS)
    for rel in REAL:
        sources[rel] = (KERNEL_SRC / rel).read_text()
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    objs = [
        str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
        for rel in MODULES
    ]
    # The program supplies _start and defines the extern net_send.
    (tmp_path / "t.ritz").write_text(PROGRAM)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = fast_link.clang(
        ["clang", "-Wno-override-module", *objs, "-o", str(exe),
         "-nostdlib", "-no-pie"],
        capture_output=True, text=True,
    )
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def test_echo_requests_are_answered_and_counted(tmp_path):
    rc = _run(tmp_path)
    assert rc == 0, f"check {rc}: {CHECKS.get(rc, 'crashed or unknown exit code')}"


def test_reply_buffers_hold_a_standard_ping():
    """A Linux ping's ICMP message is 64 bytes; the reply's stack buffers must
    hold 128 bytes (our cap) plus the 20-byte IP header and the 14-byte
    Ethernet header. The original 64-byte ip_buf overflowed on a normal ping
    and corrupted the frame (AGAST #1851)."""
    import re

    body = (KERNEL_SRC / "net" / "icmp.ritz").read_text()
    body = body[body.index("fn icmp_send_reply"):]
    ip_buf = int(re.search(r"var ip_buf: \[(\d+)\]u8", body).group(1))
    icmp_buf = int(re.search(r"var icmp_buf: \[(\d+)\]u8", body).group(1))
    frame = int(re.search(r"var frame: \[(\d+)\]u8", body).group(1))
    assert icmp_buf >= 128, "the echo reply cap is 128 bytes"
    assert ip_buf >= 20 + 128, "ip_buf must hold the IP header plus the cap"
    assert frame >= 14 + 20 + 128, "frame must hold all three headers"
    assert "if icmp_len > 128" in body
