"""Harland's syscall handlers and their runtime live in syscall/runtime/* (AGAST #2751).

#1844 splits kernel/src/main.ritz by subsystem. This slice (#1844.5) moves every
`sys_*_impl` body, every per-syscall `sys_*_handler`, the dispatch-table fill
(syscall_table_init), the SYSCALL MSR setup (syscall_init) and the asm entry
target (syscall_handler) out of main.ritz into one module per area under
syscall/runtime/. It is a re-port of the #1844 branch's split onto main's
design, not a replay: #2121's fn-pointer table on `enum Syscall: u64` stays
(syscall/dispatch.ritz), as do #2123's Errno returns, #2132's whole-frame
parent resume and #2143's mb2 framebuffer.

The checks are structural, at source level:

* each moved fn, global and constant is defined in its area module, and
  main.ritz defines none of them;
* syscall_table_init still registers the same handlers, each imported from
  the module that defines it;
* the SYS_OPEN workaround (save/restore g_child_pid and g_has_parent around
  sys_open; removed later by #1877) moved with the open handler, into the
  module that owns those globals;
* symbols bound by name from outside Ritz (`call syscall_handler` in
  syscall_entry.s, `extern fn alloc_user_stack` in loader/elf.ritz) stay `pub`;
* main.ritz's SLOC (ritz-metrics) dropped by the size of the move.

Behaviour is unchanged by construction; the OVMF Tier-1 boot
(tools/test_tier1_boot.sh) is the runtime check.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
HARLAND = RITZ0_DIR.parents[1] / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
MAIN = KERNEL_SRC / "main.ritz"
RUNTIME = KERNEL_SRC / "syscall" / "runtime"
METRICS = RITZ0_DIR.parents[1] / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

# area module -> the fns it now defines.
AREAS = {
    "entry": ["syscall_init", "syscall_table_init", "syscall_handler"],
    "process": [
        "current_pid", "syscall_strlen", "prints_str", "process_enter_init",
        "elf_status_errno", "sys_spawn_impl", "sys_spawn_args_impl", "sys_exit_impl", "sys_wait_impl",
        "sys_exit_handler", "sys_open_handler", "sys_spawn_handler", "sys_spawn_args_handler",
        "sys_wait_handler", "sys_getpid_handler", "sys_yield_handler", "sys_acpi_poweroff_handler",
    ],
    "file": [
        "sys_readdir_impl",
        "sys_close_handler", "sys_lseek_handler", "sys_mkdir_handler", "sys_write_handler",
        "sys_read_handler", "sys_readdir_handler",
    ],
    "ipc": [
        "sys_channel_create_handler", "sys_ipc_send_handler", "sys_ipc_recv_handler",
        "sys_ipc_close_handler", "sys_cap_grant_handler", "sys_cap_revoke_handler",
        "sys_cap_derive_handler", "sys_cap_info_handler", "sys_cap_check_handler",
    ],
    "memory": [
        "alloc_user_stack", "free_user_stack", "sys_mmap_impl", "sys_munmap_impl",
        "sys_mmap_handler", "sys_munmap_handler",
    ],
    "cwd": ["init_cwd", "sys_getcwd_impl", "sys_chdir_impl", "sys_getcwd_handler", "sys_chdir_handler"],
    "input": ["sys_input_poll_impl", "sys_input_read_impl", "sys_input_poll_handler", "sys_input_read_handler"],
    "framebuffer": ["sys_fb_info_impl", "sys_fb_map_impl", "sys_fb_info_handler", "sys_fb_map_handler"],
}

VARS = {
    "process": ["g_parent_ctx", "g_parent_frame", "g_has_parent", "g_child_pid", "g_child_pml4",
                "g_child_exit_code"],
    "memory": ["g_next_mmap_addr"],
    "cwd": ["g_cwd", "g_cwd_len"],
    "framebuffer": ["g_user_fb_mapped", "g_user_fb_addr"],
}

CONSTS = {
    "entry": ["MSR_EFER", "MSR_STAR", "MSR_LSTAR", "MSR_SFMASK", "EFER_SCE"],
    "memory": ["PROT_READ", "PROT_WRITE", "PROT_EXEC", "MAP_PRIVATE", "MAP_ANONYMOUS", "MAP_FIXED",
               "USER_MMAP_START", "USER_MMAP_END", "USER_STACK_PAGES", "USER_STACK_SIZE",
               "USER_STACK_TOP", "USER_STACK_BASE"],
    "framebuffer": ["FBINFO_SIZE"],
}

# What main.ritz still calls (kernel_main, run_init), by area.
MAIN_USES = {
    "entry": {"syscall_init"},
    "cwd": {"init_cwd"},
    "memory": {"alloc_user_stack"},
    "process": {"process_enter_init"},
}

# Called by name from outside Ritz's import system.
EXTERN_BOUND = {"entry": {"syscall_handler"}, "memory": {"alloc_user_stack"}}

# main.ritz SLOC (ritz-metrics) before this move, and the ceiling after it.
SLOC_BEFORE = 1336
SLOC_AFTER_MAX = 600


def _code(path):
    """Source with `#` comments stripped (no `#` occurs inside a string literal here)."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _fns(code):
    return {m.group(2): bool(m.group(1)) for m in re.finditer(r"^(pub\s+)?fn\s+(\w+)\s*\(", code, re.M)}


def _vars(code):
    return set(re.findall(r"^(?:pub\s+)?var\s+(\w+)\s*:", code, re.M))


def _consts(code):
    return set(re.findall(r"^(?:pub\s+)?const\s+(\w+)\s*:", code, re.M))


def _imports_from(code, module):
    m = re.search(rf"^import {re.escape(module)}\s*\{{([^}}]*)\}}", code, re.M)
    return set(re.findall(r"\w+", m.group(1))) if m else None


def _area(name):
    return RUNTIME / f"{name}.ritz"


def _body(code, fn):
    m = re.search(rf"^(?:pub\s+)?fn {fn}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"no fn {fn}"
    return m.group(0)


@pytest.mark.parametrize("area", sorted(AREAS))
def test_area_module_defines_its_code(area):
    path = _area(area)
    assert path.exists(), f"{path.relative_to(KERNEL_SRC)} does not exist"
    code = _code(path)
    missing = sorted(set(AREAS[area]) - set(_fns(code)))
    assert not missing, f"not defined in {area}.ritz: {missing}"
    assert not set(VARS.get(area, [])) - _vars(code), sorted(set(VARS.get(area, [])) - _vars(code))
    assert not set(CONSTS.get(area, [])) - _consts(code), sorted(set(CONSTS.get(area, [])) - _consts(code))


def test_each_fn_defined_once_across_the_kernel():
    """Kernel symbols are global (`extern fn` binds by bare name), so a moved fn
    must not survive as a second definition anywhere."""
    moved = {fn for fns in AREAS.values() for fn in fns}
    seen = {}
    for p in KERNEL_SRC.rglob("*.ritz"):
        for fn in _fns(_code(p)):
            if fn in moved:
                seen.setdefault(fn, []).append(str(p.relative_to(KERNEL_SRC)))
    dup = {fn: ps for fn, ps in seen.items() if len(ps) > 1}
    assert not dup, dup


def test_main_defines_none_of_it():
    code = _code(MAIN)
    fns = _fns(code)
    left = sorted(f for f in fns if re.fullmatch(r"sys_\w+_(impl|handler)", f)
                  or f in {fn for fns in AREAS.values() for fn in fns})
    assert not left, f"main.ritz still defines {left}"
    all_vars = {v for vs in VARS.values() for v in vs}
    assert not all_vars & _vars(code), sorted(all_vars & _vars(code))
    all_consts = {c for cs in CONSTS.values() for c in cs}
    assert not all_consts & _consts(code), sorted(all_consts & _consts(code))
    assert not re.search(r"^\s+syscall_register\(", code, re.M), "main.ritz still fills the table"
    assert "struct ParentContext" not in code


def test_main_imports_what_it_calls():
    code = _code(MAIN)
    for area, uses in MAIN_USES.items():
        imported = _imports_from(code, f"syscall.runtime.{area}")
        assert imported == uses, f"main.ritz imports {imported} from syscall.runtime.{area}, want {uses}"
        fns = _fns(_code(_area(area)))
        assert all(fns.get(n) for n in uses), f"not pub in {area}.ritz: {uses}"


def test_run_init_enters_pid1_through_process():
    """run_init no longer writes process.ritz's globals itself: it asks
    process_enter_init for PID 1, then jumps to /bin/init."""
    body = _body(_code(MAIN), "run_init")
    assert not re.search(r"\bg_(has_parent|child_\w+|parent_\w+)\b", body), body
    assert body.index("process_enter_init()") < body.index("jump_to_userspace("), body


def test_extern_bound_symbols_stay_pub():
    for area, names in EXTERN_BOUND.items():
        fns = _fns(_code(_area(area)))
        assert all(fns.get(n) for n in names), {n: fns.get(n) for n in names}
    assert re.search(r"^\s+call syscall_handler$", (HARLAND / "kernel" / "syscall_entry.s").read_text(), re.M)
    assert re.search(r"^extern fn alloc_user_stack\(\) -> u64$", _code(KERNEL_SRC / "loader" / "elf.ritz"), re.M)


def test_table_registers_handlers_imported_from_their_area():
    """syscall_table_init fills the #2121 table with the same handlers as before,
    each taken from the area module that defines it."""
    code = _code(_area("entry"))
    regs = re.findall(r"^\s+syscall_register\(Syscall\.(\w+),\s*(\w+)\)", _body(code, "syscall_table_init"), re.M)
    assert len(regs) == 32, regs
    for _, handler in regs:
        owner = [a for a, fns in AREAS.items() if handler in fns]
        assert len(owner) == 1, f"{handler} is defined in no area module"
        imported = _imports_from(code, f"syscall.runtime.{owner[0]}") or set()
        assert handler in imported, f"entry.ritz doesn't import {handler} from syscall.runtime.{owner[0]}"
        assert _fns(_code(_area(owner[0])))[handler], f"{handler} is not pub in {owner[0]}.ritz"
    # The branch's 29-arm ladder is not what came across.
    assert not re.search(r"\brax == ", code), "an `if rax ==` ladder is back"
    assert "syscall_table_init()" in _body(code, "syscall_init")


def test_sys_open_workaround_moved_with_the_open_handler():
    """The open handler saves g_child_pid/g_has_parent, calls sys_open, and
    restores them (the large-struct-return corruption; removed by #1877), in
    the module that owns those globals."""
    code = _code(_area("process"))
    assert {"g_child_pid", "g_has_parent"} <= _vars(code)
    body = _body(code, "sys_open_handler")
    steps = [
        r"let saved_child_pid: u64 = g_child_pid",
        r"let saved_has_parent: u8 = g_has_parent",
        r"let result: i64 = sys_open\(rdi as \*u8, rsi, rdx as i32\)",
        r"g_child_pid = saved_child_pid",
        r"g_has_parent = saved_has_parent",
        r"return result",
    ]
    pos = [re.search(s, body) for s in steps]
    assert all(pos), {s: bool(p) for s, p in zip(steps, pos)}
    assert [p.start() for p in pos] == sorted(p.start() for p in pos), body
    # Its comment travelled with it.
    assert "WORKAROUND" in _area("process").read_text()


@pytest.mark.integration   # runs ritz-metrics in a subprocess (AGAST #1805)
def test_main_sloc_dropped(tmp_path):
    out = tmp_path / "m.json"
    proc = subprocess.run([sys.executable, str(METRICS), "--json", str(out), str(MAIN)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    sloc = json.loads(out.read_text())["files"][0]["sloc"]
    assert sloc <= SLOC_AFTER_MAX, f"main.ritz SLOC {sloc} (was {SLOC_BEFORE})"
