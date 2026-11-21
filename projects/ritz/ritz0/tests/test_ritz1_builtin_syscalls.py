"""AGAST #3243: `open`, `read`, `write`, `close` and `nanosleep` are ordinary
identifiers on ritz0, ritz1 and ritz1_selfhosted.

They used to be syscall builtins. ritz0 lowered a bare `write(fd, p, n)` to an
inline `syscall` and tested the five names BEFORE user functions, so a module's
own `fn open(id: i32) -> Result<T, i32>` never received its call. #1791 copied
that precedence into ritz1 (a redirect to `@__ritz_builtin_<name>`). The
ticket's repro, a user `open` returning a Result and taken apart with `?`,
compiled to a raw `open(2)` syscall instead.

The rule now (LANGUAGE_SPEC §4, AGAST #3243): a call to one of the five
resolves exactly like any other call, to a declared, imported or `extern` fn of
that name. With nothing of that name it is an unknown function, for `write` as
for any other name: every compiler refuses it at the call, located, in ritz0's
words (AGAST #3255; ritz1 used to leave it to the no-libc link).
Syscalls are reached through ritzlib.sys (`sys_write`, `sys_read`, `sys_open`,
`sys_open3`, `sys_close`, `sys_nanosleep`) or `syscallN`.

`syscallN`, `__syscallN` and `cpuid_raw` went the same way (AGAST #3397):
`syscall0..6` are `asm` fns in ritzlib.sys and `cpuid_raw` one in
cryptosec.cpuid, so with no declaration in scope each is an unknown function.

Each program returns 42 when correct and a distinct small code naming the
failed check otherwise.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import RITZ_ROOT, RITZ_START, _run_pkg

pytestmark = pytest.mark.integration

EXPECTED = 42
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

# The ticket's repro, made observable: `g` reaches the user's `open`.
REPRO = """\
struct T
    id: i32

fn open(id: i32) -> Result<T, i32>
    return Ok(T { id: id })

fn g() -> Result<i32, i32>
    var t = open(1)?
    return Ok(t.id + 41)

pub fn main() -> i32
    match g()
        Ok(v) => v
        Err(e) => 1
"""

# A user fn of each name is called, whatever its signature: arities the
# builtins refused (0, 4), a bool `close`, a `write` that is no syscall.
USER_FNS = """\
fn write(fd: i64, p: *u8, n: i64) -> i64
    99

fn read(x: i32) -> i32
    x + 1

fn close(fd: i32) -> bool
    fd == 5

fn nanosleep() -> i32
    7

fn open(a: i32, b: i32, c: i32, d: i32) -> i32
    a + b + c + d

pub fn main() -> i32
    if write(1, c"x", 1) != 99
        return 1
    if read(2) != 3
        return 2
    if not close(5)
        return 3
    if nanosleep() != 7
        return 4
    if open(1, 2, 3, 4) != 10
        return 5
    42
"""

PROGRAMS = {"repro_3243": REPRO, "user_fns_of_each_name": USER_FNS}

# Nothing named `write` anywhere: an unknown function like any other (`frob`).
UNDECLARED = """\
pub fn main() -> i32
    var b: [3]u8
    let p: *u8 = @b[0]
    write(1, p, 3)
    42
"""

# The syscalls, through ritzlib.sys. @DIR@ is the test's tmp_path.
VIA_SYS = """\
import ritzlib.sys

pub fn main() -> i32
    let wfd: i32 = sys_open3(c"@DIR@/rt.txt", 0x241, 420)
    if wfd < 0
        return 1
    if sys_write(wfd, c"ritz!", 5) != 5
        return 2
    if sys_close(wfd) != 0
        return 3
    let rfd: i32 = sys_open(c"@DIR@/rt.txt", 0)
    if rfd < 0
        return 4
    var buf: [8]u8
    let got: i64 = sys_read(rfd, @buf[0], 8)
    sys_close(rfd)
    if got != 5 or buf[0] != 114 or buf[4] != 33
        return 5
    var ts: [2]i64 = [0, 1000]
    if sys_nanosleep(@ts[0], null) != 0
        return 6
    if syscall0(39) <= 0
        return 8
    if sys_write(1, c"ok\\n", 3) != 3
        return 7
    42
"""


def _compile(request, compiler: str, tmp_path: Path, source: str):
    """Compile one module; return (process, path of the .ll)."""
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
        return proc, ll
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _link(compiler: str, tmp_path: Path, ll: Path):
    exe = tmp_path / "unit"
    cmd = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    return fast_link.clang(cmd, cwd=tmp_path, capture_output=True, text=True), exe


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_user_fn_of_a_former_builtin_name_is_called(request, tmp_path, compiler, name):
    proc, ll = _compile(request, compiler, tmp_path, PROGRAMS[name])
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-2000:]}"
    link, exe = _link(compiler, tmp_path, ll)
    assert link.returncode == 0, f"{compiler}, {name}:\n{link.stderr[-2000:]}"
    got = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert got == EXPECTED, f"{compiler}, {name}: exit {got}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", ["write", "frob", "syscall3", "__syscall3", "cpuid_raw"])
def test_undeclared_fn_is_refused_at_the_call(request, tmp_path, compiler, name):
    """AGAST #3255: ritz1 accepted the call, declared `@write(...)` and left
    it to the link, whose "undefined reference" names no line.  #3397: the
    names the compilers used to lower themselves are no exception."""
    proc, ll = _compile(request, compiler, tmp_path, UNDECLARED.replace("write(", f"{name}("))
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out[-2000:]
    sep = "" if compiler == "ritz0" else "error: "
    assert re.search(rf"unit\.ritz:4:5: {sep}Unknown function: {name}$", out, re.M), out[-2000:]
    assert "Traceback" not in out, out[-2000:]
    assert not ll.exists()


@pytest.mark.parametrize("compiler", COMPILERS)
def test_syscalls_through_ritzlib_sys(tmp_path, compiler):
    program = VIA_SYS.replace("@DIR@", str(tmp_path))
    assert _run_pkg(compiler, tmp_path, "via_sys", program) == EXPECTED
