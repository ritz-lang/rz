"""AGAST #1487: ritz1 instantiates `Vec<T>` for a struct element type.

THE DEFECT

ritz1's monomorphiser collected struct instantiations only from a
`TYPE_STRUCT` param or an annotated var decl. So `Vec$StrView` was never
instantiated when the only mention of it was

  (a) a `@&Vec<StrView>` parameter,
  (b) an un-annotated local `var w = vec_new<StrView>()`, or
  (c) the body of a specialised fn (`vec_drop$StrView`'s `v: @&Vec<T>`),

and every member access on it failed with "unhandled EXPR_MEMBER" (or, for
(b), ritz1 emitted `alloca %Vec$StrView` for an undeclared type). #1440
(c3aa409) fixed collection. These tests pin it down for `Vec<StrView>`, an
imported struct, and a user struct, in each of the three shapes.

The ticket also lists `w[i].field` (index a `Vec<Struct>`, then take a
member). That one failed with "unhandled EXPR_MEMBER" EVEN WHEN ANNOTATED:
it is an emitter gap, not a collection gap. emit_member_ptr's index branches
knew `[N]St`, `[N]*St` and `**St` but not Vec. emit_vec_elem_member_ptr
(emitter_expr.ritz) now lowers it through the Vec's `data: *T` field.
`w[1].b` checks the stride is sizeof(T), not 1 or 8.

`w[i]` through a `@&Vec<T>` param is not covered: ritz0 rejects it too.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg, ritz1_bin  # noqa: F401

# `second.len` = 40 reads element 1 at `data + 1`, so the stride must be
# sizeof(StrView) = 16. Plus len 2 = 42.
_SV_BODY = """\
    vec_push<StrView>(@w, strview_from_cstr(c"hi"))
    vec_push<StrView>(@w, strview_from_cstr(c"0123456789012345678901234567890123456789"))
"""


def _strview_program(decl: str) -> str:
    return f"""\
import ritzlib.memory
import ritzlib.strview
import ritzlib.gvec

fn second_len(w: @&Vec<StrView>) -> i64
    let second: *StrView = w.data + 1
    second.len

fn main() -> i32
    {decl}vec_new<StrView>()
{_SV_BODY}    let r: i32 = second_len(@&w) as i32 + w.len as i32
    vec_drop<StrView>(@&w)
    return r
"""


# (a): the ONLY mention of Vec<StrView> is a ref param. The generic bodies
# (`vec_drop$StrView`, `vec_push$StrView`, `vec_get_ptr$StrView`) are
# specialised from it and read `v.len` / `v.data` / `v.cap`.
STRVIEW_REF_PARAM_ONLY = """\
import ritzlib.memory
import ritzlib.strview
import ritzlib.gvec

fn use_vec(w: @&Vec<StrView>) -> i64
    vec_push<StrView>(w, strview_from_cstr(c"abc"))
    let p: *StrView = vec_get_ptr<StrView>(w, 0)
    let n: i64 = p.len + w.len
    vec_drop<StrView>(w)
    n

fn main() -> i32
    42
"""

# Same shape, user struct element type.
USER_REF_PARAM_ONLY = """\
import ritzlib.memory
import ritzlib.gvec

struct Pair
    a: i64
    b: i64

fn use_vec(w: @&Vec<Pair>) -> i64
    var x: Pair
    x.a = 1
    x.b = 2
    vec_push<Pair>(w, x)
    let p: *Pair = vec_get_ptr<Pair>(w, 0)
    let n: i64 = p.b + w.len
    vec_drop<Pair>(w)
    n

fn main() -> i32
    42
"""

# `w[i].field` on a Vec of structs: index, then member.
_INDEX_MEMBER = """\
import ritzlib.memory
import ritzlib.gvec

struct {name}
    a: i64
    b: i64

fn main() -> i32
    {decl}vec_new<{name}>()
    var x: {name}
    x.a = 1
    x.b = 2
    var y: {name}
    y.a = 3
    y.b = 40
    vec_push<{name}>(@w, x)
    vec_push<{name}>(@w, y)
    return (w[1].b + w[0].b) as i32
"""


def _index_member(name: str, annotated: bool) -> str:
    decl = f"var w: Vec<{name}> = " if annotated else "var w = "
    return _INDEX_MEMBER.format(name=name, decl=decl)


CASES = {
    "strview_ref_param_only": (STRVIEW_REF_PARAM_ONLY, 42),
    "strview_inferred_local": (_strview_program("var w = "), 42),
    "strview_annotated_local": (_strview_program("var w: Vec<StrView> = "), 42),
    "user_ref_param_only": (USER_REF_PARAM_ONLY, 42),
    "index_member_p_inferred": (_index_member("P", False), 42),
    "index_member_pair_inferred": (_index_member("Pair", False), 42),
    "index_member_pair_annotated": (_index_member("Pair", True), 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_vec_struct_elem(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
