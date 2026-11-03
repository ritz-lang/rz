"""AGAST #1913: `{{` / `}}` collapse only inside print/eprint, in both compilers.

THE DEFECT

ritz0's lexer turned `{{` into `{` and `}}` into `}` in EVERY plain "..."
literal at lex time. ritz1 does it only where the print / eprint builtin reads
the literal (interp.ritz, #1374/#1521). Same source, different bytes:

    let s: StrView = "x{{y"     # ritz0: len 3   ritz1: len 4
    prints("{{\\n")              # ritz0: `{`     ritz1: `{{`

ritzunit's JSON reporter hit this (#1908): under ritz1 its report came out as
`{{ ... }}` and the harness could not parse it.

THE RULE (normative: ritz1's, and LANGUAGE_SPEC section 2's)

`{{` / `}}` are a brace escape of print interpolation, not of the string
literal. A "..." used anywhere else keeps them as two bytes. ritz1's inline
asm constraints (`"={rax},{rax}"`) depend on literals keeping their braces.

ORACLE

Each program is compiled by ritz0 and by ritz1; both binaries must print
byte-identical stdout, which is also pinned to a literal expected string so a
bug both compilers share cannot pass.
"""

import pytest

from test_ritz1_print_interpolation import _assert_parity

pytestmark = [pytest.mark.usefixtures("ritz1_bin"), pytest.mark.integration]


# The ticket's two repros: a literal's length and prints' bytes.
OUTSIDE_PRINT = """\
# A local prints: the parity harness links one module, without ritzlib.
fn prints(s: StrView)
    syscall3(1, 1, s.ptr as i64, s.len)

pub fn main() -> i32
    let s: StrView = "x{{y"
    let n: i64 = s.len
    print("len={n}\\n")
    let t: StrView = "a}}b}}"
    let m: i64 = t.len
    print("len={m}\\n")
    prints("{{\\n")
    prints("}}\\n")
    prints("{{x}}\\n")
    return 0
"""


def test_braces_kept_outside_print(tmp_path):
    _assert_parity(
        tmp_path,
        "outside",
        OUTSIDE_PRINT,
        b"len=4\nlen=6\n{{\n}}\n{{x}}\n",
    )


# Inside print / eprint the escape still means one brace.
INSIDE_PRINT = """\
pub fn main() -> i32
    let x: i64 = 5
    print("{{\\n")
    print("a{{b}}c\\n")
    print("{{{x}}}\\n")
    eprint("{{e}}\\n")
    return 0
"""


def test_braces_collapse_inside_print(tmp_path):
    _assert_parity(tmp_path, "inside", INSIDE_PRINT, b"{\na{b}c\n{5}\n")


# `\\{` is one literal brace on its own, so `\\{{` is that brace and then a
# lone `{` -- two braces -- in print as well as out of it. A rule that
# collapsed the cooked text after the fact would print one.
ESCAPED_THEN_BRACE = """\
# A local prints: the parity harness links one module, without ritzlib.
fn prints(s: StrView)
    syscall3(1, 1, s.ptr as i64, s.len)

pub fn main() -> i32
    print("\\{{\\n")
    prints("\\{{\\n")
    print("\\}}}\\n")
    return 0
"""


def test_backslash_brace_then_brace(tmp_path):
    _assert_parity(tmp_path, "escbrace", ESCAPED_THEN_BRACE, b"{{\n{{\n}}\n")
