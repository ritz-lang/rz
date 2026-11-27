"""The frame-seat handoff to /bin/netd (AGAST #4744, #4875, ring plan T38,
harland docs/RING2_NET.md "Frame seat", "Drivers inside netd (D9)").

On the translating boot netd is already running (D9: spawned at step 2 as
the NIC's driver, the seat's producer and consumer). After the in-kernel
self-test window the kernel spawns nothing: it grants netd an address page
with its ServiceBoot record and enqueues it as ATTACH. netd's ready
NetPublish commits the snapshot and then waits in the kernel while pid 1,
still the seat, tries one DHCPRELEASE (no ARP wait, no second TX try),
stops the stack (net_poll, ip_set_config, ip_set_dns), and closes the seat.
netd returns from NetPublish, drains what the kernel left on both rings
through its own stack, revokes the frame object and starts DHCP from idle.
The kernel does not copy its lease.

The behaviour is tools/test_msix_boot.sh's vtd run (its verdicts are
host-tested in projects/ritz/tools/test_ci_msix_boot.py); the drain is
host-tested in driver_abi/test/test_spsc.ritz and system/test/test_seat.ritz.
These checks pin the order and the guards that run can't observe.
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
def test_only_a_ring1_boot_with_a_published_link_hands_the_seat_over():
    """D7: an untranslated boot keeps virtio_net_init and has no netd; the
    handoff is a no-op unless step 2's netd published its link."""
    body = _fn_body(_code(RING1), "net_seat_handoff")
    guard = body.index("ring1_pid == 0")
    assert guard < body.index("netd_service_page(pid)")
    assert "ring_driver_published()" in body[: body.index("netd_service_page(pid)")]
    assert "process_spawn_program" not in body


@pytest.mark.unit
def test_the_address_page_is_set_up_before_pid_1_yields():
    """The page is granted, its ServiceBoot written and its ATTACH enqueued
    before pid 1 first yields to netd for the ready publish; the same setup
    serves a replacement (#4745)."""
    body = _fn_body(_code(RING1), "netd_service_page")
    _in_order(body, "net_service_page(", "net_service_boot(", "net_addr_register(", "net_service_attach_page(")
    assert "cap_kernel_grant(" in _fn_body(_code(NET_RT), "net_service_page")
    assert "service_boot_at(" in _fn_body(_code(NET_RT), "net_service_boot")
    handoff = _fn_body(_code(RING1), "net_seat_handoff")
    _in_order(handoff, "netd_service_page(pid)", "net_handoff_arm(", "sched_yield()")


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
def test_the_seat_switch_leaves_netd_the_only_holder():
    """D9: pid 1 drops its handle and nobody is registered as the frame
    object's consumer; netd, the seat's driver, drains and revokes it."""
    body = _fn_body(_code(RING), "ring_seat_handoff")
    _in_order(body, "seat_driver != service_pid", "seat_close()", "net_frame_register(0, 0)")


@pytest.mark.unit
def test_netpublish_holds_only_the_armed_service_until_the_switch():
    handler = _fn_body(_code(NET_RT), "sys_net_publish_handler")
    _in_order(handler, "net_publish_for(", "handoff_service", "sched_yield()")
    publish = _fn_body(_code(NET_RT), "net_publish_for")
    assert "handoff_ready = true" in publish


@pytest.mark.unit
def test_netd_drains_the_seat_after_its_ready_publish():
    body = _fn_body(_code(NETD), "take_over")
    _in_order(body, "g_svc.ready(", "net_publish(g_addr)", "service_boot_at(g_addr_va)",
              "seat_hand_over<VirtioNic>(@&g_seat, @&g_svc, at.seat_rx_read", "cap_revoke(g_seat.handle)",
              "g_svc.set_link(")
