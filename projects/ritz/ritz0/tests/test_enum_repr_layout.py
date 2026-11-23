"""AGAST #4574: an `enum E: <int>` stores its discriminant in its repr type.

LANGUAGE_SPEC §10.1: a fieldless enum with a representation type is laid
out as that integer type and holds the variant's *discriminant*, so
sizeof(E) == sizeof(repr), a struct field of type E has the repr's size and
alignment, and zeroed memory reads as discriminant 0.  An enum without one
keeps its compact one-byte tag holding the declaration index.

Each program views the same bytes as an enum-holding struct and as plain
integers, so a compiler that stores the index (or an i8) fails with a code
naming the first check that saw it.  The cross-module case pins that an
importer lays out an imported repr enum the way its own module does.
"""

import pytest

from test_enum_discriminants import COMPILERS, _run

pytestmark = pytest.mark.integration

LAYOUT = """\
enum W: i32
    Neg = -1
    Zero = 0
    Big = 1024
    Over = 9001

enum Tiny: u8
    Seven = 7
    Eight

enum Wide: i64
    Low = -5
    High = 0x100000000

enum Plain
    A
    B

struct Box
    w: W
    b: u8

struct Late
    b: u8
    w: W

struct Raw
    a: u64
    b: u64

var G: W = W.Neg
var GP: *W

fn main() -> i32
    if G as i64 != -1                 # a global's initialiser
        return 25
    var gb: *Box = @G as *Box
    if (*gb).w != W.Neg
        return 26
    if sizeof(W) != 4
        return 1
    if sizeof(Tiny) != 1
        return 2
    if sizeof(Wide) != 8
        return 3
    if sizeof(Plain) != 1
        return 4
    if sizeof(Box) != 8
        return 5
    if sizeof(Late) != 8
        return 6

    # Zeroed memory is discriminant 0.
    var raw = Raw { a: 0, b: 0 }
    let bx: *Box = @raw as *Box
    if (*bx).w as i32 != 0
        return 7
    if (*bx).w != W.Zero
        return 8
    let z: i32 = match (*bx).w
        Zero => 0
        _ => 1
    if z != 0
        return 9
    let t: *Tiny = @raw as *Tiny
    if (*t) as u8 != 0
        return 10

    # Writes store the discriminant, in the repr's width.
    (*bx).w = W.Neg
    if raw.a != 0xFFFFFFFF
        return 11
    if (*bx).w as i64 != -1           # a signed repr sign-extends
        return 24
    (*bx).w = W.Big
    if raw.a != 1024
        return 12
    *t = Tiny.Seven
    if raw.a != 1031                  # 1024 with its low byte 7
        return 13

    # Reads see the discriminant written as an integer.
    raw.a = 9001
    if (*bx).w != W.Over
        return 14
    let o: i32 = match (*bx).w
        Over => 9001
        _ => 0
    if o != 9001
        return 15

    # A value that is no variant's discriminant: `as` and `==` see it, and
    # a `_` arm takes it (§10.1).
    raw.a = 5
    if (*bx).w as i32 != 5
        return 21
    if (*bx).w == W.Zero or (*bx).w == W.Neg
        return 22
    let none: i32 = match (*bx).w
        Neg => 1
        Zero => 2
        _ => 0
    if none != 0
        return 23

    # A unit variant built by a call, `E.V()` / `V()`.
    let called: W = W.Big()
    if called as i32 != 1024
        return 27
    let bare: W = Over()
    if bare as i32 != 9001
        return 28

    # A repr enum field sits at the repr's alignment.
    raw.a = 0
    let late: *Late = @raw as *Late
    (*late).w = W.Big
    if raw.a != 1024 << 32
        return 16

    # A `*W` global steps sizeof(W) bytes, indexed or by arithmetic.
    raw.a = 0
    GP = @raw as *W
    *(GP + 1) = W.Big
    if raw.a != 1024 << 32
        return 29
    if GP[1] as i32 != 1024
        return 30

    let wd: *Wide = @raw as *Wide
    *wd = Wide.High
    if raw.a != 0x100000000
        return 17
    *wd = Wide.Low
    if (raw.a as i64) != -5
        return 18
    if (*wd) as i64 != -5
        return 19

    # An enum without a representation type keeps its index tag.
    raw.a = 0
    let p: *Plain = @raw as *Plain
    *p = Plain.B
    if raw.a != 1
        return 20
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_repr_layout(compiler, tmp_path):
    assert _run(compiler, tmp_path, LAYOUT) == 42


COLORS = """\
pub enum Hue: i32
    Neg = -1
    Zero = 0
    Big = 1024

pub fn put_big(p: *Hue)
    *p = Hue.Big

pub fn is_neg(h: Hue) -> i32
    match h
        Neg => 1
        _ => 0
"""

CROSS = """\
import colors { Hue, put_big, is_neg }

fn main() -> i32
    var n: i64 = -1
    let h: *Hue = @n as *Hue
    if sizeof(Hue) != 4
        return 1
    if is_neg(*h) != 1
        return 2
    put_big(h)
    if (n & 0xFFFFFFFF) != 1024
        return 3
    if (*h) as i32 != 1024
        return 4
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_repr_layout_across_modules(compiler, tmp_path):
    assert _run(compiler, tmp_path, CROSS, {"colors": COLORS}) == 42
