"""Seven harland kernel functions brought under the LARB v4 thresholds (AGAST #3457).

LARB review/5 (projects/larb/review/5/harland.md § F2) found seven kernel
functions over the v4 thresholds (cyclomatic complexity > 30 or nesting
depth >= 6) with no justification: keycode_to_ascii (CC 36),
dhcp_handle_packet (CC 33), elf_load and vmm_reserve_page_tables (depth 7),
kalloc, vmm_free_user_pages and vfs_find_fs (depth 6).

They were split without changing behaviour:
  - keycode_to_ascii is a lookup in two [58]u8 tables (plain / shifted).
    The old letter loop returned 'a' + (position in QWERTY order), so KEY_Q
    gave 'a' and KEY_W 'b'; the tables give the key's own letter. Nothing
    calls keycode_to_ascii (the keyboard path hands raw events to
    userspace), so no input path changes.
  - dhcp_handle_packet is an option parser (dhcp_parse_options) plus one
    handler per message type (dhcp_on_offer, dhcp_on_ack).
  - elf_load maps each PT_LOAD segment with elf_load_segment / elf_load_page.
  - the vmm walks use one helper per page-table level; kalloc moves the
    split/unlink of the chosen block into heap_take_block; vfs_find_fs asks
    vfs_mount_is_prefix.

test_seven_functions_under_v4_thresholds measures them with the LARB
ritz-metrics script (no compile). The behaviour rows compile the real
keycode_to_ascii and the real net/dhcp.ritz into host programs; exit codes
name the failed claim. elf_load, the vmm walks and kalloc run on every boot
(every spawn loads an ELF and frees its page tables, mmap_isolation checks the
PML4[1+] tables), so tools/test_tier1_boot.sh is their behaviour check;
vfs_find_fs runs in test_harland_fd_tables.py.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_table_rows import _closure

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
PROJECTS = RITZ_ROOT.parent
KERNEL_SRC = PROJECTS / "harland" / "kernel" / "src"
METRICS = PROJECTS / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

# LARB v4 thresholds: a function over either needs a finding or a justification.
MAX_CC = 30
MAX_DEPTH = 5  # depth >= 6 is over

SEVEN = {
    "keycode_to_ascii": "drivers/virtio/input.ritz",
    "dhcp_handle_packet": "net/dhcp.ritz",
    "elf_load": "loader/elf.ritz",
    "vmm_reserve_page_tables": "mm/vmm.ritz",
    "vmm_free_user_pages": "mm/vmm.ritz",
    "kalloc": "mm/heap.ritz",
    "vfs_find_fs": "fs/vfs.ritz",
}


def _load_metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_3457", METRICS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # its @dataclass looks its module up
    spec.loader.exec_module(mod)
    return mod


def test_seven_functions_under_v4_thresholds():
    metrics = _load_metrics()
    over = []
    for name, rel in SEVEN.items():
        path = KERNEL_SRC / rel
        lines = path.read_text().splitlines()
        fns = [f for f in metrics.extract_functions(path, lines, "ritz") if f.name == name]
        assert len(fns) == 1, f"{rel}: expected one fn {name}, found {len(fns)}"
        f = fns[0]
        if f.complexity > MAX_CC or f.max_depth > MAX_DEPTH:
            over.append(f"{name} ({rel}:{f.line}) CC {f.complexity} depth {f.max_depth}")
    assert not over, "over the v4 thresholds (CC > 30 or depth >= 6):\n" + "\n".join(over)


# --- host programs -------------------------------------------------------------


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, main_src, tree_sources):
    """Compile each module of the tree (own object) and main_src, link, run."""
    tree = tmp_path / "tree"
    objs = []
    for rel, text in tree_sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
        objs.append(str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",))))
    (tmp_path / "t.ritz").write_text(main_src)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# --- keycode_to_ascii ----------------------------------------------------------

# Linux evdev key codes -> (plain, shifted), US QWERTY. Written out by key, not
# derived from the kernel's tables, so a mistyped table entry shows up here.
US_QWERTY = {
    1: ("\x1b", "\x1b"),  # ESC
    **{2 + i: (d, s) for i, (d, s) in enumerate(zip("1234567890", "!@#$%^&*()"))},
    12: ("-", "_"), 13: ("=", "+"), 14: ("\b", "\b"), 15: ("\t", "\t"),
    **{16 + i: (c, c.upper()) for i, c in enumerate("qwertyuiop")},
    26: ("[", "{"), 27: ("]", "}"), 28: ("\n", "\n"),
    **{30 + i: (c, c.upper()) for i, c in enumerate("asdfghjkl")},
    39: (";", ":"), 40: ("'", '"'), 41: ("`", "~"), 43: ("\\", "|"),
    **{44 + i: (c, c.upper()) for i, c in enumerate("zxcvbnm")},
    51: (",", "<"), 52: (".", ">"), 53: ("/", "?"), 57: (" ", " "),
}
KEYCODES = 127  # 0..126: every code a [N]u8 table could be indexed by, and past it


def _keycode_source():
    """The real keycode_to_ascii (and the file's consts), cut out of input.ritz.

    The rest of input.ritz is the virtio driver (PCI, virtqueues, heap), none
    of which keycode_to_ascii uses.
    """
    lines = (KERNEL_SRC / "drivers" / "virtio" / "input.ritz").read_text().splitlines()
    consts = [ln for ln in lines if ln.startswith(("pub const ", "const "))]
    start = next(i for i, ln in enumerate(lines) if ln.startswith("pub fn keycode_to_ascii("))
    end = start + 1
    while end < len(lines) and (not lines[end] or lines[end][0] in " #"):
        end += 1
    return "\n".join(consts + [""] + lines[start:end]) + "\n"


@pytest.mark.integration
def test_keycode_to_ascii_is_us_qwerty(tmp_path):
    plain = [ord(US_QWERTY.get(c, ("\0", "\0"))[0]) for c in range(KEYCODES)]
    shifted = [ord(US_QWERTY.get(c, ("\0", "\0"))[1]) for c in range(KEYCODES)]
    # Exit 1+code: wrong plain char for code; 128+code: wrong shifted char.
    main = f"""\
import keymap {{ keycode_to_ascii }}

fn main() -> i32
    let plain: [{KEYCODES}]u8 = [{", ".join(map(str, plain))}]
    let shifted: [{KEYCODES}]u8 = [{", ".join(map(str, shifted))}]
    var c: i32 = 0
    while c < {KEYCODES}
        if keycode_to_ascii(c as u16, false) != plain[c]
            return 1 + c
        if keycode_to_ascii(c as u16, true) != shifted[c]
            return 128 + c
        c = c + 1
    return 0
"""
    rc = _run(tmp_path, main, {"keymap.ritz": _keycode_source()})
    assert rc == 0, (f"key code {rc - 1}: wrong plain char" if rc < 128
                     else f"key code {rc - 128}: wrong shifted char")


# --- net/dhcp.ritz -------------------------------------------------------------

# kernel/src/serial.ritz re-exports ritzlib's StrView, as this does: a stub
# declaring its own would clash with the one ritzlib.endian's imports bring.
SERIAL_STUB = """\
pub import ritzlib.strview { StrView }
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

# Builders write no header (length 0) and the Ethernet frame is the payload, so
# the frame dhcp passes to net_send is exactly its DHCP message. ip_set_config
# and ip_set_dns record what they were given.
NET_IP_STUB = """\
pub var g_ip: [4]u8
pub var g_gw: [4]u8
pub var g_mask: [4]u8
pub var g_dns: [4]u8
pub var g_config_calls: i32 = 0
pub var g_dns_calls: i32 = 0

fn copy4(dst: *u8, src: *u8)
    var i: i64 = 0
    while i < 4
        *(dst + i) = *(src + i)
        i = i + 1

pub fn ip_build_header(buf: *u8, dst_ip: *u8, protocol: u8, payload_len: u32) -> u32
    return 0

pub fn ip_set_config(ip: *u8, gateway: *u8, netmask: *u8)
    copy4(@g_ip[0], ip)
    copy4(@g_gw[0], gateway)
    copy4(@g_mask[0], netmask)
    g_config_calls = g_config_calls + 1

pub fn ip_set_dns(dns: *u8)
    copy4(@g_dns[0], dns)
    g_dns_calls = g_dns_calls + 1
"""

NET_UDP_STUB = """\
pub fn udp_build_header(buf: *u8, src_port: u16, dst_port: u16, payload_len: u32) -> u32
    return 0
"""

NET_ETH_STUB = """\
var g_bcast: [6]u8

pub fn eth_get_broadcast_mac() -> *u8
    return @g_bcast[0]

pub fn eth_build_frame(buf: *u8, dst_mac: *u8, ethertype: u16, payload: *u8, payload_len: u32) -> u32
    var i: u32 = 0
    while i < payload_len
        *(buf + i as i64) = *(payload + i as i64)
        i = i + 1
    return payload_len
"""

# The ARP cache dhcp_release_frame reads (AGAST #4744): a hit for the server
# only when the test says so, and the address it was asked for.
NET_ARP_STUB = """\
pub var g_arp_hit: bool = false
pub var g_arp_asked: [4]u8

pub fn arp_cache_lookup(ip: *u8, mac_out: *u8) -> i32
    var i: i64 = 0
    while i < 4
        g_arp_asked[i] = *(ip + i)
        i = i + 1
    if not g_arp_hit
        return -1
    i = 0
    while i < 6
        *(mac_out + i) = 0xAA
        i = i + 1
    return 0
"""

# Drive DISCOVER -> OFFER -> REQUEST -> ACK. A reply carries the client's xid
# (read back from the DISCOVER it sent) and options: message type, mask,
# router, DNS, server id. Exit codes name the failed claim.
DHCP_MAIN = """\
import net.dhcp { dhcp_discover, dhcp_handle_packet, dhcp_get_state, dhcp_is_configured, dhcp_release_frame, Release }
import net.ip { g_ip, g_gw, g_mask, g_dns, g_config_calls, g_dns_calls }
import net.arp { g_arp_hit, g_arp_asked }

var g_frame: [576]u8

fn release_len() -> u32
    match dhcp_release_frame(@g_frame)
        Release.Frame(n) => n
        Release.NoLease => 1
        Release.NoServerMac => 2
        Release.TooSmall => 3

# DISCOVER, OFFER, ACK again: a fresh lease for the next release case.
fn lease_again() -> bool
    dhcp_discover()
    var len: u32 = build_reply(2)
    dhcp_handle_packet(@g_pkt[0], len)
    len = build_reply(5)
    dhcp_handle_packet(@g_pkt[0], len)
    dhcp_is_configured()

var g_sent: [600]u8
var g_sends: i32 = 0
var g_pkt: [300]u8

pub fn net_send(data: *u8, len: u32) -> i32
    var i: u32 = 0
    while i < len and i < 600
        g_sent[i as i32] = *(data + i as i64)
        i = i + 1
    g_sends = g_sends + 1
    return 0

pub fn net_get_mac(mac_out: *u8)
    var i: i64 = 0
    while i < 6
        *(mac_out + i) = 0x52
        i = i + 1
    return  # as net/stack.ritz's: the extern decl is void

fn put4(at: i32, a: u8, b: u8, c: u8, d: u8)
    g_pkt[at] = a
    g_pkt[at + 1] = b
    g_pkt[at + 2] = c
    g_pkt[at + 3] = d

fn opt4(at: i32, code: u8, a: u8, b: u8, c: u8, d: u8) -> i32
    g_pkt[at] = code
    g_pkt[at + 1] = 4
    put4(at + 2, a, b, c, d)
    return at + 6

# A reply of message type msg_type; xid from the DISCOVER in g_sent.
fn build_reply(msg_type: u8) -> u32
    var i: i32 = 0
    while i < 300
        g_pkt[i] = 0
        i = i + 1
    g_pkt[0] = 2
    put4(4, g_sent[4], g_sent[5], g_sent[6], g_sent[7])
    put4(16, 10, 0, 2, 15)          # yiaddr
    put4(236, 0x63, 0x82, 0x53, 0x63)
    g_pkt[240] = 53
    g_pkt[241] = 1
    g_pkt[242] = msg_type
    g_pkt[243] = 0                  # one pad byte
    var at: i32 = opt4(244, 1, 255, 255, 0, 0)
    at = opt4(at, 3, 10, 0, 2, 1)
    at = opt4(at, 6, 10, 0, 2, 3)
    at = opt4(at, 54, 10, 0, 2, 4)
    g_pkt[at] = 255
    return (at + 1) as u32

fn same4(p: *u8, a: u8, b: u8, c: u8, d: u8) -> bool
    return *p == a and *(p + 1) == b and *(p + 2) == c and *(p + 3) == d

fn main() -> i32
    # No lease yet: nothing to release
    if release_len() != 1
        return 11
    dhcp_discover()
    if g_sends != 1 or g_sent[242] != 1 or dhcp_get_state() != 1
        return 1

    # Not ours: a bad magic cookie, then a wrong xid, are ignored
    var len: u32 = build_reply(2)
    g_pkt[236] = 0
    dhcp_handle_packet(@g_pkt[0], len)
    len = build_reply(2)
    g_pkt[7] = g_pkt[7] + 1
    dhcp_handle_packet(@g_pkt[0], len)
    # Too short to hold the cookie
    len = build_reply(2)
    dhcp_handle_packet(@g_pkt[0], 239)
    if g_sends != 1 or dhcp_get_state() != 1
        return 2

    # An ACK before any REQUEST is ignored
    len = build_reply(5)
    dhcp_handle_packet(@g_pkt[0], len)
    if g_config_calls != 0 or dhcp_get_state() != 1
        return 3

    # OFFER -> REQUEST for the offered IP (option 50) to the server (option 54)
    len = build_reply(2)
    dhcp_handle_packet(@g_pkt[0], len)
    if g_sends != 2 or dhcp_get_state() != 2 or g_sent[242] != 3
        return 4
    if g_sent[243] != 50 or not same4(@g_sent[245], 10, 0, 2, 15)
        return 5
    if g_sent[249] != 54 or not same4(@g_sent[251], 10, 0, 2, 4)
        return 6

    # ACK -> the IP layer gets the offered IP, router, mask and DNS
    len = build_reply(5)
    dhcp_handle_packet(@g_pkt[0], len)
    if g_config_calls != 1 or not dhcp_is_configured()
        return 7
    if not same4(@g_ip[0], 10, 0, 2, 15) or not same4(@g_gw[0], 10, 0, 2, 1)
        return 8
    if not same4(@g_mask[0], 255, 255, 0, 0)
        return 9
    if g_dns_calls != 1 or not same4(@g_dns[0], 10, 0, 2, 3)
        return 10

    # DHCPRELEASE (AGAST #4744). The stub builders write no IPv4 or UDP
    # header and eth_build_frame copies the datagram as is, so the message
    # sits 28 bytes in. The server's MAC is not cached: no frame, no ARP
    # request (the stub has none to call), and the lease is dropped anyway.
    let sends: i32 = g_sends
    if release_len() != 2 or not same4(@g_arp_asked[0], 10, 0, 2, 4)
        return 12
    if dhcp_is_configured() or g_sends != sends
        return 13
    # Cached: one RELEASE for the leased address to the server, and no send
    # of its own (the caller sends it once).
    if not lease_again()
        return 14
    g_arp_hit = true
    let sends2: i32 = g_sends
    if release_len() != 28 + 250 or g_sends != sends2 or dhcp_is_configured()
        return 14
    let m: *u8 = @g_frame[28]
    if *m != 1 or not same4(m + 12, 10, 0, 2, 15) or *(m + 28) != 0x52
        return 15
    if not same4(m + 236, 0x63, 0x82, 0x53, 0x63) or *(m + 240) != 53 or *(m + 242) != 7
        return 15
    if *(m + 243) != 54 or not same4(m + 245, 10, 0, 2, 4) or *(m + 249) != 255
        return 15
    # Released: a second call has no lease
    if release_len() != 1
        return 11
    return 0
"""

DHCP_CLAIMS = {
    1: "DISCOVER not sent",
    2: "a reply with a bad cookie, a wrong xid or no room for the cookie was acted on",
    3: "an ACK before REQUEST configured the stack",
    4: "OFFER did not send a REQUEST",
    5: "REQUEST lacks option 50 = the offered IP",
    6: "REQUEST lacks option 54 = the server id",
    7: "ACK did not configure the stack",
    8: "ACK configured the wrong IP or router",
    9: "ACK configured the wrong netmask",
    10: "ACK set the wrong DNS",
    11: "DHCPRELEASE built with no lease bound",
    12: "DHCPRELEASE did not look the server up in the ARP cache, or built a frame without its MAC",
    13: "an unsent DHCPRELEASE left the lease bound, or sent something",
    14: "DHCPRELEASE was not built once for a cached server, or sent itself",
    15: "DHCPRELEASE: wrong op, ciaddr, chaddr, cookie, message type or server id",
}


@pytest.mark.integration
def test_dhcp_discover_offer_request_ack(tmp_path):
    tree = {
        "serial.ritz": SERIAL_STUB,
        "klog.ritz": KLOG_STUB,
        "net/types.ritz": (KERNEL_SRC / "net" / "types.ritz").read_text(),
        "net/ip.ritz": NET_IP_STUB,
        "net/udp.ritz": NET_UDP_STUB,
        "net/eth.ritz": NET_ETH_STUB,
        "net/arp.ritz": NET_ARP_STUB,
        "net/dhcp.ritz": (KERNEL_SRC / "net" / "dhcp.ritz").read_text(),
        # dhcp.ritz imports ritzlib.endian (AGAST #1858), and endian imports
        # ritzlib.span for its Span<u8> parameters (#4644); a real build
        # compiles each module to its own object, and so must this tree.
        **{f"ritzlib/{unit}.ritz": (RITZ_ROOT / "ritzlib" / f"{unit}.ritz").read_text()
           for unit in _closure(("endian",))},
    }
    rc = _run(tmp_path, DHCP_MAIN, tree)
    assert rc == 0, f"exit {rc}: {DHCP_CLAIMS.get(rc, 'crashed')}"
