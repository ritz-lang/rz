"""AGAST #3597: the checkers know the built-in `Span<T>` with no import.

THE BUG

`Span<T>` is built in (#3346, R29): the emitter lowers `Span.empty()` from
the slot it lands in and builds `Span<u8> { ptr, len }` as `{ *u8, i64 }`,
import or not.  The checkers didn't know it:

    return Span.empty()               # --check-names: Unknown identifier: Span
                                      # --check-types: undefined variable: Span
    Span<u8> { ptr: @a[0], len: 3 }   # --check-types: undefined struct: Span

THE FIX

Both passes take `Span` as a type when it's a method call's receiver and no
local shadows it, as the emitter's `_builtin_type_receiver` does; the type
checker types a `Span<T> { .. }` literal with Span's fields `ptr: *T` and
`len: i64` (`_ensure_builtin_generic_struct_specialization`).  What the
emitter refuses stays refused: a bare `Span` as a value, and a `Span { .. }`
literal with no type argument.  A declared or imported `struct Span<T>`
(ritzlib.span) is the program's own and is checked as before.
"""

import pytest

from name_resolver import resolve_names
from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit


def names(source: str) -> list:
    return [str(e) for e in resolve_names(parse(source))]


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


# The ticket's repro, minus its import (a unit parse resolves none).
EMPTY = """\
fn empty() -> Span<u8>
    return Span.empty()

fn main() -> i32
    empty().len as i32
"""

# test_span_builtin_no_import.ritz:23,32: a literal in a let and as an arg.
LITERAL = """\
fn span_sum(s: Span<u8>) -> i64
    s.len

fn main() -> i32
    var a: [3]u8 = [1, 2, 3]
    let s: Span<u8> = Span<u8> { ptr: @a[0], len: 3 }
    let n: i64 = span_sum(Span<u8> { ptr: @a[1], len: 2 })
    (s.len + n) as i32
"""

# A bare `Span` is a type, not a value: the emitter has nothing to emit.
BARE_VALUE = """\
fn main() -> i32
    let x = Span
    0
"""


class TestNames:
    def test_span_receiver(self):
        assert names(EMPTY) == []

    def test_span_literal(self):
        assert names(LITERAL) == []

    def test_bare_span_value_is_unknown(self):
        assert any("Unknown identifier: Span" in e for e in names(BARE_VALUE))


class TestTypes:
    def test_span_receiver(self):
        assert types(EMPTY) == []

    def test_span_literal(self):
        assert types(LITERAL) == []

    def test_bare_span_value_is_undefined(self):
        assert any("undefined variable: Span" in e for e in types(BARE_VALUE))

    def test_local_named_span_is_a_value(self):
        # A local shadows the type: `Span.get()` is P_get, whose bool
        # doesn't fit an i64.  As the type, it would be the emitter's and
        # untyped, so no error.
        src = ("struct P\n    x: i32\n\n"
               "impl P\n    fn get(self: @P) -> bool\n        true\n\n"
               "fn f(Span: P) -> i64\n"
               "    let n: i64 = Span.get()\n"
               "    n\n")
        assert any("bool" in e for e in types(src)), types(src)

    def test_literal_fields_are_spans(self):
        src = ("fn main() -> i32\n"
               "    var a: [3]u8 = [1, 2, 3]\n"
               "    let s = Span<u8> { ptr: @a[0], size: 3 }\n"
               "    0\n")
        assert any("struct 'Span' has no field 'size'" in e for e in types(src))

    def test_literal_field_types_take_the_type_arg(self):
        # `ptr` is `*T` at the literal's own `T`, and `len` is an i64.
        src = ("fn main() -> i32\n"
               "    var a: [3]u8 = [1, 2, 3]\n"
               "    let s = Span<u16> { ptr: true, len: false }\n"
               "    0\n")
        errors = types(src)
        assert any("field 'ptr': expected *u16, got bool" in e for e in errors), errors
        assert any("field 'len': expected i64, got bool" in e for e in errors), errors

    def test_literal_ptr_of_another_type_is_refused(self):
        # A `@a[0]` of an i32 array doesn't fit a `Span<u8>`'s `*u8`.
        src = ("fn main() -> i32\n"
               "    var a: [3]i32 = [1, 2, 3]\n"
               "    let s = Span<u8> { ptr: @a[0], len: 3 }\n"
               "    0\n")
        assert any("reference to one type doesn't fit" in e for e in types(src))

    def test_literal_without_type_arg_is_undefined(self):
        # The emitter builds Span's struct from its type argument.
        src = ("fn main() -> i32\n"
               "    var a: [3]u8 = [1, 2, 3]\n"
               "    let s = Span { ptr: @a[0], len: 3 }\n"
               "    0\n")
        assert any("undefined struct: Span" in e for e in types(src))

    def test_declared_span_is_the_programs_own(self):
        # ritzlib.span's shape, with a field the built-in lacks.
        src = ("struct Span<T>\n"
               "    ptr: *T\n"
               "    len: i64\n"
               "    cap: i64\n\n"
               "fn main() -> i32\n"
               "    var a: [3]u8 = [1, 2, 3]\n"
               "    let s = Span<u8> { ptr: @a[0], len: 3, cap: 3 }\n"
               "    0\n")
        assert types(src) == []
