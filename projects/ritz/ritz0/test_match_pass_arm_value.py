"""AGAST #3740, #3759: `pass` has no value, so it can't be used as one.

LANGUAGE_SPEC §2.4, §6.1, §8.2 (ruled 2026-11-17): `pass` is a no-op
statement with no value.  Wherever a value is wanted (an `if` / `match` arm
whose merge is used, a `let` / `var` initialiser, a `return`, an assignment's
right side, an argument, an operand) it is a located error, at the `pass`, on
all three compilers.  If you mean 0, write 0.

Before: a scalar slot took the `pass` arm as a silent 0 on all three
compilers; a struct `if` was invalid IR on ritz0 (`phi %Big [..], [0, ..]`)
and a zero-fill on ritz1; ritz0 misnamed a pointer or `Option` slot, or
crashed unlocated (#3758).  #3740 refused a struct / enum `match` at the `let`
with a "no single value type" message; this rule now reports it at the `pass`.

`pass` as a statement, or as an arm of an `if` / `match` used as a statement,
is unchanged, as is the tail of a `-> T` fn (#1429's "can reach its end
without producing a value", pinned by test_fn_tail_requires_value.py).

ritz1 puts `error: ` before the message, as diag.ritz does.  The forms are
one table per compiler (test_row_table.py, docs/TESTING.md): 66 cases
were over the suite's test budget.
"""

import pytest

from test_ref_into_value import COMPILERS, _compile
from test_row_table import assert_refusals, assert_runs

MESSAGE = (
    "`pass` has no value, so it can't be used where a value is wanted; "
    "write the value (`0` if you mean 0)"
)

# `PASS` marks the offending `pass`: the error is located there.
BIG = "struct Big\n    a: i64\n    b: i64\n    c: i64\n    d: i64\n\n"
SMALL = "struct Big\n    a: i64\n    b: i64\n\n"
ENUM_T = "enum T\n    A\n    B\n\n"
BIG_INIT = "a: 1, b: 2, c: 3, d: 4"


def _struct_form(struct, decl, arm_a, arm_b, init):
    return (
        f"{struct}{ENUM_T}fn f(t: T, p: *Big) -> i64\n"
        f"    {decl} c: Big = match t\n"
        f"        T.A => {arm_a}\n"
        f"        T.B => {arm_b}\n"
        "    return c.a\n\n"
        "fn main() -> i32\n"
        f"    var b = Big {{ {init} }}\n"
        "    return f(T.A, @b) as i32\n"
    )


def _scalar_fn(body, ret="i64", tail="    return 0\n"):
    """`f(n: i64)` whose body is `body`; main calls it."""
    return (
        "fn g(x: i64) -> i64\n    x\n\n"
        f"fn f(n: i64, p: *i64) -> {ret}\n{body}{tail}\n"
        "fn main() -> i32\n"
        "    var v: i64 = 7\n"
        "    return f(1, @v) as i32\n"
    )


FORMS = {
    # #3740: a struct / enum annotation, `match` form.
    "match_struct_large": _struct_form(BIG, "var", "*p", "PASS", BIG_INIT),
    "match_struct_let": _struct_form(BIG, "let", "*p", "PASS", BIG_INIT),
    "match_pass_first": _struct_form(BIG, "var", "PASS", "*p", BIG_INIT),
    "match_pass_block": _struct_form(BIG, "var", "*p", "\n            PASS", BIG_INIT),
    # Two words: merged through a phi, not #3696's result slot.
    "match_struct_small": _struct_form(SMALL, "var", "*p", "PASS", "a: 1, b: 2"),
    "match_enum": (
        f"{ENUM_T}fn f(t: T) -> i64\n"
        "    var c: T = match t\n"
        "        T.A => T.B\n"
        "        T.B => PASS\n"
        "    return 0\n\n"
        "fn main() -> i32\n"
        "    return f(T.A) as i32\n"
    ),
    "match_generic": (
        "struct Box<T>\n    v: T\n\n"
        "fn f(n: i64) -> i64\n"
        "    var c: Box<i64> = match n\n"
        "        0 => Box<i64> { v: 3 }\n"
        "        _ => PASS\n"
        "    return c.v\n\n"
        "fn main() -> i32\n"
        "    return f(0) as i32\n"
    ),
    # #3759: the scalar slot (a silent 0), the `if` form, the struct `if`
    # (invalid IR on ritz0), pointer and Option slots (#3758).
    "match_scalar": _scalar_fn(
        "    var c: i64 = match n\n        0 => 5\n        _ => PASS\n",
        tail="    return c\n",
    ),
    "if_scalar": _scalar_fn(
        "    var c: i64 = if n > 0 then 5 else PASS\n", tail="    return c\n"
    ),
    "if_scalar_first": _scalar_fn(
        "    let c: i64 = if n > 0 then PASS else 5\n", tail="    return c\n"
    ),
    "if_struct": (
        f"{BIG}fn f(n: i64, p: *Big) -> i64\n"
        "    var c: Big = if n > 0 then *p else PASS\n"
        "    return c.a\n\n"
        "fn main() -> i32\n"
        f"    var b = Big {{ {BIG_INIT} }}\n"
        "    return f(1, @b) as i32\n"
    ),
    "if_pointer": _scalar_fn(
        "    var c: *i64 = if n > 0 then p else PASS\n", tail="    return *c\n"
    ),
    "match_option": _scalar_fn(
        "    var c: Option<i64> = match n\n        0 => Some(5)\n        _ => PASS\n"
    ),
    "untyped_let": _scalar_fn(
        "    let c = if n > 0 then 5 else PASS\n", tail="    return c\n"
    ),
    "bare_let": _scalar_fn("    let c: i64 = PASS\n", tail="    return c\n"),
    "returned": _scalar_fn("    return if n > 0 then 5 else PASS\n", tail=""),
    "assigned": _scalar_fn(
        "    var c: i64 = 1\n    c = match n\n        0 => 5\n        _ => PASS\n",
        tail="    return c\n",
    ),
    "argument": _scalar_fn(
        "    let c: i64 = g(if n > 0 then 5 else PASS)\n", tail="    return c\n"
    ),
}


def _marked(source):
    """`source` with its `PASS` spelled `^pass`: the error is reported there."""
    assert source.count("PASS") == 1, source
    return source.replace("PASS", "^pass")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_pass_used_as_value_is_refused(compiler, tmp_path):
    assert_refusals(
        compiler,
        tmp_path,
        {name: (_marked(src), MESSAGE) for name, src in FORMS.items()},
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", ["match_struct_large", "if_struct"])
def test_pass_is_reported_once_and_no_ir_is_written(compiler, tmp_path, name):
    """Compiled alone (a batch can't show it): one error, at the `pass`, not a
    second at the `let` (#3740's "no single value type"), and no IR."""
    marked = _marked(FORMS[name])
    where = f"{marked[: marked.index('^')].count(chr(10)) + 1}:"
    proc, ll, _ = _compile(compiler, tmp_path, name, marked.replace("^", ""))
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert out.count("`pass` has no value") == 1, out
    assert f"main.ritz:{where}" in out, out
    assert "no single value type" not in out, out
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


# `pass` where no value is wanted still compiles, and runs, on all three.
ACCEPTED = {  # name: (program, exit code)
    "match_statement": (
        f"{BIG}{ENUM_T}fn f(t: T, p: *Big) -> i64\n"
        "    var c: Big = *p\n"
        "    match t\n"
        "        T.A => c = *p\n"
        "        T.B => pass\n"
        "    return c.a\n\n"
        "fn main() -> i32\n"
        f"    var b = Big {{ {BIG_INIT} }}\n"
        "    return f(T.A, @b) as i32\n",
        1,
    ),
    "all_values": (_struct_form(BIG, "var", "*p", "*p", BIG_INIT), 1),
    "if_statement": (
        _scalar_fn(
            "    var c: i64 = 1\n    if n > 0\n        c = 2\n    else\n        pass\n    pass\n",
            tail="    return c\n",
        ),
        2,
    ),
    # A procedure's tail runs for effect: its `pass` arm wants no value.
    "procedure_tail": (
        "fn f(n: i64)\n"
        "    match n\n"
        "        0 => pass\n"
        "        _ => pass\n\n"
        "fn main() -> i32\n"
        "    f(1)\n"
        "    return 0\n",
        0,
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_pass_as_statement_still_runs(compiler, tmp_path):
    assert_runs(compiler, tmp_path, ACCEPTED)
