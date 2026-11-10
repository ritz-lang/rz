"""AGAST #2543: a `*[N]S` copied out of another keeps S, so `p[i].f` resolves.

    var x: [3]S
    var q: *[3]S = @x
    let p = q
    if p[1].b != 5      # ritz1: "cannot emit: unhandled EXPR_MEMBER"

`p[i].f` lowers through `p#`, the `*S` view add_array_view binds beside `p`, and
the view needs S's name.  inferred_array_elem_name found it on the initialiser:
`@x` names it, but a `*[N]S` local didn't, since a name on the local itself
would register it as a `*S`.  So `let p = q`, `let p: *[3]S = q`, and `let p =
*r` with `r: **[3]S` (#2539) all bound `p` without a view, and both `p[i].f`
reads and stores were refused.  `q[i].f` on q itself was fine: `@x` named q's
view.  A `*[N]S` local now names S, as a parameter of the type did.

ritz0 is the oracle: 0 on every row.  The checks return the number of the
first that failed, so a red cell says which access broke.
"""

import pytest

from test_ritz1_array_ptr_element import COMPILERS, run_with  # noqa: F401  (fixture)

_S = "struct S\n    a: i32\n    b: i32\n\n"

_FILL = """\
    var x: [3]S
    x[0] = S { a: 1, b: 2 }
    x[1] = S { a: 3, b: 5 }
    x[2] = S { a: 7, b: 11 }
"""

# 1-2 read; 3-5 store and its neighbours; 6 compound; 7 a copy of the copy.
_CHECKS = """\
    if p[1].b != 5
        return 1
    if p[2].a + p[0].b != 9
        return 2
    p[2].a = 40
    if x[2].a != 40
        return 3
    if x[2].b != 11
        return 4
    if x[1].a != 3
        return 5
    p[1].b += 2
    if x[1].b != 7
        return 6
    let p2 = p
    p2[0].a = 13
    if x[0].a != 13
        return 7
    return 0
"""

# How `p` comes to hold @x.  `{pann}` is "" (inferred) or ": *[3]S".
SOURCES = {
    # The ticket's program.
    "copy_local": "    var q: *[3]S = @x\n    let p{pann} = q\n",
    "copy_local_var": "    var q: *[3]S = @x\n    var p{pann} = q\n",
    # q itself inferred, from `@&x` (an `@x` can't be stored through).
    "copy_inferred": "    let q = @&x\n    let p{pann} = q\n",
    # #2539: through a `**[3]S`, inferred and annotated.
    "deref_inferred_r": "    var q: *[3]S = @x\n    let r = @q\n    let p{pann} = *r\n",
    "deref_annotated_r": "    var q: *[3]S = @x\n    let r: **[3]S = @q\n    let p{pann} = *r\n",
    "deref_mut_r": "    var q: *[3]S = @x\n    let r = @&q\n    let p{pann} = *r\n",
}


def _program(source: str, pann: str) -> str:
    return (
        _S
        + "pub fn main() -> i32\n"
        + _FILL
        + SOURCES[source].format(pann=pann)
        + _CHECKS
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ann", ["inferred", "annotated"])
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_struct_array_pointer_copy(run_with, source, ann, compiler):
    pann = "" if ann == "inferred" else ": *[3]S"
    assert run_with(compiler, f"{source}_{ann}", _program(source, pann)) == 0


# A `*[N]S` parameter already names S, so `let p = q` resolved; `let p2 = p`,
# check 7, copies a local and didn't.
_PARAM = (
    _S
    + "fn f(q: *[3]S, x: *[3]S) -> i32\n"
    + "    let p = q\n"
    + _CHECKS
    + "\npub fn main() -> i32\n"
    + _FILL
    + "    return f(@x, @x)\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_array_pointer_param_copy(run_with, compiler):
    assert run_with(compiler, "param_copy", _PARAM) == 0


# A `*[N]S` is not a `*S`: `p.b` and `(*r).b` name no element, and both compilers
# refuse them.  The first fix put S in the local's type_name, which made each a
# `*S` and read element 0's b (test_ritz1_addr_of_borrow.py's untyped_field).
NOT_AN_ELEMENT = {
    "copy_field": "    let p = q\n    return p.b\n",
    "copy_annotated_field": "    let p: *[3]S = q\n    return p.b\n",
    "copy_inferred_field": "    let q2 = @&x\n    let p = q2\n    return p.b\n",
    "ref_deref_field": "    let r = @q\n    return (*r).b\n",
    "ref_annotated_deref_field": "    let r: **[3]S = @q\n    return (*r).b\n",
    "ref_copy_field": "    let r = @q\n    let p = *r\n    return p.b\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_AN_ELEMENT))
def test_struct_array_pointer_is_not_its_element(run_with, name, compiler):
    program = (
        _S
        + "pub fn main() -> i32\n    var x: [3]S\n    var q: *[3]S = @x\n"
        + NOT_AN_ELEMENT[name]
    )
    with pytest.raises(AssertionError, match=f"failed on {name}"):
        run_with(compiler, name, program)
