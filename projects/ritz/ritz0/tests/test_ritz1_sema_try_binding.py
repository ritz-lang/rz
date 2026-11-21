"""AGAST #3974: `let x = f()?` binds x as the Ok / Some payload, in Sema too.

THE GAP

Sema bound an unannotated `let x = f()?` untyped: sema_expr_ty had no
EXPR_TRY case.  So sema_bool_kind answered BK_UNSURE for a field or method of
x, and bool_check refused `if x.b` / `if not x.m()` with "ritz1 cannot tell
that it is" (angelo's src/loader/ttf.ritz:184-187, `let offset_table =
parse_offset_table(@&reader)?` then `if not offset_table.is_truetype()`).
ritz0 compiles them; the emitter already typed the local (its `?` var-decl
path).

THE CHANGE

sema_expr_ty types `c?` as the struct c's Result<T, E> carries in Ok or its
Option<T> in Some (sema_tagged_payload), whatever shape `c` is: a call, a
method call or a field.

THE TESTS

Each carrier shape, with `if x.b`, `if x.m()` and `if not x.m()` on the
binding, compiles on all three compilers.  Every row failed on ritz1 and
ritz1_selfhosted before the change.
"""

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = """\
struct T
    b: bool
    v: i32

impl T
    pub fn ok(self) -> bool
        self.v == 1

fn mk() -> Result<T, StrView>
    Ok(T { b: true, v: 1 })

fn mk_opt() -> Option<T>
    Some(T { b: true, v: 1 })

struct F
    n: i32

impl F
    pub fn mk(self: @F) -> Result<T, StrView>
        Ok(T { b: true, v: self.n })

struct H
    r: Result<T, StrView>

"""

# The `?` operand, and the carrier the enclosing fn returns.
CARRIERS = {
    "result_call": ("mk()", "Result<i32, StrView>", "Err(\"no\")", "Ok(0)"),
    "option_call": ("mk_opt()", "Option<i32>", "None", "Some(0)"),
    "result_method": ("f.mk()", "Result<i32, StrView>", "Err(\"no\")", "Ok(0)"),
    "result_field": ("h.r", "Result<i32, StrView>", "Err(\"no\")", "Ok(0)"),
}


def _program(form):
    operand, ret, fail, done = CARRIERS[form]
    return PRELUDE + (
        f"fn load(f: @F, h: @H) -> {ret}\n"
        f"    let x = {operand}?\n"
        "    if not x.b\n"
        f"        return {fail}\n"
        "    if x.ok()\n"
        f"        return {done}\n"
        "    if not x.ok()\n"
        f"        return {fail}\n"
        f"    {done}\n"
        "\n"
        "fn main() -> i32\n"
        "    var f: F = F { n: 1 }\n"
        "    var h: H = H { r: mk() }\n"
        "    match load(@f, @h)\n"
        "        _ => 0\n"
    )


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", CARRIERS)
def test_a_field_or_method_of_a_try_binding_is_a_condition(request, tmp_path, compiler, form):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, f"try_{form}", _program(form))
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused `let x = {CARRIERS[form][0]}?`:\n{out}"
