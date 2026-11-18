"""The typing pass sees a field through `Deref` (LANGUAGE_SPEC §7.7, AGAST #3598).

`b.x` on a struct with no field `x` that implements `Deref` is its target's
`x`, read or written in place (ritzlib's `Box<T>`). The typing pass looked `x`
up on the struct itself and reported "struct 'Box' has no field 'x'" for every
such use in test/test_level32.ritz. The rule-5 errors (no `Deref`, neither has
the field, a write through only `Deref`) are the emitter's (deref_rules.py).

Parse-only: one TypeChecker per row, no compile.
"""

from parser import parse
from type_checker import TypeChecker


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


# A Box<T>-shaped generic whose impl names its parameter `U`, not the struct's
# `T`: the target is substituted through the impl's own parameter names.
WRAP = """
struct Point
    x: i32
    y: i32

struct Trio
    a: [3]i32
    q: Point

struct W<T>
    ptr: *T

impl<U> Deref for W<U>
    fn deref(self: @W<U>) -> @U
        @*self.ptr

impl<U> DerefMut for W<U>
    fn deref_mut(self: @&W<U>) -> @&U
        @&*self.ptr

"""

# A non-generic Deref struct.
HOLD = WRAP + """
struct Hold
    p: *Point

impl Deref for Hold
    fn deref(self: @Hold) -> @Point
        @*self.p

"""


def fn(body: str, params: str = "w: @&W<Point>, t: @&W<Trio>") -> str:
    return f"fn f({params}) -> i32\n" + "".join(f"    {s}\n" for s in body.split(";")) + "    0\n"


class TestFieldThroughDeref:
    def test_read(self):
        assert types(WRAP + fn("let v: i32 = w.x")) == []

    def test_read_has_the_targets_field_type(self):
        # The substituted target's `i32`, not an opaque `U` accepting anything.
        errs = types(WRAP + fn("let v: *u8 = w.x"))
        assert errs and "no field" not in errs[0], errs

    def test_write_and_compound_assign(self):
        assert types(WRAP + fn("w.x = 5;w.y += 3")) == []

    def test_nested_field_and_element(self):
        assert types(WRAP + fn("t.a[1] = 7;let v: i32 = t.q.x + t.a[0]")) == []

    def test_non_generic_deref(self):
        assert types(HOLD + fn("let v: i32 = h.y", "h: @Hold")) == []

    def test_through_two_derefs(self):
        assert types(WRAP + fn("ww.x = 1;let v: i32 = ww.y", "ww: @&W<W<Point>>")) == []

    def test_own_field_comes_first(self):
        errs = types(WRAP + fn("let v: i32 = w.ptr"))
        assert errs and "no field" not in errs[0], errs


class TestStillRefused:
    def test_no_deref(self):
        src = WRAP + "struct S\n    p: *Point\n\n" + fn("let v: i32 = s.x", "s: @S")
        assert any("struct 'S' has no field 'x'" in e for e in types(src))

    def test_inherent_deref_method_is_not_deref(self):
        src = WRAP + ("struct S\n    p: *Point\n\nimpl S\n    fn deref(self: @S) -> @Point\n"
                      "        @*self.p\n\n") + fn("let v: i32 = s.x", "s: @S")
        assert any("struct 'S' has no field 'x'" in e for e in types(src))

    def test_target_lacks_the_field(self):
        assert any("has no field 'z'" in e for e in types(WRAP + fn("let v: i32 = w.z")))
