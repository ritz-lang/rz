"""AGAST #2102: `{expr}` interpolates only inside print/eprint, in both compilers.

THE DEFECT

ritz0's lexer turned EVERY "..." holding a matched `{...}` into an
interpolated string. ritz1 keeps such a literal's braces as plain bytes
everywhere except where the print / eprint builtin reads it (interp.ritz,
#1374/#1521). Same source, different result:

    let s: StrView = "{a}"      # ritz0: "Interpolated strings cannot be used
                                #         as values"   ritz1: len 3
    "bare{a}\\n"                 # ritz0: prints `bare7` ritz1: no output

THE RULE (normative: ritz1's)

A "..." literal is plain bytes. Its placeholders are split and evaluated only
when it is the argument of print / eprint. #1913 fixed the `{{` / `}}` half
of the same rule (test_brace_escape_scope.py).

ORACLE

Each program is compiled by ritz0 and by ritz1; both binaries must print
byte-identical stdout AND stderr, which are also pinned to literal expected
bytes so a bug both compilers share cannot pass.
"""

import subprocess

import pytest

import fast_link

from test_ritz1_builtin_struct_shadow import RITZ_START
from test_ritz1_print_interpolation import _compile

pytestmark = [pytest.mark.usefixtures("ritz1_bin"), pytest.mark.integration]


def _run(compiler, tmp_path, name, program):
    """Compile, link, run; return (stdout, stderr). Asserts each step succeeds."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR would not link:\n{link.stderr[-2000:]}"
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 0, f"{compiler} binary for {name} exited {run.returncode}"
    return run.stdout, run.stderr


def _assert_parity(tmp_path, name, program, out, err=b""):
    got0 = _run("ritz0", tmp_path, name, program)
    got1 = _run("ritz1", tmp_path, name, program)
    assert got0 == (out, err), f"ritz0 oracle drifted for {name}: {got0!r}"
    assert got1 == (out, err), f"ritz1 gave {got1!r}, ritz0 gave {got0!r}"


# Shared helpers. A local `prints` / `len`: the harness links one module,
# without ritzlib.
PRELUDE = """\
fn prints(s: StrView)
    syscall3(1, 1, s.ptr as i64, s.len)
    let bar: StrView = "|"
    syscall3(1, 1, bar.ptr as i64, bar.len)

fn len(s: StrView) -> i64
    return s.len

struct Box
    s: StrView

fn ret() -> StrView
    return "<{b}>"

"""


# The ticket's repro, and every value position the brief names.
VALUES = PRELUDE + """\
pub fn main() -> i32
    let a: i64 = 7
    let s: StrView = "{a}"
    prints(s)
    # Un-annotated locals are checked by length only: ritz1 cannot yet pass
    # one to a StrView param (AGAST #2103, unrelated to braces).
    let t = "x{a}y"
    var u: StrView = "{a}{a}"
    prints(u)
    var w = "{ a }"
    prints("arg{a}")
    prints(ret())
    let bx: Box = Box { s: "{f}" }
    prints(bx.s)
    let n: i64 = len("{a}")
    let sn: i64 = s.len
    let tn: i64 = t.len
    let un: i64 = u.len
    let wn: i64 = w.len
    print("\\nn={n} s={sn} t={tn} u={un} w={wn}\\n")
    return 0
"""


def test_placeholder_braces_are_plain_outside_print(tmp_path):
    _assert_parity(
        tmp_path,
        "values",
        VALUES,
        b"{a}|{a}{a}|arg{a}|<{b}>|{f}|\nn=3 s=3 t=5 u=6 w=5\n",
    )


# `{x}` next to `{{` / `}}`: outside print every byte stays; inside print the
# pairs collapse and the placeholder is evaluated. `\\{` is a literal brace
# in both places.
MIXED = PRELUDE + """\
pub fn main() -> i32
    let a: i64 = 7
    let s: StrView = "{{{a}}}"
    prints(s)
    prints("{{a}} {a}")
    prints("\\{a}")
    let n: i64 = s.len
    print("\\nlen={n}\\n")
    print("{{{a}}} {{a}} \\{a} a={a}\\n")
    return 0
"""


def test_placeholder_mixed_with_brace_escapes(tmp_path):
    _assert_parity(
        tmp_path,
        "mixed",
        MIXED,
        b"{{{a}}}|{{a}} {a}|{a}|\nlen=7\n{7} {a} {a} a=7\n",
    )


# print / eprint still interpolate, to their own fds.
PRINTS = """\
pub fn main() -> i32
    let a: i64 = 7
    let b: bool = true
    print("a={a} b={b} sum={a + 1}\\n")
    eprint("e={a}\\n")
    return 0
"""


def test_print_and_eprint_still_interpolate(tmp_path):
    _assert_parity(tmp_path, "prints", PRINTS, b"a=7 b=true sum=8\n", b"e=7\n")


# A bare literal statement is a value nobody uses: ritz1 prints nothing, so
# ritz0 must not silently desugar it into a print.
BARE = """\
pub fn main() -> i32
    let a: i64 = 7
    "bare{a}\\n"
    "plain\\n"
    print("done\\n")
    return 0
"""


def test_bare_placeholder_statement_prints_nothing(tmp_path):
    _assert_parity(tmp_path, "bare", BARE, b"done\n")
