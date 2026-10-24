"""Regression tests for AGAST #1791 (dup #1516): ritz0's named syscall builtins
under ritz1.

    let fd: i32 = open(c"/tmp/x.txt", 0x241, 420)
    let n: i64 = write(fd, c"hi", 2)
    close(fd)

ritz0 lowers a bare call to `open`, `read`, `write`, `close` or `nanosleep`
to an inline `syscall` (ritz0/emitter_llvmlite.py, `_emit_syscall`). ritz1
did not know the names, so it emitted `declare i64 @open(...)` and the
no-libc link failed with `undefined reference to 'open'`.  That was the only
blocker of examples/tier5_async/56_async_runtime.

ritz1 now redirects such a call to a reserved `weak_odr` body,
`@__ritz_builtin_<name>`, emitted next to the syscallN bodies. The reserved
name, rather than `@open` itself, is what keeps ritz0's precedence:

  * a local fn pointer of that name is called through (ritz0 checks fn-ptr
    locals before builtins);
  * a builtin beats a module's own `fn write` -- ritz0 tests the builtin
    names before user functions -- and the user's `@write` is still emitted
    for anything that takes its address, with no duplicate definition.

ritz0 accepts 1-3 arguments for any of the five and leaves unused argument
registers unset. ritz1 pads to three with zeros (one signature per body) and
rejects 0 or >3 arguments, as ritz0 does. `open` and `close` results are
narrowed to i32 like ritz0's `trunc`.

Each program returns 42 when correct and a distinct small code naming the
failed check otherwise. ritz0 is the oracle.
"""

import os
import re
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import (  # noqa: F401
    RITZ1_BIN,
    RITZ_ROOT,
    _run,
    ritz1_bin,
)

EXPECTED = 42

# Each test gets its own tmp_path; programs that touch the filesystem take
# their path from it (substituted for @DIR@) so parallel runs never collide.
PROGRAMS = {
    # --- the ticket repro ---------------------------------------------------
    "ticket_1791": """\
pub fn main() -> i32
    let fd: i32 = open(c"@DIR@/x.txt", 0x241, 420)
    if fd < 0
        return 1
    let n: i64 = write(fd, c"hi", 2)
    if close(fd) != 0
        return 2
    if n != 2
        return 3
    42
""",
    # --- each builtin, round trip ------------------------------------------
    "write_read_round_trip": """\
pub fn main() -> i32
    let wfd: i32 = open(c"@DIR@/rt.txt", 0x241, 420)
    if wfd < 0
        return 1
    if write(wfd, c"ritz!", 5) != 5
        return 2
    close(wfd)
    let rfd: i32 = open(c"@DIR@/rt.txt", 0, 0)
    if rfd < 0
        return 3
    var buf: [8]u8
    let got: i64 = read(rfd, @buf[0], 8)
    close(rfd)
    if got != 5
        return 4
    if buf[0] != 114 or buf[4] != 33
        return 5
    42
""",
    "write_to_stdout_fd": """\
pub fn main() -> i32
    let n: i64 = write(1, c"ok\\n", 3)
    if n != 3
        return 1
    42
""",
    "nanosleep_returns_zero": """\
struct Timespec
    sec: i64
    nsec: i64

pub fn main() -> i32
    var ts: Timespec = Timespec { sec: 0, nsec: 1000 }
    let r: i64 = nanosleep(@ts, 0)
    if r != 0
        return 1
    42
""",
    # --- result widths and errno passthrough --------------------------------
    "open_missing_is_enoent": """\
pub fn main() -> i32
    let fd: i32 = open(c"@DIR@/does/not/exist", 0, 0)
    if fd != -2
        return 1
    42
""",
    "close_bad_fd_is_ebadf_i32": """\
pub fn main() -> i32
    let r: i32 = close(987654)
    if r != -9
        return 1
    42
""",
    "inferred_result_types": """\
pub fn main() -> i32
    # `fd` stays typed: ritz0 treats a re-used inferred builtin result as moved.
    let fd: i32 = open(c"@DIR@/inf.txt", 0x241, 420)
    if fd < 0
        return 1
    let n = write(fd, c"abc", 3)
    let r = close(fd)
    if n != 3 or r != 0
        return 2
    42
""",
    "result_in_condition_and_arith": """\
pub fn main() -> i32
    let fd: i32 = open(c"@DIR@/cond.txt", 0x241, 420)
    if write(fd, c"abcd", 4) + 38 != 42
        return 1
    if close(fd) == 0
        return 42
    2
""",
    "args_of_narrow_types": """\
pub fn main() -> i32
    let fd: i32 = open(c"@DIR@/narrow.txt", 0x241, 420)
    let len: u8 = 3
    let n32: i32 = 2
    if write(fd, c"xyz", len) != 3
        return 1
    if write(fd, c"pq", n32) != 2
        return 2
    close(fd)
    42
""",
    # --- arity: ritz0 accepts 1..3 args -------------------------------------
    "open_with_two_args": """\
pub fn main() -> i32
    let wfd: i32 = open(c"@DIR@/two.txt", 0x241, 420)
    close(wfd)
    let fd: i32 = open(c"@DIR@/two.txt", 0)
    if fd < 0
        return 1
    close(fd)
    42
""",
    # --- precedence (ritz0: fn-ptr local > builtin > user fn) ---------------
    "builtin_beats_user_fn_of_same_name": """\
fn write(fd: i64, p: *u8, n: i64) -> i64
    99

pub fn main() -> i32
    let n: i64 = write(1, c"x\\n", 2)
    if n != 2
        return 1
    42
""",
    "user_close_returning_bool_is_shadowed": """\
fn close(fd: i32) -> bool
    true

pub fn main() -> i32
    let r: i32 = close(987654)
    if r != -9
        return 1
    42
""",
    # The shadowing fn's `-> bool` must not type the call: an inferred
    # result would become a bool and lose the -9.
    "user_close_bool_inferred_result": """\
fn close(fd: i32) -> bool
    true

pub fn main() -> i32
    let r = close(987654)
    if r != -9
        return 1
    42
""",
    # open/close results are i32 (ritz0's trunc): an inferred `var` gets an
    # i32 slot, so a store through `*i32` round-trips a negative value.
    "inferred_open_close_are_i32_slots": """\
fn set_neg(p: *i32)
    *p = -5

pub fn main() -> i32
    # Borrow-then-read only: ritz0 treats an inferred builtin result as moved
    # once passed by value.  Both start NON-negative: writing -5 into the low
    # half of an i64 slot that holds a negative value would still read -5.
    var fd = open(c"@DIR@/w.txt", 0x241, 420)
    set_neg(@fd)
    if fd != -5
        return 1
    let fd2: i32 = open(c"@DIR@/w.txt", 0, 0)
    var r = close(fd2)
    set_neg(@r)
    if r != -5
        return 2
    42
""",
    "user_close_bool_shadow_in_expressions": """\
fn close(fd: i32) -> bool
    true

fn take(x: i32) -> i32
    x

pub fn main() -> i32
    if close(987654) != -9
        return 1
    if take(close(987654)) != -9
        return 2
    var a: [2]i32 = [0, 0]
    a[0] = close(987654)
    if a[0] != -9
        return 3
    if close(987654) + 0 != -9
        return 4
    let z: bool = close(987654) == -9
    if not z
        return 5
    42
""",
    # A typed fn-pointer PARAM keeps its signature (#1671), so its call
    # reaches the regular call path, where the builtin check must yield.
    "fn_ptr_param_beats_builtin": """\
fn fake_read(fd: i64, p: *u8, n: i64) -> i64
    7

fn via(read: fn(i64, *u8, i64) -> i64) -> i64
    var b: [1]u8
    read(0, @b[0], 1)

pub fn main() -> i32
    if via(fake_read) != 7
        return 1
    42
""",
    "fn_ptr_local_beats_builtin": """\
fn fake_read(fd: i64, p: *u8, n: i64) -> i64
    7

pub fn main() -> i32
    let read: fn(i64, *u8, i64) -> i64 = fake_read
    var b: [1]u8
    if read(0, @b[0], 1) != 7
        return 1
    42
""",
    "methods_named_close_unaffected": """\
struct Thing
    v: i32

impl Thing
    fn close(self: *Thing) -> i32
        self.v

pub fn main() -> i32
    var t: Thing = Thing { v: 42 }
    t.close()
""",
}


def _program(name: str, tmp_path) -> str:
    return PROGRAMS[name].replace("@DIR@", str(tmp_path))


def _ritz1_compile(tmp_path, program: str):
    src = tmp_path / "prog.ritz"
    src.write_text(program)
    ll = tmp_path / "prog.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return comp, (ll.read_text() if ll.exists() else "")


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, _program(name, tmp_path)) == EXPECTED


# ritz1 gives every inferred `var x = f()` an i64 slot, whatever f returns
# (#1795, not specific to the builtins).  This is the one program that can see
# get_expr_type's TYPE_I32 for open/close; strict, so the fix must re-arm it.
RITZ1_XFAIL = {
    "inferred_open_close_are_i32_slots": "AGAST #1795 — inferred var slot is always i64",
}


@pytest.mark.integration
@pytest.mark.parametrize(
    "name",
    [
        pytest.param(n, marks=pytest.mark.xfail(reason=RITZ1_XFAIL[n], strict=True))
        if n in RITZ1_XFAIL
        else n
        for n in sorted(PROGRAMS)
    ],
)
def test_ritz1_named_syscall_builtins(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 left `open`/`read`/`write`/`close`/`nanosleep` undefined (#1791)."""
    assert _run("ritz1", tmp_path, name, _program(name, tmp_path)) == EXPECTED


@pytest.mark.integration
def test_ritz1_emits_no_extern_for_builtins(ritz1_bin, tmp_path):  # noqa: F811
    """The builtins resolve in-module: no `declare` for them or their bodies."""
    comp, ir = _ritz1_compile(tmp_path, _program("write_read_round_trip", tmp_path))
    assert comp.returncode == 0, comp.stderr[-2000:]
    for name in ("open", "read", "write", "close"):
        assert f"declare i64 @{name}(" not in ir, ir
        assert f"declare i64 @__ritz_builtin_{name}(" not in ir, ir
        assert f"define weak_odr i64 @__ritz_builtin_{name}(" in ir, ir


@pytest.mark.integration
def test_ritz1_builtin_calls_pass_three_args(ritz1_bin, tmp_path):  # noqa: F811
    """Every body takes three i64s; shorter calls are zero-padded to match.

    A short call still runs (the kernel ignores the unset registers), so
    only the IR shows a missing pad -- and a call whose arity disagrees with
    its in-module definition is undefined behaviour for LLVM.
    """
    comp, ir = _ritz1_compile(
        tmp_path,
        "pub fn main() -> i32\n"
        '    let fd: i32 = open(c"/nonexistent", 0)\n'
        "    close(fd)\n"
        "    42\n",
    )
    assert comp.returncode == 0, comp.stderr[-2000:]
    calls = re.findall(r"call i64 @__ritz_builtin_(\w+)\(([^)]*)\)", ir)
    assert sorted(n for n, _ in calls) == ["close", "open"], ir
    for name, args in calls:
        assert args.count("i64 ") == 3, (name, args)


@pytest.mark.integration
def test_ritz1_builtin_bodies_only_when_used(ritz1_bin, tmp_path):  # noqa: F811
    """A module that calls none of the five carries none of their bodies."""
    comp, ir = _ritz1_compile(tmp_path, "pub fn main() -> i32\n    42\n")
    assert comp.returncode == 0, comp.stderr[-2000:]
    assert "__ritz_builtin_" not in ir, ir


@pytest.mark.integration
@pytest.mark.parametrize(
    "call", ["close()", 'write(1, c"x", 1, 0)'], ids=["no_args", "four_args"]
)
def test_ritz1_rejects_bad_arity(ritz1_bin, tmp_path, call):  # noqa: F811
    """ritz0 refuses 0 or more than 3 arguments; so does ritz1."""
    comp, _ = _ritz1_compile(tmp_path, f"pub fn main() -> i32\n    {call}\n    42\n")
    assert comp.returncode != 0
    assert "takes 1 to 3 arguments" in comp.stderr, comp.stderr[-2000:]


@pytest.mark.integration
def test_ritz1_builtins_link_across_modules(ritz1_bin, tmp_path):  # noqa: F811
    """Two modules that both use `write` link: the weak_odr bodies merge."""
    pkg = tmp_path / "twomod"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "helper.ritz").write_text(
        'pub fn say() -> i64\n    write(1, c"a\\n", 2)\n'
    )
    (pkg / "src" / "main.ritz").write_text(
        "import helper\n\n"
        "pub fn main() -> i32\n"
        "    let a: i64 = say()\n"
        '    let b: i64 = write(1, c"b\\n", 2)\n'
        "    if a + b != 4\n"
        "        return 1\n"
        "    42\n"
    )
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "twomod"\nversion = "0.1.0"\n\n'
        '[build]\ntarget = "x86_64-linux"\n'
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    for compiler in ("ritz0", "ritz1"):
        proc = subprocess.run(
            [
                "python3",
                str(RITZ_ROOT / "build.py"),
                "build",
                str(pkg),
                "--no-cache",
                "--compiler",
                compiler,
            ],
            cwd=RITZ_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert proc.returncode == 0, (
            f"{compiler}:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
        )
        exes = [p for p in (pkg / "build").rglob("twomod") if p.is_file()]
        assert exes, f"{compiler}: no binary under {pkg / 'build'}"
        out = subprocess.run([str(exes[0])], capture_output=True, timeout=60)
        assert out.returncode == EXPECTED, (compiler, out)
        assert out.stdout == b"a\nb\n", (compiler, out.stdout)
        subprocess.run(["rm", "-rf", str(pkg / "build")], check=True)
