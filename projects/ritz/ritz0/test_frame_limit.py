"""AGAST #3738: ritz0 refuses a fn whose stack frame exceeds the stack.

THE DEFECT

lexis's `main` held several big fixed-array aggregates by value (a
`[4096]CssRule` stylesheet, its selector map, by-value-return temporaries)
and compiled to `movabs $0x2fbfb5da80,%rax; sub %rax,%rsp`: a ~205 GB frame.
Nothing complained; the binary SIGSEGV'd on its first call (#3700).

THE RULE

A fn's frame is the sum of its allocas' sizes: its locals, its by-value
params' copies and its by-value temporaries (an sret slot, a lent copy).
When that sum exceeds FRAME_LIMIT_BYTES (8 MiB, the default `ulimit -s`),
ritz0 refuses the fn, located at the largest local or temporary and naming
its size, the fn and the frame's total.  A frame of exactly the limit is
accepted.  There is no opt-out attribute: a deliberately big frame goes on
the heap or in a static.  ritz1 refuses with the same rule and words (#3739).

Each row compiles once per compiler (ritz0, ritz1, ritz1_selfhosted; no
link), so the matrix is one row per rule: a single local, a sum of locals
(largest is not the first), a temporary, and the boundary.
"""

import re
from pathlib import Path

import pytest
from test_ref_into_value import COMPILERS, _emit

pytestmark = [pytest.mark.integration, pytest.mark.parametrize("compiler", COMPILERS)]

MIB = 1024 * 1024


def _compile(compiler: str, tmp_path: Path, src: str):
    path = tmp_path / "t.ritz"
    path.write_text(src)
    proc = _emit(compiler, path, tmp_path / "t.ll", tmp_path)
    return proc, proc.stdout + proc.stderr


def _refused(compiler: str, tmp_path: Path, src: str, line: int, col: int, size: int, fn: str):
    proc, out = _compile(compiler, tmp_path, src)
    assert proc.returncode != 0, out
    assert f"t.ritz:{line}:{col}:" in out, out
    assert f"`{fn}`" in out, out
    assert f"{size} bytes" in out, out
    assert "Traceback" not in out, out
    return out


def test_local_over_limit_is_refused_at_the_local(compiler, tmp_path):
    out = _refused(compiler, tmp_path, """\
struct Rule
    a: [1024]u8

fn fill(r: *Rule) -> i32
    r.a[0] = 1
    0

pub fn main(args: Span<StrView>) -> i32
    var small: [16]u8 = [0; 16]
    var rules: [16384]Rule
    fill(@&rules[0])
    0
""", line=10, col=5, size=16 * MIB, fn="main")
    # An adapted main (#200) is still named `main`, not `__ritz_main` (#4018).
    # The whole message, ritz0's words on every compiler (the total depends
    # on each compiler's own temporaries, so it is matched by shape).
    assert re.search(
        r"t\.ritz:10:5: (?:error: )?fn `main` needs a \d+ bytes \(16\.0 MiB\) stack "
        r"frame, over the 8388608 bytes \(8 MiB\) stack; `rules` here takes "
        r"16777216 bytes \(16 MiB\): put it on the heap or in a static$", out, re.M), out


def test_locals_that_sum_over_limit_point_at_the_largest(compiler, tmp_path):
    # Each local alone fits; together they don't.  The larger one is
    # declared second, so "first alloca" would point at the wrong line.
    _refused(compiler, tmp_path, """\
fn touch(p: *u8) -> i32
    p[0] = 1
    0

fn main() -> i32
    var a: [4194304]u8
    var b: [5242880]u8
    touch(@&a[0])
    touch(@&b[0])
    0
""", line=7, col=5, size=5 * MIB, fn="main")


def test_by_value_temporary_over_limit_is_refused_at_the_expr(compiler, tmp_path):
    # `make()` returns a 9 MB struct through an sret slot in main's frame;
    # main itself declares no big local.
    out = _refused(compiler, tmp_path, """\
struct Big
    a: [9000000]u8

fn first(b: @Big) -> u8
    b.a[0]

fn main() -> i32
    let n = first(@make())
    n as i32

fn make() -> Big
    var b: Big
    b.a[0] = 7
    b
""", line=8, col=20, size=9000000, fn="main")
    assert "by-value temporary" in out, out


def test_frame_of_exactly_the_limit_compiles(compiler, tmp_path):
    proc, out = _compile(compiler, tmp_path, """\
fn touch(p: *u8) -> i32
    p[0] = 1
    0

fn main() -> i32
    var a: [8388608]u8
    touch(@&a[0])
""")
    assert proc.returncode == 0, out
