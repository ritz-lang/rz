"""Harland dispatches syscalls through a table keyed by `enum Syscall: u64` (AGAST #2121).

syscall_handler (kernel/src/main.ritz) was a 29-arm `if rax == SYS_X` ladder,
cyclomatic complexity 62. #1880 gave the language enums with explicit
discriminants and `E.from(v) -> Option<E>`; harland now declares its syscall
ABI as `pub enum Syscall: u64` (syscall/numbers.ritz) and dispatches through a
handler table (syscall/dispatch.ritz) that main.ritz fills once at init.

The tests compile the real harland modules into small host programs, so each
claim is checked as behaviour on every compiler:

* the enum's discriminants are exactly the syscall ABI user programs rely on;
* the table calls the registered handler with the caller's arguments, and an
  unregistered, undeclared or out-of-range number gets Errno.NoSys (-ENOSYS);

plus the ticket's acceptance at source level: ritz-metrics reports
syscall_handler CC <= 15, and the kernel registers the same syscalls the
ladder dispatched.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
HARLAND = RITZ_ROOT.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
METRICS = RITZ_ROOT.parent / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The syscall ABI, as user programs (ritzlib/sys.ritz, indium) encode it.
# Changing a number here is an ABI break, not a refactor.
# Stat (4), SpawnEx (28), Pipe (29), IpcCall (32), NetInfo (60) and NetPing (61)
# were declared but never dispatched, so every call got an error (AGAST #2122):
# they are gone, and their numbers are free.
ABI = {
    "Read": 0, "Write": 1, "Open": 2, "Close": 3, "Lseek": 8,
    "Mmap": 9, "Munmap": 11, "Readdir": 17,
    "Exit": 20, "Spawn": 21, "Wait": 22, "Getpid": 23, "Yield": 24,
    "SpawnArgs": 25, "Getcwd": 26, "Chdir": 27,
    "IpcSend": 30, "IpcRecv": 31, "IpcClose": 33,
    "CapGrant": 40, "CapRevoke": 41, "CapDerive": 42, "CapInfo": 43, "CapCheck": 44,
    "InputPoll": 50, "InputRead": 51,
    "Mkdir": 83,
    "ChannelCreate": 100,
    "AcpiPoweroff": 200,
    "FbInfo": 210, "FbMap": 211,
    "DebugPrint": 255,
}

# What the old `if rax ==` ladder dispatched (Write and DebugPrint shared an arm),
# plus Lseek and Mkdir, whose fs/syscall.ritz implementations were never wired
# up (AGAST #2122). Every declared syscall is dispatched: see
# test_every_declared_syscall_is_dispatched.
DISPATCHED = {
    "Exit", "Open", "Close", "Write", "DebugPrint", "Read", "Yield", "Getpid",
    "Readdir", "Spawn", "SpawnArgs", "Wait", "ChannelCreate", "IpcSend",
    "IpcRecv", "IpcClose", "CapGrant", "CapRevoke", "CapDerive", "CapInfo",
    "CapCheck", "Mmap", "Munmap", "Getcwd", "Chdir", "InputPoll", "InputRead",
    "AcpiPoweroff", "FbInfo", "FbMap", "Lseek", "Mkdir",
}


def _compile(compiler, tmp_path, src, name, extra=()):
    path = tmp_path / f"{name}.ritz"
    path.write_text(src)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{KERNEL_SRC}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0 and ll.exists(), \
        f"{compiler} rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(compiler, tmp_path, src, modules):
    """Compile `src` and each harland module (own object each, as a build does), link, run."""
    objs = []
    for mod in modules:
        text = (KERNEL_SRC / (mod.replace(".", "/") + ".ritz")).read_text()
        extra = ("--no-runtime",) if compiler == "ritz0" else ()
        objs.append(str(_compile(compiler, tmp_path, text, mod.replace(".", "_"), extra)))
    objs.insert(0, str(_compile(compiler, tmp_path, src, "t")))
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# --- the enum is the ABI -------------------------------------------------------

def _abi_program():
    checks = "\n".join(
        f"    if Syscall.{name} as u64 != {num}\n        return {i + 1}"
        for i, (name, num) in enumerate(ABI.items()))
    return f"""\
import ritzlib.option
import syscall.numbers

fn main() -> i32
{checks}
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_syscall_enum_discriminants_are_the_abi(compiler, tmp_path):
    rc = _run(compiler, tmp_path, _abi_program(), ["syscall.numbers"])
    names = list(ABI)
    assert rc == 0, f"{compiler}: Syscall.{names[rc - 1]} is not {ABI[names[rc - 1]]}" \
        if 0 < rc <= len(names) else f"{compiler}: exit {rc}"


def test_syscall_enum_declares_exactly_the_abi():
    src = (KERNEL_SRC / "syscall" / "numbers.ritz").read_text()
    m = re.search(r"^pub enum Syscall: u64\n((?:[ \t]+.*\n|[ \t]*\n|#.*\n)+)", src, re.M)
    assert m, "syscall/numbers.ritz has no `pub enum Syscall: u64`"
    declared = dict(re.findall(r"^\s+(\w+)\s*=\s*(\d+)", m.group(1), re.M))
    assert {k: int(v) for k, v in declared.items()} == ABI
    # One declaration of each number in this module: the loose consts are gone.
    assert not re.search(r"^pub const SYS_", src, re.M), "SYS_* consts still beside the enum"


# --- the dispatch table ----------------------------------------------------------

DISPATCH = """\
import ritzlib.option
import syscall.errno
import syscall.numbers
import syscall.dispatch

fn h_sum(a: u64, b: u64, c: u64, d: u64) -> i64
    (a + b * 10 + c * 100 + d * 1000) as i64

fn h_seven(a: u64, b: u64, c: u64, d: u64) -> i64
    7

fn main() -> i32
    syscall_register(Syscall.Write, h_sum)
    syscall_register(Syscall.DebugPrint, h_sum)
    syscall_register(Syscall.Read, h_seven)
    # Registered: the handler runs with the caller's four arguments.
    if syscall_dispatch(1, 1, 2, 3, 4) != 4321
        return 1
    if syscall_dispatch(255, 4, 3, 2, 1) != 1234
        return 2
    if syscall_dispatch(0, 0, 0, 0, 0) != 7
        return 3
    if not syscall_has_handler(1)
        return 4
    # Declared (Open) but not registered by this program.
    if syscall_has_handler(2) or syscall_dispatch(2, 0, 0, 0, 0) != Errno.NoSys as i64
        return 5
    # Not a syscall number at all, inside and beyond the table.
    if syscall_has_handler(5) or syscall_dispatch(5, 0, 0, 0, 0) != Errno.NoSys as i64
        return 6
    if syscall_has_handler(256) or syscall_dispatch(256, 0, 0, 0, 0) != Errno.NoSys as i64
        return 7
    if syscall_dispatch(0xFFFFFFFFFFFFFFFF, 0, 0, 0, 0) != Errno.NoSys as i64
        return 8
    if Errno.NoSys as i64 != -38
        return 9
    # Re-registering replaces the handler.
    syscall_register(Syscall.Read, h_sum)
    if syscall_dispatch(0, 1, 0, 0, 0) != 1
        return 10
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_dispatch_table(compiler, tmp_path):
    assert _run(compiler, tmp_path, DISPATCH, ["syscall.errno", "syscall.numbers", "syscall.dispatch"]) == 0


# --- the kernel's use of it ------------------------------------------------------

def test_syscall_handler_cc_at_most_15(tmp_path):
    out = tmp_path / "m.json"
    proc = subprocess.run([sys.executable, str(METRICS), "--json", str(out),
                           str(KERNEL_SRC / "main.ritz")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    fns = [f for f in json.loads(out.read_text())["functions"] if f["name"] == "syscall_handler"]
    assert len(fns) == 1, fns
    assert fns[0]["complexity"] <= 15, f"syscall_handler CC {fns[0]['complexity']}"


def test_kernel_registers_every_dispatched_syscall():
    src = (KERNEL_SRC / "main.ritz").read_text()
    regs = re.findall(r"^\s+syscall_register\(Syscall\.(\w+),\s*(\w+)\)", src, re.M)
    names = [n for n, _ in regs]
    assert len(names) == len(set(names)), f"registered twice: {names}"
    assert set(names) == DISPATCHED
    assert not re.search(r"\brax == SYS_", src), "the `if rax ==` ladder is back"


def test_syscall_init_fills_the_table(tmp_path):
    """main.ritz compiles as `rz build harland` does, and syscall_init (run before
    any user program) fills the table: without it every syscall is ENOSYS."""
    out = tmp_path / "main.ll"
    proc = subprocess.run(
        [sys.executable, str(RITZ0_DIR / "ritz0.py"), str(KERNEL_SRC / "main.ritz"), "-o", str(out),
         "--no-runtime", "--project-root", str(HARLAND), "--sources", '["kernel/src"]',
         "--target", "x86_64-none-elf"],
        capture_output=True, text=True, cwd=RITZ0_DIR, timeout=300,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)))
    assert proc.returncode == 0 and out.exists(), proc.stdout + proc.stderr
    ir = out.read_text()
    m = re.search(r'^define [^\n]*@"syscall_init"\(.*?^}', ir, re.M | re.S)
    assert m, "no definition of syscall_init"
    assert '@"syscall_table_init"(' in m.group(0), m.group(0)


# --- one ABI: ritzlib's harland numbers are the kernel's (AGAST #2122) -----------

RITZLIB_SYS = RITZ_ROOT / "ritzlib" / "sys.ritz"


def _kernel_enum():
    """{variant: number} as syscall/numbers.ritz declares `enum Syscall: u64`."""
    src = (KERNEL_SRC / "syscall" / "numbers.ritz").read_text()
    m = re.search(r"^pub enum Syscall: u64\n((?:[ \t]+.*\n|[ \t]*\n|#.*\n)+)", src, re.M)
    assert m, "syscall/numbers.ritz has no `pub enum Syscall: u64`"
    return {k: int(v) for k, v in re.findall(r"^\s+(\w+)\s*=\s*(\d+)", m.group(1), re.M)}


def _ritzlib_harland_numbers(src):
    """{SYS_NAME: number} for every `const SYS_*` a harland build of ritzlib sees:
    those under `[[target_os = "harland"]]` and those with no target attribute."""
    nums = {}
    attr = None
    for line in src.splitlines():
        a = re.match(r'^\[\[target_os\s*=\s*"(\w+)"\]\]', line)
        if a:
            attr = a.group(1)
            continue
        c = re.match(r"^(?:pub\s+)?const\s+(SYS_\w+)\s*:\s*\w+\s*=\s*(\d+)", line)
        if c and attr in (None, "harland"):
            assert c.group(1) not in nums, f"ritzlib declares {c.group(1)} twice for harland"
            nums[c.group(1)] = int(c.group(2))
        if line.strip() and not line.startswith("#"):
            attr = None
    return nums


def _variant(sys_name):
    """SYS_SPAWN_ARGS -> SpawnArgs: the Syscall variant a ritzlib constant names."""
    return "".join(w.capitalize() for w in sys_name[len("SYS_"):].split("_"))


def test_ritzlib_harland_numbers_match_kernel():
    """ritzlib/sys.ritz can't import a kernel module, so its harland block keeps
    its own SYS_* constants; this diff is what keeps them from drifting. Each one
    names a Syscall variant with the same number, and so is dispatched."""
    kernel = _kernel_enum()
    lib = _ritzlib_harland_numbers(RITZLIB_SYS.read_text())
    # Not vacuous: the parser sees the shared, the platform-split and the
    # harland-only constants.
    assert {"SYS_READ", "SYS_WRITE", "SYS_EXIT", "SYS_MMAP", "SYS_INPUT_READ"} <= set(lib), lib
    wrong = {n: (v, kernel.get(_variant(n))) for n, v in lib.items() if kernel.get(_variant(n)) != v}
    assert not wrong, "ritzlib SYS_* (value, kernel Syscall value) disagree: " + repr(wrong)


def test_ritzlib_diff_sees_a_drifted_number():
    """The diff's parser on a ritzlib that disagrees with the kernel: a harland
    constant is picked up (and a Linux one is not), so a wrong number shows."""
    src = ('[[target_os = "linux"]]\nconst SYS_MMAP: i64 = 9\n'
           '[[target_os = "harland"]]\nconst SYS_MMAP: i64 = 10\n'
           'const SYS_READ: i64 = 0\n')
    assert _ritzlib_harland_numbers(src) == {"SYS_MMAP": 10, "SYS_READ": 0}
    assert _kernel_enum()[_variant("SYS_MMAP")] != 10


def test_every_declared_syscall_is_dispatched():
    """No declared-but-undispatched syscalls: a user program can only name a
    number the kernel has a handler for (anything else answers ENOSYS)."""
    src = (KERNEL_SRC / "main.ritz").read_text()
    registered = set(re.findall(r"^\s+syscall_register\(Syscall\.(\w+),", src, re.M))
    assert set(_kernel_enum()) == registered, \
        f"declared, not dispatched: {sorted(set(_kernel_enum()) - registered)}"


def test_no_second_kernel_syscall_table():
    """The dead arch/x86_64/syscall.ritz (SYS_MMAP = 10 against numbers.ritz's 9)
    is gone, and nothing points readers at it."""
    assert not (KERNEL_SRC / "arch" / "x86_64" / "syscall.ritz").exists()
    for p in [HARLAND / "kernel" / "user_program.s", HARLAND / "build.py"]:
        assert "arch/x86_64/syscall.ritz" not in p.read_text(), p


# --- indium user programs speak the same ABI (AGAST #2133) ----------------------

INDIUM_USER = RITZ_ROOT.parent / "indium" / "user"


def _indium_drift():
    """{file: {SYS_NAME: (value, kernel value)}} for every `const SYS_*` an indium
    user program declares for harland (harland-targeted or untargeted) whose
    number is not the kernel's. Linux branches ([[target_os = "linux"]]) are
    another ABI and are skipped."""
    kernel = _kernel_enum()
    drift = {}
    for path in sorted(INDIUM_USER.glob("*.ritz")):
        nums = _ritzlib_harland_numbers(path.read_text())
        wrong = {n: (v, kernel.get(_variant(n))) for n, v in nums.items()
                 if kernel.get(_variant(n)) != v}
        if wrong:
            drift[path.name] = wrong
    return drift


def test_indium_user_sys_numbers_match_kernel():
    """Every SYS_* number an indium user program declares for harland is the
    kernel's `enum Syscall` number: a private table can't send Yield as Spawn."""
    scanned = {p.name: _ritzlib_harland_numbers(p.read_text()) for p in INDIUM_USER.glob("*.ritz")}
    # Not vacuous: the scan reaches the programs that still declare numbers.
    assert {"SYS_OPEN", "SYS_CLOSE"} <= set(scanned["libharland.ritz"]), scanned
    assert scanned["minimal_syscall.ritz"] == {"SYS_EXIT": 20}, scanned
    assert scanned["portable_hello.ritz"] == {"SYS_WRITE": 1, "SYS_EXIT": 20}, scanned
    drift = _indium_drift()
    assert not drift, "indium SYS_* (value, kernel Syscall value) disagree: " + repr(drift)


def test_portable_getpid_takes_its_syscalls_from_ritzlib():
    """portable_getpid is harland-only: it uses ritzlib.sys's wrappers, which the
    #2122 diff pins to the kernel, rather than its own table, and its bin is
    built for target_os harland so ritzlib selects the harland numbers."""
    src = (INDIUM_USER / "portable_getpid.ritz").read_text()
    assert not re.search(r"^\s*(?:pub\s+)?const\s+SYS_", src, re.M), "private SYS_* table is back"
    m = re.search(r"^import ritzlib\.sys \{([^}]*)\}", src, re.M)
    assert m and {"sys_write", "sys_exit", "sys_yield", "sys_getpid"} <= \
        set(re.findall(r"\w+", m.group(1))), "portable_getpid doesn't import ritzlib.sys's wrappers"
    toml = (RITZ_ROOT.parent / "indium" / "ritz.toml").read_text()
    b = re.search(r'^name = "portable_getpid"\n((?:(?!\[).*\n)*)', toml, re.M)
    assert b and re.search(r'^target_os = "harland"$', b.group(1), re.M), b and b.group(1)
