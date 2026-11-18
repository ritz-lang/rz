"""ritzlib platform layering (AGAST #1857).

Before: net.ritz and async_net.ritz each redeclared 14 Linux socket syscall
numbers with no target attribute, uring.ritz and timer.ritz added more, and
ritzlib/tests/test_memory.ritz one of its own: x86_64 Linux numbers that a
harland build would silently see. The kernel side of the same problem: every
allocator in ritzlib.memory called mmap directly, so nothing but a Linux or
harland process could supply its pages.

The contract pinned here:

* `const SYS_*` is declared in ritzlib/sys.ritz and nowhere else in ritzlib,
  and every one there carries a `[[target_os = "..."]]` attribute, so a
  target only ever sees its own table. (`target_arch` gating is LARB's to
  specify first; filed as a follow-up.)
* The collections a harland user program uses (gvec, string, hashmap, over
  memory) compile for `--target-os harland`.

The behavioural half (an injected page source whose map returns -ENOMEM
makes every allocator return null) is in ritzlib/tests/test_memory.ritz, so it
runs on every compiler.
"""

import os
import re
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZLIB = RITZ_ROOT / "ritzlib"
SYS = RITZLIB / "sys.ritz"

CONST_SYS = re.compile(r"^\s*(?:pub\s+)?const\s+(SYS_\w+)\b")
TARGET_OS = re.compile(r'^\[\[target_os\s*=\s*"\w+"\]\]')


def _sys_consts_outside_sys():
    """[(path:line, name)] for every `const SYS_*` in ritzlib but sys.ritz."""
    hits = []
    for path in sorted(RITZLIB.rglob("*.ritz")):
        if path == SYS:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            m = CONST_SYS.match(line)
            if m:
                hits.append((f"{path.relative_to(RITZ_ROOT)}:{n}", m.group(1)))
    return hits


def _ungated_sys_consts(src):
    """Names of `const SYS_*` in `src` not directly under a [[target_os]]."""
    ungated = []
    prev = ""
    for line in src.splitlines():
        m = CONST_SYS.match(line)
        if m and not TARGET_OS.match(prev):
            ungated.append(m.group(1))
        if line.strip():
            prev = line
    return ungated


@pytest.mark.unit
def test_syscall_numbers_are_declared_only_in_sys():
    hits = _sys_consts_outside_sys()
    assert not hits, "const SYS_* outside ritzlib/sys.ritz: " + repr(hits)


@pytest.mark.unit
def test_every_syscall_number_in_sys_is_target_gated():
    src = SYS.read_text()
    # Not vacuous: sys.ritz holds the table.
    assert sum(1 for l in src.splitlines() if CONST_SYS.match(l)) > 80
    ungated = _ungated_sys_consts(src)
    assert not ungated, "SYS_* in sys.ritz with no [[target_os]]: " + repr(ungated)


# --- packages outside ritzlib take their numbers from sys.ritz too (#4121) ----

# The check that no package redeclares these beside `import ritzlib.sys`
# reads every package's *.ritz, so it runs in the tools step:
# tools/test_package_syscall_numbers.py (AGAST #4032).

# Numbers zeus, ritzunit, cryptosec, mausoleum and nexus used to redeclare
# ungated; sys.ritz lacked them. x86_64 Linux ABI (arch/x86/entry/syscalls).
LINUX_ADDED = {
    "SYS_SENDMSG": 46, "SYS_RECVMSG": 47, "SYS_RT_SIGTIMEDWAIT": 128,
    "SYS_PRCTL": 157, "SYS_SETRLIMIT": 160, "SYS_FUTEX": 202,
    "SYS_GETRANDOM": 318, "SYS_MEMFD_CREATE": 319,
}
# Harland numbers indium's libharland/cat and prism used to redeclare; the
# kernel-enum diff in test_harland_syscall_dispatch.py checks their values.
HARLAND_ADDED = {"SYS_OPEN", "SYS_CLOSE", "SYS_FB_INFO", "SYS_FB_MAP"}
SYS_VALUE = re.compile(r"^\s*(?:pub\s+)?const\s+(SYS_\w+)\s*:\s*\w+\s*=\s*(\d+)")


def _gated_table(src, os_name):
    """{SYS_NAME: number} for each const directly under [[target_os = os_name]]."""
    table = {}
    prev = ""
    for line in src.splitlines():
        m = SYS_VALUE.match(line)
        if m and prev.strip() == f'[[target_os = "{os_name}"]]':
            table[m.group(1)] = int(m.group(2))
        if line.strip():
            prev = line
    return table


@pytest.mark.unit
def test_sys_declares_the_numbers_packages_used_to_redeclare():
    src = SYS.read_text()
    linux = _gated_table(src, "linux")
    assert {k: linux.get(k) for k in LINUX_ADDED} == LINUX_ADDED
    assert HARLAND_ADDED <= set(_gated_table(src, "harland"))


@pytest.mark.unit
def test_gating_check_sees_an_ungated_const():
    src = ('[[target_os = "linux"]]\nconst SYS_A: i64 = 1\n'
           'const SYS_B: i64 = 2\n'
           '[[target_os = "harland"]]\n\nconst SYS_C: i64 = 3\n')
    assert _ungated_sys_consts(src) == ["SYS_B"]


# A harland user program on the core collections (rzsh does this for real).
# The collections are core and no longer import sys (AGAST #4119): the program
# does, so its pages come from sys's ritz_platform_page_map, harland's mmap.
HARLAND_COLLECTIONS = """\
import ritzlib.sys
import ritzlib.gvec
import ritzlib.string
import ritzlib.hashmap

fn main() -> i32
    var v: Vec<i64> = vec_new<i64>()
    vec_push<i64>(@&v, 7)
    var s: String = string_new()
    string_push(@&s, 65)
    var m: HashMapI64 = hashmap_i64_new()
    hashmap_i64_insert(@&m, 1, 2)
    return v.len as i32
"""


@pytest.mark.integration
def test_core_collections_build_for_harland(tmp_path):
    src = tmp_path / "harland_vec.ritz"
    src.write_text(HARLAND_COLLECTIONS)
    ll = tmp_path / "harland_vec.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(src), "-o", str(ll), "--target-os", "harland"],
                     cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0, comp.stderr[-3000:]
    ir = ll.read_text()
    # It is the harland build: sys_mmap_anon's harland body (4-arg mmap).
    assert "sys_mmap_anon" in ir
    assert "ritz_platform_page_map" in ir
