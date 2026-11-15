"""AGAST #1694: ritz0 sizes a plain "..." literal by its UTF-8 bytes.

THE BUG

ritz0 took a literal's length with Python ``len(str)``, which counts code
points.  Each non-ASCII character then dropped one byte per extra byte from
the END of the literal: ``"Dµs".len`` was 3 (ritz1: 4), ``prints("Aµs|")``
printed ``Aµs`` and ``print("C{x}µs|")`` printed ``C7µs``.  A const StrView
or const ``[N]StrView`` element with a non-ASCII character did not even
assemble: its backing array was declared with the code-point count but
filled with the bytes.

THE FIX

Every place ritz0 sizes literal text counts ``value.encode('utf-8')``:
StrView literals, a String let's ``string_from_bytes`` length, print/eprint
interpolation segments, const StrView globals and const StrView array
elements.  ``c"..."`` literals were already right (the backing global is
built from the bytes, and nothing reads a length).

ORACLE

One row per sizing site, so breaking one site turns only its own row red.
Each literal ends with a 4-byte character (the widest loss), and the program
prints it followed by ``|``: a short ``len`` drops the bytes before the bar.  ritz1 runs the
rows it accepts; it refuses ``var s: String = "..."``, so that row is
ritz0-only.  It reads a const ``[N]StrView`` element since #3325.  The 2-, 3- and
4-byte cases on all three compilers live in the matrix file
``ritz0/test/test_utf8_literal_len.ritz``.
"""

import pytest

from test_eprint_interpolation import _compile, _run

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("ritz1_bin")]

BOTH = ("ritz0", "ritz1")
RITZ0 = ("ritz0",)

# name -> (compilers, program, expected stdout)
CASES = {
    "strview_let": (
        BOTH,
        """\
pub fn main() -> i32
    let v: StrView = "D😀"
    print("{v}|")
    0
""",
        "D😀|",
    ),
    "print_segment": (
        BOTH,
        """\
pub fn main() -> i32
    let x: i32 = 7
    print("C{x}😀")
    0
""",
        "C7😀",
    ),
    "const_strview": (
        BOTH,
        """\
const K: StrView = "K😀"

pub fn main() -> i32
    let k: StrView = K
    print("{k}|")
    0
""",
        "K😀|",
    ),
    # #3325: ritz1 emitted each "..." element as `%StrView zeroinitializer`
    # and refused `KS[1]` as a whole array.
    "const_strview_array": (
        BOTH,
        """\
const KS: [2]StrView = ["a", "c😀"]

pub fn main() -> i32
    let k: StrView = KS[1]
    print("{k}|")
    0
""",
        "c😀|",
    ),
    # A field of an element, at a runtime index: ritz1's member path had no
    # const arm ("unhandled EXPR_MEMBER").  "c😀" is 5 bytes.
    "const_strview_array_field": (
        BOTH,
        """\
const KS: [2]StrView = ["a", "c😀"]

pub fn main() -> i32
    var i: i64 = 1
    let n: i64 = KS[i].len
    print("{n}|")
    0
""",
        "5|",
    ),
    # The two names ritz0's String-let lowering needs, without ritzlib.
    "string_let": (
        RITZ0,
        """\
struct String
    ptr: *u8
    len: i64

fn string_from_bytes(p: *u8, n: i64) -> String
    String { ptr: p, len: n }

pub fn main() -> i32
    var s: String = "S😀"
    let n: i64 = s.len
    print("{n}|")
    0
""",
        "5|",
    ),
}

ROWS = [(name, c) for name, (cs, _, _) in CASES.items() for c in cs]


@pytest.mark.parametrize("name,compiler", ROWS, ids=[f"{n}-{c}" for n, c in ROWS])
def test_literal_sized_by_utf8_bytes(tmp_path, name, compiler):
    _, program, want = CASES[name]
    out, err = _run(compiler, tmp_path, name, program)
    assert out == want.encode("utf-8"), f"{compiler} {name}: {out!r}"
    assert err == b""


# A non-ASCII char literal is more than one byte, so it is not a u8: ritz0
# used to emit ord() of it ('€' became an out-of-range i8 8364).  Both
# compilers refuse it.  One row per width beyond ASCII would only re-test the
# same `> 0x7F` check, so '€' (3 bytes) stands for all of them.
CHAR_PROGRAM = "pub fn main() -> i32\n    let c: u8 = '€'\n    c as i32\n"


@pytest.mark.parametrize("compiler", BOTH)
def test_non_ascii_char_literal_refused(tmp_path, compiler):
    proc, _ = _compile(compiler, tmp_path, "char", CHAR_PROGRAM)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted '€' as a u8:\n{out[-1500:]}"
    assert f"char_{compiler}.ritz:2:" in out, out[-1500:]
    if compiler == "ritz0":
        assert "'€' is 3 bytes in UTF-8" in out, out[-1500:]
