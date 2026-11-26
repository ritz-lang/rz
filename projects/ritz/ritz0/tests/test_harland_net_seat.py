"""The frame-seat handoff to /bin/netd (AGAST #4744, ring plan T38,
harland docs/RING2_NET.md "Frame seat").

On the translating boot, after the in-kernel self-test window, the kernel
spawns /bin/netd at CPL 3 with the frame and address handles in its
ServiceBoot record. netd's ready NetPublish commits the snapshot and then
waits in the kernel while pid 1, still the seat, tries one DHCPRELEASE (no
ARP wait, no second TX try), stops the stack (net_poll, ip_set_config,
ip_set_dns), and registers netd as the frame object's only consumer and
producer. netd returns from NetPublish, adopts the kernel's ring indexes
and starts DHCP from idle. The kernel does not copy its lease.

The behaviour is tools/test_msix_boot.sh's vtd run (its verdicts are
host-tested in projects/ritz/tools/test_ci_msix_boot.py); the ring index
adoption is host-tested in driver_abi/test/test_spsc.ritz and
system/test/test_netsvc.ritz. These checks pin the order and the guards
that run can't observe.
"""

import re
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
HARLAND = RITZ0_DIR.parent.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
MAIN = KERNEL_SRC / "main.ritz"
RING1 = KERNEL_SRC / "net" / "ring1.ritz"
RING = KERNEL_SRC / "net" / "ring.ritz"
STACK = KERNEL_SRC / "net" / "stack.ritz"
DHCP = KERNEL_SRC / "net" / "dhcp.ritz"
NET_RT = KERNEL_SRC / "syscall" / "runtime" / "net.ritz"
NETD = HARLAND / "system" / "src" / "netd.ritz"


def _code(path):
    return "\n".join(l.split("#", 1)[0].rstrip() for l in path.read_text().splitlines())


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


def _in_order(body, *needles):
    at = -1
    for n in needles:
        i = body.find(n, at + 1)
        assert i > at, f"{n!r} missing or out of order"
        at = i


@pytest.mark.unit
def test_the_handoff_runs_after_the_self_test_window_and_before_init():
    tail = _fn_body(_code(MAIN), "kernel_tail")
    _in_order(tail, "net_ring1_spawn()", "postinit_diagnostics(", "net_seat_handoff()", "run_init()")


@pytest.mark.unit
def test_only_a_ring1_boot_with_a_published_link_spawns_netd():
    """D7: an untranslated boot keeps virtio_net_init and spawns no netd."""
    body = _fn_body(_code(RING1), "net_seat_handoff")
    guard = body.index("ring1_pid == 0")
    assert guard < body.index('process_spawn_program("/bin/netd")')
    assert "ring_driver_published()" in body[: body.index('process_spawn_program("/bin/netd")')]


@pytest.mark.unit
def test_netd_is_set_up_before_it_runs():
    """Its address page is its first shared mapping (DRV_RING_BASE) and the
    ServiceBoot record is written before pid 1 first yields to it."""
    body = _fn_body(_code(RING1), "netd_grant_to")
    _in_order(body, "cap_kernel_grant(", "shm_map(", "DRV_RING_BASE", "service_boot_at(")
    handoff = _fn_body(_code(RING1), "net_seat_handoff")
    _in_order(handoff, 'process_spawn_program("/bin/netd")', "netd_grant_to(", "net_handoff_arm(", "sched_yield()")


@pytest.mark.unit
def test_release_then_stack_stop_then_seat_switch_then_netd_resumes():
    body = _fn_body(_code(RING1), "net_seat_handoff")
    _in_order(body, "net_handoff_ready()", "seat_release()", "net_stack_release()",
              "ring_seat_handoff(", "seat_rx_read", "net_handoff_done()")
    # The switch runs whether or not the release was sent: nothing returns
    # between the release and the switch.
    between = body[body.index("seat_release()"):body.index("ring_seat_handoff(")]
    assert "return" not in between
    release = _fn_body(_code(RING1), "seat_release")
    _in_order(release, "dhcp_release_frame(", "ring_send_once(")
    assert "ring_send(" not in release


@pytest.mark.unit
def test_the_release_waits_for_neither_arp_nor_a_second_tx_slot():
    rel = _fn_body(_code(DHCP), "dhcp_release_frame")
    assert "arp_cache_lookup(" in rel
    assert "arp_send_request(" not in rel and "while" not in rel.split("arp_cache_lookup(")[1]
    once = _fn_body(_code(RING), "ring_send_once")
    assert "sched_yield" not in once and "while" not in once
    assert "Publish.Full => " in once


@pytest.mark.unit
def test_the_kernel_stops_its_stack_and_copies_no_lease():
    body = _fn_body(_code(STACK), "net_stack_release")
    for step in ("net_initialized = false", "net_via_ring = false", "ip_init()", "dhcp_reset()"):
        assert step in body, step
    handoff = _fn_body(_code(RING1), "net_seat_handoff")
    for copy in ("ip_get_our_addr", "addr_publish", "NetAddr"):
        assert copy not in handoff, copy


@pytest.mark.unit
def test_the_seat_switch_makes_netd_the_only_consumer():
    body = _fn_body(_code(RING), "ring_seat_handoff")
    _in_order(body, "seat_close()", "net_frame_register(")
    assert "service_pid" in body.split("net_frame_register(")[1].split(")")[0]


@pytest.mark.unit
def test_netpublish_holds_only_the_armed_service_until_the_switch():
    handler = _fn_body(_code(NET_RT), "sys_net_publish_handler")
    _in_order(handler, "net_publish_for(", "handoff_service", "sched_yield()")
    publish = _fn_body(_code(NET_RT), "net_publish_for")
    assert "handoff_ready = true" in publish


@pytest.mark.unit
def test_netd_adopts_the_seat_after_its_ready_publish():
    body = _fn_body(_code(NETD), "bring_up")
    _in_order(body, "g_svc.ready(", "net_publish(", "service_boot_at(DRV_RING_BASE)",
              "g_svc.take_seat(seat.seat_rx_read, seat.seat_tx_write)", "g_svc.set_link(")
