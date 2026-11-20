"""Harland's pre-init network self-tests are a boot option (AGAST #4335).

Before: `postinit_diagnostics` ran `network_dhcp_ping` (DHCP, a gateway ping
and a 300-frame TX burst) before `/bin/init` was loaded. Under QEMU's
virtio-net that finishes in seconds; on EC2 Nitro the ENA path panicked the
kernel there, so `init_interactive` and `rzsh` never started and the serial
console filled its latest-64-KiB window with ICMP replies.

After: the UEFI loader turns the tests on only when the boot volume holds the
zero-byte marker `\\harland\\net-selftest`, and BootInfo version 3 carries the
flag. Without it the kernel leaves the NIC alone until init is up, so a
misbehaving driver cannot keep the shell from starting. QEMU's NIC gate
(`tools/test_msix_boot.sh`) writes the marker, so the NIC coverage stays
where it lives; every other boot script does not, and `test_nvme_boot.sh`
asserts the runtime skip line.

These are source-level contract checks: the runtime proof is the QEMU boots
in the gate. The loader and kernel each define their own packed BootInfo
structure, so their field lists are compared here rather than trusted to
stay in step by hand.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
HARLAND = RITZ0_DIR.parents[1] / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
PMM = KERNEL_SRC / "mm" / "pmm.ritz"
MAIN = KERNEL_SRC / "main.ritz"
BOOT_MAIN = HARLAND / "boot" / "src" / "main.ritz"
TOOLS = HARLAND / "tools"

# Boot scripts that boot the kernel. Only the NIC gate asks for the network
# self-tests; the rest must boot with the NIC untouched.
BOOT_SCRIPTS = [
    "test_tier1_boot.sh",
    "test_nvme_boot.sh",
    "test_esp_initramfs_boot.sh",
    "test_shell_boot.sh",
    "test_irq_dest_boot.sh",
    "test_msix_boot.sh",
]


def _code(path):
    """Source with `#` comments stripped (no `#` occurs inside a string here)."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _const(code, name):
    m = re.search(rf"^(?:pub\s+)?const {re.escape(name)}: u32 = (\w+)$", code, re.M)
    assert m, f"no const {name}"
    return int(m.group(1), 0)


def _fn_body(code, fn):
    m = re.search(rf"^(?:pub\s+)?fn {fn}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"no fn {fn}"
    return m.group(0)


def _struct_fields(code, header):
    """The field names of a packed struct, in order (comment lines inside it
    were stripped to blanks by _code, so scan to the next top-level line)."""
    m = re.search(rf"^{re.escape(header)}\n(.*?)(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"no struct {header}"
    return [re.match(r"    (\w+)\s*:", line).group(1)
            for line in m.group(1).splitlines() if re.match(r"    (\w+)\s*:", line)]


def _imports_from(code, module):
    m = re.search(rf"^import {re.escape(module)}\s*\{{([^}}]*)\}}", code, re.M)
    return set(re.findall(r"\w+", m.group(1))) if m else None


def test_boot_info_v3_appends_the_network_self_test_flag():
    code = _code(PMM)
    assert _const(code, "HARLAND_BOOT_VERSION_FLAGS") == 3
    assert _const(code, "HARLAND_BOOT_FLAG_NET_SELFTEST") == 1
    # AGAST #1851: a second boot option, so the EC2 acceptance image can ask
    # the kernel to keep polling until a peer instance's ping is answered
    # without making every other net-selftest boot wait for a peer.
    assert _const(code, "HARLAND_BOOT_FLAG_NET_RESPONDER") == 2
    fields = _struct_fields(code, "pub struct HarlandBootInfo")
    # Appended after version 2's initramfs fields: an older loader's offset
    # for every field it knows must not move.
    assert fields[-2:] == ["flags", "_pad3"]
    assert fields.index("initramfs_size") < fields.index("flags")


def test_loader_and_kernel_boot_info_layouts_are_identical():
    """The two structures are separate declarations of one ABI."""
    kernel = _struct_fields(_code(PMM), "pub struct HarlandBootInfo")
    loader = _struct_fields(_code(BOOT_MAIN), "struct BootInfo")
    assert loader == kernel


def test_loader_and_kernel_agree_on_the_boot_option():
    loader = _code(BOOT_MAIN)
    kernel = _code(PMM)
    assert _const(loader, "BOOT_VERSION") == 3
    assert _const(loader, "BOOT_FLAG_NET_SELFTEST") == _const(
        kernel, "HARLAND_BOOT_FLAG_NET_SELFTEST")
    assert _const(loader, "BOOT_FLAG_NET_RESPONDER") == _const(
        kernel, "HARLAND_BOOT_FLAG_NET_RESPONDER")


def test_loader_reads_the_marker_from_the_boot_volume():
    code = _code(BOOT_MAIN)
    probe = _fn_body(code, "load_boot_options_from_fs")
    assert 'ascii_to_ucs2("\\\\harland\\\\net-selftest"' in probe
    assert "boot_flags = boot_flags | BOOT_FLAG_NET_SELFTEST" in probe


def test_loader_reads_the_net_responder_marker():
    """AGAST #1851: the EC2 acceptance image adds \\harland\\net-responder;
    the kernel then waits a bounded window for an inbound ICMP echo request."""
    code = _code(BOOT_MAIN)
    probe = _fn_body(code, "load_boot_options_from_fs")
    assert 'ascii_to_ucs2("\\\\harland\\\\net-responder"' in probe
    assert "boot_flags = boot_flags | BOOT_FLAG_NET_RESPONDER" in probe
    # Called while the root volume is open, as the initramfs probe is...
    assert "load_boot_options_from_fs(root_file)" in _fn_body(code, "load_kernel_from_fs")
    # ...and handed to the kernel in BootInfo.
    assert "boot_info.flags = boot_flags" in _fn_body(code, "build_boot_info")


def test_kernel_hands_the_responder_option_to_postinit():
    body = _fn_body(_code(MAIN), "kernel_main")
    assert "var run_net_responder: bool = false" in body
    assert re.search(
        r"run_net_responder = "
        r"\(\(\*harland_boot_info\)\.flags & HARLAND_BOOT_FLAG_NET_RESPONDER\) != 0",
        body), body
    assert "postinit_diagnostics(run_net_selftests, run_net_responder)" in body


def test_postinit_waits_for_a_peer_ping_only_when_asked():
    """The responder window must be bounded, must poll the NIC (so ARP and
    ICMP are answered), and must log the counters that are the acceptance
    evidence in the serial log."""
    code = _code(KERNEL_SRC / "postinit.ritz")
    diagnostics = _fn_body(code, "postinit_diagnostics")
    assert "network_dhcp_ping(run_net_responder)" in diagnostics
    net = _fn_body(code, "network_dhcp_ping")
    assert "network_wait_for_peer_ping()" in net
    wait = _fn_body(code, "network_wait_for_peer_ping")
    assert "net_poll()" in wait
    assert "deadline_after_us" in wait and "deadline_passed" in wait
    assert "icmp_echo_request_count()" in wait
    assert "icmp_echo_reply_sent_count()" in wait
    assert "[net] peer ping" in wait


def test_kernel_reads_flags_only_from_a_v3_boot_info():
    """An older loader leaves the flag 0 rather than undefined bytes."""
    code = _code(MAIN)
    body = _fn_body(code, "kernel_main")
    assert "var run_net_selftests: bool = false" in body
    assert re.search(
        r"if \(\*harland_boot_info\)\.version >= HARLAND_BOOT_VERSION_FLAGS\n"
        r"\s+run_net_selftests = "
        r"\(\(\*harland_boot_info\)\.flags & HARLAND_BOOT_FLAG_NET_SELFTEST\) != 0",
        body), body
    assert "postinit_diagnostics(run_net_selftests, run_net_responder)" in body


def test_main_imports_the_flag_constants():
    names = _imports_from(_code(MAIN), "mm.pmm")
    assert {"HARLAND_BOOT_VERSION_FLAGS", "HARLAND_BOOT_FLAG_NET_SELFTEST",
            "HARLAND_BOOT_FLAG_NET_RESPONDER"} <= names


def test_only_the_qemu_nic_gate_asks_for_the_network_self_tests():
    """Only the NIC gate writes the marker into its ESP; the other boots may
    mention it (to assert its absence) but must not create it."""
    for name in BOOT_SCRIPTS:
        assert (TOOLS / name).is_file(), f"missing boot script {name}"
        text = (TOOLS / name).read_text()
        if name == "test_msix_boot.sh":
            assert "esp/harland/net-selftest" in text, \
                "the NIC gate must create the boot option"
        else:
            assert "esp/harland/net-selftest" not in text, \
                f"{name} must not ask for the NIC tests"


def test_a_boot_without_the_option_asserts_the_skip_and_no_nic_init():
    """The runtime half of the gate: an ESP without the marker must log the
    skip and must not initialize the network stack (which would probe ENA)."""
    nvme = (TOOLS / "test_nvme_boot.sh").read_text()
    assert "[net] Network self-tests skipped" in nvme
    assert "network without the boot option" in nvme
