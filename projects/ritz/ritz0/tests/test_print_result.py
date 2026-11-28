"""AGAST #4962: the print builtins return `Result<(), Errno>`, not a byte sum.

THE GAP

`write(w, "...{x}...")` / `writeln`, `print` / `eprint` and the interpolated
`println` / `eprintln` lowered to the i64 sum of every piece's count, in both
compilers.  A failed piece's -errno was added into the total, so the error was
lost (a later piece's count could even make the sum positive), and every piece
after the failure was still written.  ritzlib's plain `write` / `writeln`
return `Result<(), Errno>` since AGAST #4930; the builtins now say the same
(LANGUAGE_SPEC §2.6).

THE RULE

Each piece is written in order; the first one that fails stops the call, and
its errno is the `Err`.  `Ok(())` means every byte was accepted.  The value is
ritzlib.errno's `errno_check` of the status, so it is the same type `?` and
`match` see on any syscall wrapper.

ORACLE

One package per compiler.  `main` returns how many checks failed and names
each on stderr; stdout is closed by the last check, so the earlier ones'
output goes to a span writer and stderr.
"""

import subprocess

import pytest

from test_format_into import _build

pytestmark = [pytest.mark.integration]

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PROGRAM = """\
import ritzlib.errno
import ritzlib.fmt
import ritzlib.string
import ritzlib.sys

struct Point
    x: i64
    y: i64

impl Display for Point
    fn show(self: @Point, w: @&Writer) -> i64
        let start: i64 = w.len()
        match write(w, "({self.x}, {self.y})")
            Ok(_) => w.len() - start
            Err(e) => -(e.code() as i64)

fn fail(what: StrView) -> i32
    eprintln("FAIL {what}")
    1

# `?` takes the builtin's Result like any other.
fn both(w: @&Writer, p: @Point) -> Result<(), Errno>
    writeln(w, "p={p}")?
    write(w, "x={p.x}")?
    Ok(())

# print's value through `?`, with a placeholder and without.
fn shout(n: i64) -> Result<(), Errno>
    print("{n}")?
    print("!\\n")?
    Ok(())

# The errno of `r`, or 0 for Ok.
fn code_of(r: Result<(), Errno>) -> i32
    match r
        Ok(_) => 0
        Err(e) => e.code()

pub fn main() -> i32
    var bad: i32 = 0
    let p: Point = Point { x: 3, y: 4 }

    # Ok: every byte, through a String writer and `?`.
    var s: String = string_new()
    var sw: Writer = string_writer(@&s)
    if code_of(both(@&sw, @p)) != 0 or not s.as_view().eq("p=(3, 4)\\nx=3")
        bad += fail("ok")
    if code_of(shout(7)) != 0
        bad += fail("print ?")

    # The first failing piece stops the call: "ab" + "123" fill 5 of 6
    # bytes, "cdef" is NoSpc, and the 1-byte "{x}" after it, which would
    # fit, is never written.
    var buf: [6]u8
    var w: Writer = span_writer(Span<u8> { ptr: @buf[0] as *u8, len: 6 })
    let n: i64 = 123
    let x: i64 = 7
    if code_of(write(@&w, "ab{n}cdef{x}")) != 28
        bad += fail("stop: not NoSpc")
    if w.len() != 5
        bad += fail("stop: wrote past the failure")

    # A Display impl's error is the call's: show's own write puts "(3"
    # down and then is NoSpc, and writeln's newline after it isn't written.
    var small: [3]u8
    var w2: Writer = span_writer(Span<u8> { ptr: @small[0] as *u8, len: 3 })
    if code_of(writeln(@&w2, "{p}")) != 28
        bad += fail("display: not NoSpc")
    if not w2.view().eq("(3")
        bad += fail("display: wrote after the failure")

    # print / println to a closed stdout: EBADF, whether or not the literal
    # holds a placeholder; eprint still reaches stderr.
    if sys_close(1) < 0
        bad += fail("close")
    if code_of(print("n={n}\\n")) != 9
        bad += fail("print: not BadF")
    if code_of(print("plain\\n")) != 9
        bad += fail("plain print: not BadF")
    if code_of(println("n={n}")) != 9
        bad += fail("println: not BadF")
    if code_of(eprint("e={n}\\n")) != 0
        bad += fail("eprint")
    bad
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_print_builtins_return_a_result(tmp_path, compiler):
    proc, exe = _build(compiler, tmp_path, "print_result", PROGRAM)
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
    run = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)
    assert run.stdout == b"7!\n", f"{compiler}: {run.stdout!r}"
    assert run.stderr == b"e=123\n", f"{compiler}: {run.stderr!r}"
    assert run.returncode == 0, f"{compiler}: {run.returncode} check(s) failed"
