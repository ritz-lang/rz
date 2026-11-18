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
cpu_map_started(cpu index); the scheduler finds its CpuSched through the same
lookup.

The behaviour test compiles the real cpu_map.ritz (it has no imports and no
hardware access) into a host program with sparse APIC IDs up to 255; its exit
code names the failed claim. The source-level tests pin that apic.ritz, the
ACPI tables and the scheduler go through cpu_map. The runtime check is the
boot with -smp 4 (tools/test_boot.sh, tools/test_tier1_boot.sh).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
CPU_MAP = KERNEL_SRC / "arch" / "x86_64" / "cpu_map.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
TABLES = KERNEL_SRC / "drivers" / "acpi" / "tables.ritz"
SCHED = KERNEL_SRC / "sched" / "mod.ritz"

# The kernel is built by ritz0 only, so one compiler row (TESTING.md, "What a
# ritz0 pytest case costs").

PROGRAM = """\
import arch.x86_64.cpu_map

fn main() -> i32
    if MAX_CPUS != 16
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
    if cpu_map_started(-1) != 0 or cpu_map_started(16) != 0
        return 10
    # Fill to MAX_CPUS; the next CPU is refused and changes nothing.
    var id: u32 = 100
    while num_cpus < 16
        if cpu_map_add(id) != num_cpus as i32 - 1
            return 11
        id = id + 1
    if cpu_map_add(300) != -1 or num_cpus != 16 or cpu_index_of_apic_id(300) != -1
        return 12
    if cpu_index_of_apic_id(111) != 15 or cpu_apic_ids[15] != 111
        return 13
    # reset forgets CPUs and their started flags
    cpu_map_reset()
    if num_cpus != 0 or cpu_index_of_apic_id(16) != -1 or cpu_map_started(2) != 0
        return 14
    0
"""

CLAIMS = {1: "MAX_CPUS is 16", 2: "reset empties the table", 3: "add returns CPU indexes in order",
          4: "APIC ID -> CPU index", 5: "absent APIC ID -> -1", 6: "mark_started returns the index",
          7: "only the AP's own index is flagged", 8: "APIC ID 255 flags index 3",
          9: "unknown APIC ID flags nothing", 10: "out-of-range index reads 0",
          11: "add up to MAX_CPUS", 12: "17th CPU refused", 13: "16th CPU recorded",
          14: "reset clears started flags"}


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
    for path in (APIC, TABLES, SCHED, KERNEL_SRC / "main.ritz"):
        code = _code(path)
        rel = path.relative_to(KERNEL_SRC)
        assert not re.search(r"^(?:pub\s+)?const MAX_CPUS\b", code, re.M), f"{rel} defines MAX_CPUS"
        assert not re.search(r"^(?:pub\s+)?var (?:num_cpus|cpu_apic_ids)\b", code, re.M), f"{rel} keeps a CPU table"
    parse = _code(TABLES)
    assert re.search(r"cpu_map_add\(\(\*lapic\)\.apic_id as u32\)", parse), "MADT CPUs not recorded via cpu_map_add"
    assert not re.search(r"num_cpus < 16", parse)


def test_scheduler_finds_its_cpu_through_the_map():
    body = _body(_code(SCHED), "get_cpu_sched")
    assert "cpu_index_of_apic_id(lapic_id())" in body, body
    assert "cpu_apic_ids" not in body, body
