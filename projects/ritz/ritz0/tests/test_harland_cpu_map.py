"""Harland indexes per-CPU state by CPU index, not by APIC ID (AGAST #1883, M7).

apic.ritz kept `ap_started: [16]u8` and wrote `ap_started[my_apic_id]` from
each AP (and the BSP polled `ap_started[apic_id]`), so an APIC ID of 16 or
more, normal on larger EC2 instances and on AMD, wrote past the array.
The 16-CPU limit was spelled three ways (sched's MAX_CPUS, ACPI's
`cpu_apic_ids: [16]u8`, apic.ritz's literals).

Now arch/x86_64/cpu_map.ritz owns the CPU table: MAX_CPUS, num_cpus,
cpu_apic_ids (u32: room for x2APIC IDs), the APIC ID -> CPU index lookup and
the per-CPU "started" flags. The MADT parser records CPUs with cpu_map_add, an
AP flags itself with cpu_map_mark_started(lapic_id()) and the BSP polls
cpu_map_started(cpu index). (The scheduler that also looked its CpuSched up
here was deleted unused by #1882.)

The behaviour test compiles the real cpu_map.ritz (it has no imports and no
hardware access) into a host program with sparse APIC IDs up to 255; its exit
code names the failed claim. The source-level tests pin that apic.ritz and the
ACPI tables go through cpu_map. The runtime check is the
boot with -smp 4 (tools/test_boot.sh, tools/test_tier1_boot.sh).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
CPU_MAP = KERNEL_SRC / "arch" / "x86_64" / "cpu_map.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
TABLES = KERNEL_SRC / "drivers" / "acpi" / "tables.ritz"

# The kernel is built by ritz0 only, so one compiler row (TESTING.md, "What a
# ritz0 pytest case costs").

PROGRAM = """\
import arch.x86_64.cpu_map

# A MADT Processor Local APIC entry (type 0, 8 bytes) at buf[off].
fn put_lapic(buf: *u8, off: i64, apic_id: u8, flags: u8) -> i32
    *(buf + off) = 0
    *(buf + off + 1) = 8
    *(buf + off + 2) = 0
    *(buf + off + 3) = apic_id
    *(buf + off + 4) = flags
    *(buf + off + 5) = 0
    *(buf + off + 6) = 0
    *(buf + off + 7) = 0
    0

# A MADT Processor Local x2APIC entry (type 9, 16 bytes) at buf[off].
fn put_x2apic(buf: *u8, off: i64, x2apic_id: u32, flags: u8) -> i32
    *(buf + off) = 9
    *(buf + off + 1) = 16
    *(buf + off + 2) = 0
    *(buf + off + 3) = 0
    *(buf + off + 4) = (x2apic_id & 0xFF) as u8
    *(buf + off + 5) = ((x2apic_id >> 8) & 0xFF) as u8
    *(buf + off + 6) = ((x2apic_id >> 16) & 0xFF) as u8
    *(buf + off + 7) = ((x2apic_id >> 24) & 0xFF) as u8
    var i: i64 = 8
    while i < 16
        *(buf + off + i) = 0
        i = i + 1
    *(buf + off + 8) = flags
    0

fn main() -> i32
    if MAX_CPUS != 64
        return 1
    cpu_map_reset()
    if num_cpus != 0 or cpu_index_of_apic_id(0) != -1
        return 2
    # Sparse APIC IDs, as firmware lists them: 16 and 255 are past a [16] array.
    if cpu_map_add(0) != 0 or cpu_map_add(2) != 1 or cpu_map_add(16) != 2 or cpu_map_add(255) != 3
        return 3
    if cpu_index_of_apic_id(16) != 2 or cpu_index_of_apic_id(255) != 3 or cpu_index_of_apic_id(2) != 1
        return 4
    if cpu_index_of_apic_id(1) != -1 or cpu_index_of_apic_id(3) != -1
        return 5
    # The AP with APIC ID 16 flags CPU index 2, and only it.
    if cpu_map_mark_started(16) != 2
        return 6
    if cpu_map_started(2) != 1 or cpu_map_started(0) != 0 or cpu_map_started(1) != 0 or cpu_map_started(3) != 0
        return 7
    if cpu_map_mark_started(255) != 3 or cpu_map_started(3) != 1
        return 8
    # An APIC ID that isn't in the table flags nothing.
    if cpu_map_mark_started(7) != -1 or cpu_map_started(0) != 0 or cpu_map_started(1) != 0
        return 9
    if cpu_map_started(-1) != 0 or cpu_map_started(64) != 0
        return 10
    # Fill to MAX_CPUS (well past the old 16); the next CPU is refused and changes nothing.
    var id: u32 = 100
    while num_cpus < 64
        if cpu_map_add(id) != num_cpus as i32 - 1
            return 11
        id = id + 1
    if cpu_map_add(300) != -1 or num_cpus != 64 or cpu_index_of_apic_id(300) != -1
        return 12
    if cpu_index_of_apic_id(111) != 15 or cpu_apic_ids[15] != 111 or cpu_index_of_apic_id(159) != 63
        return 13
    # CPU indexes past 16 flag and read their own started flag.
    if cpu_map_mark_started(140) != 44 or cpu_map_started(44) != 1 or cpu_map_started(43) != 0
        return 15
    # reset forgets CPUs and their started flags
    cpu_map_reset()
    if num_cpus != 0 or cpu_index_of_apic_id(16) != -1 or cpu_map_started(2) != 0 or cpu_map_started(44) != 0
        return 14
    # x2APIC IDs (32 bits, past the 8-bit xAPIC destination) are kept whole.
    if cpu_map_add(0) != 0 or cpu_map_add(0x12345) != 1 or cpu_apic_ids[1] != 0x12345
        return 16
    if cpu_map_needs_x2apic() != 1
        return 17
    cpu_map_reset()
    if cpu_map_add(0) != 0 or cpu_map_add(255) != 1 or cpu_map_needs_x2apic() != 0
        return 18
    # MADT entries: type 0 and type 9 CPUs are recorded, disabled ones and
    # other entry types are not; a CPU listed twice keeps one index.
    cpu_map_reset()
    var buf: [64]u8
    let b: *u8 = @buf[0]
    put_lapic(b, 0, 3, 1)
    if cpu_map_add_madt_entry(b) != 0 or cpu_apic_ids[0] != 3
        return 19
    put_x2apic(b, 0, 0x100, 1)
    if cpu_map_add_madt_entry(b) != 1 or cpu_apic_ids[1] != 0x100
        return 20
    put_x2apic(b, 0, 0xABCDEF01, 2)   # online-capable counts
    if cpu_map_add_madt_entry(b) != 2 or cpu_apic_ids[2] != 0xABCDEF01
        return 21
    put_x2apic(b, 0, 0x200, 0)        # disabled
    put_lapic(b, 16, 9, 0)            # disabled
    if cpu_map_add_madt_entry(b) != -1 or cpu_map_add_madt_entry(b + 16) != -1 or num_cpus != 3
        return 22
    put_x2apic(b, 0, 3, 1)            # APIC ID 3 again, as an x2APIC entry
    if cpu_map_add_madt_entry(b) != 0 or num_cpus != 3
        return 23
    *b = 1                            # an I/O APIC entry is not a CPU
    if cpu_map_add_madt_entry(b) != -1 or num_cpus != 3
        return 24
    put_lapic(b, 0, 4, 1)
    *(b + 1) = 4                      # a type 0 entry shorter than 8 bytes
    put_x2apic(b, 16, 5, 1)
    *(b + 17) = 12                    # a type 9 entry shorter than 16 bytes
    if cpu_map_add_madt_entry(b) != -1 or cpu_map_add_madt_entry(b + 16) != -1 or num_cpus != 3
        return 25
    0
"""

CLAIMS = {1: "MAX_CPUS is 64", 2: "reset empties the table", 3: "add returns CPU indexes in order",
          4: "APIC ID -> CPU index", 5: "absent APIC ID -> -1", 6: "mark_started returns the index",
          7: "only the AP's own index is flagged", 8: "APIC ID 255 flags index 3",
          9: "unknown APIC ID flags nothing", 10: "out-of-range index reads 0",
          11: "add up to MAX_CPUS", 12: "65th CPU refused", 13: "16th and 64th CPUs recorded",
          14: "reset clears started flags", 15: "CPU index 44 flags itself",
          16: "32-bit x2APIC ID kept whole", 17: "an ID > 255 needs x2APIC", 18: "IDs <= 255 don't",
          19: "MADT type 0 CPU recorded", 20: "MADT type 9 CPU recorded", 21: "online-capable type 9 recorded",
          22: "disabled CPUs skipped", 23: "a CPU in both type 0 and 9 keeps one index",
          24: "non-CPU entry ignored", 25: "short entries ignored"}


@pytest.mark.integration
def test_cpu_map_indexes_by_cpu_not_apic_id(tmp_path):
    tree = tmp_path / "tree" / "arch" / "x86_64"
    tree.mkdir(parents=True)
    (tree / "cpu_map.ritz").write_text(CPU_MAP.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "cpu_map.ritz", "cpu_map", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {CLAIMS.get(rc, 'crash')}"


# --- source level: everyone goes through cpu_map ----------------------------------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def test_apic_flags_and_polls_by_cpu_index():
    code = _code(APIC)
    assert not re.search(r"^var ap_started\b", code, re.M), "apic.ritz still keeps its own ap_started"
    assert not re.search(r"\[\s*\w*apic_id\w*\s+as\s+i32\s*\]", code), "an array is indexed by an APIC ID"
    assert "cpu_map_mark_started(my_apic_id)" in _body(code, "ap_entry")
    boot_one = _body(code, "ap_boot_one")
    assert re.search(r"cpu_map_started\(cpu_idx\)", boot_one), boot_one
    boot_all = _body(code, "ap_boot_all")
    assert re.search(r"ap_boot_one\(apic_id, i,", boot_all), boot_all
    assert not re.search(r"while i < 16\b", code), "literal CPU limit in apic.ritz"


def test_one_cpu_limit_and_table():
    for path in (APIC, TABLES, KERNEL_SRC / "main.ritz"):
        code = _code(path)
        rel = path.relative_to(KERNEL_SRC)
        assert not re.search(r"^(?:pub\s+)?const MAX_CPUS\b", code, re.M), f"{rel} defines MAX_CPUS"
        assert not re.search(r"^(?:pub\s+)?var (?:num_cpus|cpu_apic_ids)\b", code, re.M), f"{rel} keeps a CPU table"
    parse = _body(_code(TABLES), "acpi_parse_madt")
    assert "cpu_map_add_madt_entry(entry_addr as *u8)" in parse, "MADT CPUs not recorded via cpu_map_add_madt_entry"
    # Type 9 (x2APIC) entries reach cpu_map too, not only type 0 (#4184).
    assert re.search(r"MADT_LOCAL_APIC or \(\*entry\)\.entry_type == MADT_X2APIC", parse), parse
    assert not re.search(r"num_cpus < 16", parse)


def _max_cpus():
    m = re.search(r"^pub const MAX_CPUS: i32 = (\d+)$", _code(CPU_MAP), re.M)
    assert m, "MAX_CPUS not found in cpu_map.ritz"
    return int(m.group(1))


def test_per_cpu_arrays_are_max_cpus_long():
    """Array lengths must be literals, so each per-CPU array spells MAX_CPUS out.

    A [16] array with MAX_CPUS = 64 is a BSS overflow once CPU 16 boots (#4184).
    (sched/mod.ritz's cpu_sched was one; #1882 deleted the unused scheduler.)"""
    n = _max_cpus()
    assert n > 16, "MAX_CPUS still 16: CPUs past 16 are dropped"
    for path, names in ((CPU_MAP, ("cpu_apic_ids", "cpu_started")), (APIC, ("ap_stack_tops",))):
        code = _code(path)
        for name in names:
            m = re.search(rf"^(?:pub\s+)?var {name}: \[(\d+)\]", code, re.M)
            assert m, f"{path.name}: {name} not found"
            assert int(m.group(1)) == n, f"{path.name}: {name} is [{m.group(1)}], MAX_CPUS is {n}"


def test_apic_x2apic_mode():
    """x2APIC mode when CPUID.1:ECX[21]: IA32_APIC_BASE bit 10, ICR through MSR 0x830
    with a 32-bit destination, and no 8-bit cast of an APIC ID (#4184)."""
    code = _code(APIC)
    assert not re.search(r"cpu_apic_ids\[\w+\] as u8", code), "APIC ID cut to 8 bits"
    assert not re.search(r"^var ap_stacks: \[", code, re.M), "AP stacks still a static array"
    assert "pmm_alloc_page()" in _body(code, "get_ap_stack_top"), "AP stacks not from the PMM"
    assert "get_ap_stack_top(i)" in _body(code, "ap_boot_all"), "ap_boot_all does not use the PMM stacks"
    assert re.search(r"cpuid\(1\)", code) and re.search(r"1 << 21", code), "no CPUID.1:ECX[21] check"
    assert re.search(r"0x1B\b", code) and re.search(r"1 << 10", code), "x2APIC not enabled via IA32_APIC_BASE"
    assert re.search(r"0x830\b", code), "ICR not written through MSR 0x830"
    assert re.search(r"fn lapic_send_ipi\(dest_apic: u32,", code), "IPI destination still 8 bits"
    # Every AP switches its own LAPIC to x2APIC before it reads its ID.
    entry = _body(code, "ap_entry")
    assert entry.index("x2apic_enable_local()") < entry.index("lapic_id()"), entry
