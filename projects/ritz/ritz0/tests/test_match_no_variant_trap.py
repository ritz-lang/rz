"""AGAST #4586: an exhaustive `match` on a repr enum traps on a value that
names no variant.

LANGUAGE_SPEC §10.1: an `enum E: <int>` stores its discriminant (#4574), so
memory read as one can hold a value no variant has (zeroed memory where no
variant is 0, or bytes written as an integer).  A `match` that names every
variant and has no `_` or binding arm then has no arm for it: it stops the
program, writing

    <file>:<line>:<col>: match on <E>: value <v> names no variant

to stderr and exiting 1, where <line>:<col> is the `match` and <v> the raw
discriminant (signed for an `iN` repr, unsigned for a `uN` one).  Before
this, that path was `unreachable`: undefined behaviour.

A `_` or binding arm takes such a value instead, and a value that is a
variant's discriminant takes its own arm; neither traps.

Rows are sized to the rule: the trap's message for a value-yielding match
(signed zero), a statement match (signed negative, ritz1's void-arm path)
and an unsigned repr, plus one program for the no-trap cases.  All three
compilers must agree byte for byte.
"""

import os
import subprocess

import fast_link
import pytest
from ritz0_inproc import run_ritz0
from test_enum_discriminants import COMPILERS, RITZ_ROOT, RITZ_START, _ir

pytestmark = pytest.mark.integration


def _run_full(compiler, tmp_path, src):
    """Compile, link and run `src` as t.ritz: (exit code, stdout, stderr)."""
    objs = [str(_ir(compiler, tmp_path, src))]
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    proc = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60,
                          check=False)
    return proc.returncode, proc.stdout, proc.stderr


# A value-yielding match on a zeroed `W` field: W has no variant 0.
ZERO = """\
enum W: i32
    Neg = -1
    Big = 1024

struct Box
    w: W

fn pick(b: *Box) -> i32
    match (*b).w
        Neg => 1
        Big => 2

fn main() -> i32
    var raw: i64 = 0
    let b: *Box = @raw as *Box
    pick(b) + 40
"""

# A statement match (each arm a call, no value) on -7, a negative value.
NEG = """\
enum W: i32
    Neg = -1
    Big = 1024

var HIT: i32 = 0

fn note(n: i32)
    HIT = n

fn main() -> i32
    var raw: i64 = 0xFFFFFFF9
    let w: *W = @raw as *W
    match *w
        Neg => note(1)
        Big => note(2)
    42
"""

# An unsigned repr: 200 prints as 200, not -56.
UNSIGNED = """\
enum Op: u8
    Read = 1
    Write = 2

fn code(o: Op) -> i32
    match o
        Read => 10
        Write => 20

fn main() -> i32
    var raw: u64 = 200
    let o: *Op = @raw as *Op
    code(*o)
"""

TRAPS = {
    "zero": (ZERO, "t.ritz:9:5: match on W: value 0 names no variant\n"),
    "negative": (NEG, "t.ritz:13:5: match on W: value -7 names no variant\n"),
    "unsigned": (UNSIGNED, "t.ritz:6:5: match on Op: value 200 names no variant\n"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(TRAPS))
def test_exhaustive_match_traps_on_no_variant(compiler, case, tmp_path):
    src, message = TRAPS[case]
    code, out, err = _run_full(compiler, tmp_path, src)
    assert (code, out, err) == (1, "", message), f"{compiler}: {case}"


# No trap: a `_` arm and a binding arm take the value; a valid value takes
# its own arm through an exhaustive match.
NO_TRAP = """\
enum W: i32
    Neg = -1
    Big = 1024

fn under(w: W) -> i32
    match w
        Neg => 1
        _ => 7

fn bound(w: W) -> i32
    match w
        Neg => 1
        other => 100

fn exact(w: W) -> i32
    match w
        Neg => 3
        Big => 4

fn main() -> i32
    var raw: i64 = 0
    let w: *W = @raw as *W
    if under(*w) != 7
        return 1
    if bound(*w) != 100
        return 2
    *w = W.Big
    if exact(*w) != 4
        return 3
    if exact(W.Neg) != 3
        return 4
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_catch_all_and_valid_values_do_not_trap(compiler, tmp_path):
    assert _run_full(compiler, tmp_path, NO_TRAP) == (42, "", "")


def test_freestanding_trap_calls_the_platform_hook(tmp_path):
    """A kernel has no exit syscall (#4119): ritz0's freestanding trap stops
    through `ritz_platform_fatal`, and its IR holds no syscall."""
    path = tmp_path / "kernel.ritz"
    path.write_text("enum W: i32\n    Neg = -1\n    Big = 1024\n\n"
                    "pub fn kpick(w: W) -> i32\n    match w\n"
                    "        Neg => 1\n        Big => 2\n")
    out = tmp_path / "kernel.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(path), "-o", str(out), "--no-runtime",
                      "--target", "x86_64-none-elf"],
                     cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0 and out.exists(), comp.stdout + comp.stderr
    ir = out.read_text()
    assert "syscall" not in ir, "a freestanding trap issued a syscall"
    assert "call void @\"ritz_platform_fatal\"" in ir, ir
    assert "__ritz_match_trap" in ir, ir
