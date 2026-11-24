#!/usr/bin/env python3
"""An emitter user error is located, not a Python traceback (AGAST #1390).

ritz0's emitter had 147 bare ValueError raise sites on main (185 when
filed). Most described the *user's* mistake, an unknown variant, a builtin's
arity, `?` in a function that can't return it, and each reached the user as
an eleven-frame traceback naming no file:

    Compiler error: Unknown variant C in enum E
    Traceback (most recent call last):
      ...
    ValueError: Unknown variant C in enum E

Now:

    Compiler error: main.ritz:5:13: Unknown variant C in enum E

The sites were triaged, not caught wholesale: 129 user errors raise
`self._err(msg)` (a `SourceError`, located at the innermost expression being
emitted), one static helper raises `SourceError` at its field, and 17
internal invariants raise `InternalError`, which still prints a traceback.
`_emit_call` and `_emit_stmt` keep their narrow-key except clauses (#1366,
#1384); nothing new catches ValueError.

Each row is one class of site and its control: the refused program with `^`
where the error is, the message, and the corrected program, which must
still compile. Without the controls, "raise an error everywhere" would pass.
"""

import os
import re
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_ref_into_value import COMPILERS, _compile as _compile3
from test_table_rows import assert_refusals


RITZ_ROOT = Path(__file__).resolve().parents[2]

LOCATED = re.compile(r"main\.ritz:\d+:\d+: ")


def _compile(tmp_path, src):
    (tmp_path / "main.ritz").write_text(src)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0(["main.ritz", "-o", str(tmp_path / "main.ll"), "--no-runtime"],
                     cwd=tmp_path, env=env, timeout=300)


def _located(marked):
    """`marked` without its `^`, and where the `^` was as `line:col`."""
    before = marked[:marked.index("^")]
    return (marked.replace("^", "", 1),
            f"{before.count(chr(10)) + 1}:{len(before) - before.rfind(chr(10))}")


MAIN0 = "\nfn main() -> i32\n    0\n"
GEN = "fn id<T>(x: T) -> T\n    x\n\nfn ap(f: fn(i32) -> i32) -> i32\n    f(3)\n\n"
GENERIC_FN_VALUE = "`id` is generic, so it can't be used as a value: call it"

# row -> (refused program with `^`, message, corrected program)
ROWS = {
    # A field on a scalar.  The checker's _refuse_primitive_member (#4155)
    # refuses it before _emit_field_access's raise is reached.
    "field_on_scalar": ("""\
fn main() -> i32
    let a: i64 = 5
    let b = ^a.x
    0
""", "`a` has type `i64`, which is not a struct: it has no field `x`", """\
struct P
    x: i64

fn main() -> i32
    let a = P { x: 5 }
    let b = a.x
    0
"""),
    # A tuple index on a scalar: refused by the checker too (#4155).
    "tuple_field_on_scalar": ("""\
fn main() -> i32
    let a: i64 = 1
    let b = ^a.0
    0
""", "`a` has type `i64`, which is not a struct: it has no field `0`", """\
fn main() -> i32
    let a = (1, 2)
    let b = a.0
    0
"""),
    # A field store whose target isn't a struct: refused by the checker
    # (#4155) before _emit_stmt_inner's raise.
    "field_assign_on_scalar": ("""\
fn main() -> i32
    var a: i64 = 1
    ^a.x = 2
    0
""", "`a` has type `i64`, which is not a struct: it has no field `x`", """\
struct P
    x: i64

fn main() -> i32
    var a = P { x: 1 }
    a.x = 2
    0
"""),
    # _emit_stmt_inner: `let (a, b)` of a 3-tuple.
    "tuple_destructure_count": ("""\
fn main() -> i32
    let t = (1, 2, 3)
    ^let (a, b) = t
    0
""", "Tuple destructuring mismatch: expected 3 elements, got 2 names", """\
fn main() -> i32
    let t = (1, 2, 3)
    let (a, b, c) = t
    0
"""),
    # _try_emit_bitops_intrinsic: a bit operation's arity.
    "bitop_arity": ("""\
fn main() -> i32
    let a: u32 = 5
    let b = ^a.rotl()
    0
""", "rotl() requires exactly 1 argument", """\
fn main() -> i32
    let a: u32 = 5
    let b = a.rotl(1)
    0
"""),
    # _try_emit_strview_builtin: StrView.as_bytes() arity.
    "strview_builtin_arity": ("""\
fn main() -> i32
    let s = "hi"
    let b = ^s.as_bytes(1)
    0
""", "as_bytes() takes no arguments", """\
fn main() -> i32
    let s = "hi"
    let b = s.as_bytes()
    0
"""),
    # _try_emit_simd_builtin: a SIMD builtin's arity.
    "simd_builtin_arity": ("""\
fn f(a: v4i32) -> v4i32
    ^simd_add(a)
""" + MAIN0, "simd_add() requires 2 arguments (vector, vector)", """\
fn f(a: v4i32) -> v4i32
    simd_add(a, a)
""" + MAIN0),
    # _dispatch_method_call: no method of that name on a primitive. Located
    # at the method's name.
    "no_method": ("""\
fn main() -> i32
    let f: f64 = 2.0
    let g = f.^sqrt()
    0
""", "No method 'sqrt' found for type 'f64'", """\
fn main() -> i32
    let f: f64 = 2.0
    let g = f.floor()
    0
"""),
    # _try_emit_float_intrinsic: a float method's arity.
    "float_intrinsic_arity": ("""\
fn main() -> i32
    let f: f64 = 2.0
    let g = ^f.floor(1)
    0
""", "floor() takes no arguments", """\
fn main() -> i32
    let f: f64 = 2.0
    let g = f.floor()
    0
"""),
    # _dispatch_method_call: a receiver whose type nothing names.
    "method_on_untyped": ("""\
fn main() -> i32
    let b = ^(1, 2).foo()
    0
""", "Cannot call method 'foo' on unknown type", """\
struct P
    x: i64

impl P
    fn foo(self: @P) -> i64
        self.x

fn main() -> i32
    let b = P { x: 1 }.foo()
    0
"""),
    # _emit_try_op_option: `?` on an Option outside an Option fn.
    "try_option_outside_option_fn": ("""\
fn f() -> Option<i64>
    Some(1)

fn g() -> i64
    let x = ^f()?
    x
""" + MAIN0, "Try operator on an Option used in a function that does not return an Option (got None)", """\
fn f() -> Option<i64>
    Some(1)

fn g() -> Option<i64>
    let x = f()?
    Some(x)
""" + MAIN0),
    # _emit_try_op: `?` on a plain value.
    "try_on_plain_value": ("""\
fn f() -> i64
    5

fn g() -> Option<i64>
    let b = ^f()?
    Some(b)
""" + MAIN0, "Try operator requires a Result or an Option", """\
fn f() -> Option<i64>
    Some(5)

fn g() -> Option<i64>
    let b = f()?
    Some(b)
""" + MAIN0),
    # _get_enum_variant_tag: a variant the enum doesn't declare.
    "unknown_variant": ("""\
enum E
    A
    B

fn main() -> i32
    let e = ^E.C
    0
""", "Unknown variant C in enum E", """\
enum E
    A
    B

fn main() -> i32
    let e = E.B
    0
"""),
    # _struct_lit_field_indices (static): located at the field's value.
    "struct_lit_unknown_field": ("""\
struct P
    x: i64

fn main() -> i32
    let p = P { x: 1, y: ^2 }
    0
""", "`P` has no field `y`", """\
struct P
    x: i64
    y: i64

fn main() -> i32
    let p = P { x: 1, y: 2 }
    0
"""),
    # AGAST #4655: a generic instance's literal, and the built-in Span's.
    # ritz1 dropped the field and compiled each.
    "struct_lit_generic_unknown_field": ("""\
struct H<T>
    v: T

fn main() -> i32
    let h = H<u8> { v: 1, w: ^2 }
    0
""", "`H<u8>` has no field `w`", """\
struct H<T>
    v: T

fn main() -> i32
    let h = H<u8> { v: 1 }
    0
"""),
    "span_lit_unknown_field": ("""\
fn main() -> i32
    var a: [3]u8 = [1, 2, 3]
    let s = Span<u8> { ptr: @a[0], size: ^3 }
    0
""", "`Span<u8>` has no field `size`", """\
fn main() -> i32
    var a: [3]u8 = [1, 2, 3]
    let s = Span<u8> { ptr: @a[0], len: 3 }
    0
"""),
    # _emit_array_fill: `[0; 0]`.
    "array_fill_zero": ("""\
fn main() -> i32
    let a = ^[0; 0]
    0
""", "Array fill count must be positive", """\
fn main() -> i32
    let a = [0; 2]
    0
"""),
    # _emit_array_lit: `[]` with no declared type.
    "empty_array_untyped": ("""\
fn main() -> i32
    let a = ^[]
    0
""", "Empty array literal needs a declared array type (e.g. `let a: [0]u8 = []`)", """\
fn main() -> i32
    let a: [0]u8 = []
    0
"""),
    # _emit_const_array: an array literal for a scalar const. Located at
    # the initialiser: a module-level site, so no expression is being
    # emitted to default to.
    "const_array_scalar_type": ("""\
const A: i64 = ^[1, 2]
""" + MAIN0, "Const array 'A' must have array type, got i64", """\
const A: [2]i64 = [1, 2]
""" + MAIN0),
    # _emit_heap_expr: `heap` without ritzlib.memory.
    "heap_without_memory": ("""\
struct P
    x: i64

fn main() -> i32
    let p = ^heap P { x: 1 }
    0
""", "heap requires ritzlib.memory (malloc not found)", """\
import ritzlib.memory

struct P
    x: i64

fn main() -> i32
    let p = heap P { x: 1 }
    0
"""),
    # A generic fn named as a value (AGAST #4661): a template has no
    # address, so only a call names it.  ritz0's name resolver said "Unknown
    # identifier: id", though `id` is declared; ritz1 emitted a reference to
    # the uninstantiated template.  `id<i32>` as a value doesn't parse.
    "generic_fn_value": ("""\
fn id<T>(x: T) -> T
    x

fn main() -> i32
    let f = ^id
    0
""", GENERIC_FN_VALUE, """\
fn id<T>(x: T) -> T
    x

fn main() -> i32
    let f = id(1)
    0
"""),
    "generic_fn_value_argument": (GEN + """\
fn main() -> i32
    ap(^id) - 3
""", GENERIC_FN_VALUE, GEN + """\
fn main() -> i32
    ap(id_i32) - 3

fn id_i32(x: i32) -> i32
    id(x)
"""),
    "generic_fn_value_return": (GEN + """\
fn g() -> fn(i32) -> i32
    return ^id
""" + MAIN0, GENERIC_FN_VALUE, GEN + """\
fn g(x: i32) -> i32
    return id(x)
""" + MAIN0),
}


@pytest.mark.integration
@pytest.mark.parametrize("row", sorted(ROWS))
def test_user_error_is_located_not_a_traceback(tmp_path, row):
    marked, message, _ = ROWS[row]
    src, where = _located(marked)
    comp = _compile(tmp_path, src)
    assert comp.returncode != 0, f"accepted {row}:\n{src}"
    assert "Traceback (most recent call last)" not in comp.stderr, comp.stderr[-3000:]
    assert f"main.ritz:{where}: {message}" in comp.stderr, comp.stderr[-3000:]


@pytest.mark.integration
@pytest.mark.parametrize("row", sorted(ROWS))
def test_corrected_program_still_compiles(tmp_path, row):
    good = ROWS[row][2]
    comp = _compile(tmp_path, good)
    assert comp.returncode == 0, f"{row}:\n{good}\n{comp.stderr[-3000:]}"


# AGAST #4654 / #4665: every compiler refuses each row with ritz0's words,
# at the `^`.  ritz1 named an emitter failure ("ritz1 cannot emit: unhandled
# EXPR_MEMBER") or a later, unrelated fault, or compiled the row.  A row
# listed here is a known ritz1 gap: a strict xfail.
RITZ1_GAPS = {
    "array_fill_zero": 4654, "bitop_arity": 4654, "const_array_scalar_type": 4654,
    "empty_array_untyped": 4654, "float_intrinsic_arity": 4654,
    "method_on_untyped": 4654, "no_method": 4654, "simd_builtin_arity": 4654,
    "strview_builtin_arity": 4654, "try_on_plain_value": 4654,
    "tuple_destructure_count": 4654, "unknown_variant": 4654,
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_compiler_says_it_there(tmp_path, compiler):
    gaps = {} if compiler == "ritz0" else RITZ1_GAPS
    assert_refusals(compiler, tmp_path,
                    {row: (marked, message) for row, (marked, message, _) in ROWS.items()},
                    gaps)


@pytest.mark.parametrize("compiler", [c for c in COMPILERS if c != "ritz0"])
def test_ritz1_compiles_each_corrected_program(tmp_path, compiler):
    bad = []
    for row, (_, _, good) in sorted(ROWS.items()):
        comp, _, _ = _compile3(compiler, tmp_path, row, good)
        if comp.returncode != 0:
            bad.append(f"{row}: {(comp.stdout + comp.stderr)[-500:]}")
    assert not bad, "\n".join(bad)


def test_no_bare_value_error_left_in_the_emitter():
    """LARB review/5 N4: every site is a SourceError or an InternalError."""
    here = Path(__file__).parents[1]
    # The emitter split moves code into emitter/*.py (AGAST #1826).
    sources = [here / "emitter_llvmlite.py"] + [
        p for p in sorted((here / "emitter").glob("*.py")) if not p.name.startswith("test_")]
    for path in sources:
        assert path.read_text().count("raise ValueError") == 0, path.name


def test_internal_error_is_not_dressed_as_a_user_error():
    """An invariant stays a traceback: InternalError is no EmitError, so
    ritz0's top level re-raises it rather than printing it as a diagnostic."""
    from emitter_llvmlite import EmitError, InternalError, SourceError
    assert not issubclass(InternalError, EmitError)
    # Both stay ValueErrors: `except ValueError` fallbacks (an lvalue address
    # before spilling an rvalue) must behave as they did before #1390.
    assert issubclass(InternalError, ValueError)
    assert issubclass(SourceError, ValueError) and issubclass(SourceError, EmitError)
