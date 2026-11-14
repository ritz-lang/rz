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
    # #2552: an annotated `@[N]S` / `@&[N]S` local named S as an `@S` local does.
    "ref_annotated_field": "    let p: @[3]S = @x\n    return p.b\n",
    "mut_ref_annotated_field": "    let p: @&[3]S = @&x\n    return p.b\n",
    "mut_ref_annotated_store_field": "    let p: @&[3]S = @&x\n    p.b = 4\n    return 0\n",
    "ref_annotated_copy_field": "    let p: @[3]S = @x\n    let p2 = p\n    return p2.b\n",
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


# AGAST #2548: the same refusals on a `*[N]S` param.  A param put S in its
# type_name, which made `q.b` a `*S` field read of element 0 in ritz1 alone.
# `@[N]S` and `@&[N]S` params share the binding, so they're refused the same way.
PARAM_NOT_AN_ELEMENT = {
    "param_field": "    return q.b\n",
    "param_copy_field": "    let p = q\n    return p.b\n",
    "param_copy_annotated_field": "    let p: {pty} = q\n    return p.b\n",
    "param_ref_deref_field": "    let r = @q\n    return (*r).b\n",
    "param_ref_copy_field": "    let r = @q\n    let p = *r\n    return p.b\n",
    "param_store_field": "    q.b = 4\n    return 0\n",
}

PARAM_TYPES = {"ptr": "*[3]S", "ref": "@[3]S", "mut_ref": "@&[3]S"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pty", sorted(PARAM_TYPES))
@pytest.mark.parametrize("name", sorted(PARAM_NOT_AN_ELEMENT))
def test_struct_array_pointer_param_is_not_its_element(run_with, name, pty, compiler):
    if pty == "ref" and name == "param_store_field":
        pytest.skip("an `@[N]S` can't be stored through either way")
    ty = PARAM_TYPES[pty]
    program = (
        _S
        + f"fn f(q: {ty}) -> i32\n"
        + PARAM_NOT_AN_ELEMENT[name].format(pty=ty)
        + "\npub fn main() -> i32\n    var x: [3]S\n    return f(@&x)\n"
    )
    with pytest.raises(AssertionError, match=f"failed on {name}_{pty}"):
        run_with(compiler, f"{name}_{pty}", program)


# AGAST #2552: an annotated `@[N]S` / `@&[N]S` local keeps its element paths
# once S is out of its type_name: `p[i].f` reads, stores and compound stores,
# and through `let p2 = p`.  An `@[3]S` is read-only, so it runs the reads.
_READS = """\
    if p[1].b != 5
        return 1
    if p[2].a + p[0].b != 9
        return 2
    let p2 = p
    if p2[2].b != 11
        return 7
    return 0
"""

ANNOTATED_LOCALS = {"ref": "    let p: @[3]S = @x\n", "mut_ref": "    let p: @&[3]S = @&x\n"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pty", sorted(ANNOTATED_LOCALS))
def test_annotated_ref_array_local_elements(run_with, pty, compiler):
    checks = _CHECKS if pty == "mut_ref" else _READS
    program = _S + "pub fn main() -> i32\n" + _FILL + ANNOTATED_LOCALS[pty] + checks
    assert run_with(compiler, f"annotated_local_elements_{pty}", program) == 0


# A method's params bind on their own path (emitter.ritz, the impl loop).
_METHOD = _S + "struct H\n    n: i32\n\nimpl H\n    fn g(self: @H, q: *[3]S) -> i32\n{body}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_array_pointer_method_param_is_not_its_element(run_with, compiler):
    program = _METHOD.format(body="        return q.b\n") + (
        "\npub fn main() -> i32\n    var x: [3]S\n    var h: H\n    return h.g(@x)\n")
    with pytest.raises(AssertionError, match="failed on method_field"):
        run_with(compiler, "method_field", program)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_array_pointer_method_param_elements(run_with, compiler):
    body = "        let p = q\n        p[1].b += 2\n        q[2].a = 40\n        return q[1].b + p[2].a\n"
    program = _METHOD.format(body=body) + (
        "\npub fn main() -> i32\n" + _FILL + "    var h: H\n    return h.g(@x)\n")
    assert run_with(compiler, "method_elements", program) == 47


# The element paths on those params keep working: reads, stores and compound
# stores, directly and through `let p = q`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pty", ["ptr", "mut_ref"])
@pytest.mark.parametrize("via", ["direct", "copy"])
def test_struct_array_pointer_param_elements(run_with, pty, via, compiler):
    # `x` is the param; `p` is x itself (direct) or `let p = x` (copy).
    checks = _CHECKS if via == "copy" else _CHECKS.replace("p[", "x[").replace("p2 = p", "p2 = x")
    program = (
        _S
        + f"fn f(x: {PARAM_TYPES[pty]}) -> i32\n"
        + ("    let p = x\n" if via == "copy" else "")
        + checks
        + "\npub fn main() -> i32\n"
        + _FILL
        + "    return f(@&x)\n"
    )
    assert run_with(compiler, f"param_elements_{pty}_{via}", program) == 0


# #2548: S moved out of a `*[N]S` param's type_name, and every reader that took
# S from there for the pointer as a whole now asks array_ptr_elem_name, as a
# `let p = q` local's readers already had to (#2543 left them refused).  Each
# returns 6, x[1].b, through the pointer `P`.
WHOLE_OPS = {
    # get_ptr_elem_size: `P + k` walks rows of `[3]S`.
    "row_arith": "    let r = P + 0\n    return r[1].b\n",
    # emit_assign's `*p = a` whole-array store.
    "store_whole": "    var y: [3]S\n    y[1] = S {{ a: 2, b: 6 }}\n    P[1].b = 1\n    *P = y\n    return P[1].b\n",
    # ref_behind / array_place_shape: `*p` read as a `[3]S`.
    "load_whole_let": "    var z: [3]S = *P\n    return z[1].b\n",
    "load_whole_assign": "    var z: [3]S\n    z = *P\n    return z[1].b\n",
    # check_array_ref_arg: `P` into a `*[3]S` param.
    "call_ptr": "    return g(P)\n",
}

_FNS = ("fn g(a: *[3]S) -> i32\n    return a[1].b\n\n"
        "fn h(a: [3]S) -> i32\n    return a[1].b\n\n")
_X = "    var x: [3]S\n    x[0] = S { a: 0, b: 0 }\n    x[1] = S { a: 1, b: 6 }\n    x[2] = S { a: 0, b: 0 }\n"


def _whole_program(holder: str, op: str) -> str:
    body = WHOLE_OPS[op].format()   # `{{` in the store's struct literal
    if holder == "local_copy":
        return (_S + _FNS + "pub fn main() -> i32\n" + _X
                + "    var q: *[3]S = @x\n    let p = q\n" + body.replace("P", "p"))
    if holder == "mut_ref_local":   # #2552
        return (_S + _FNS + "pub fn main() -> i32\n" + _X
                + "    let p: @&[3]S = @&x\n" + body.replace("P", "p"))
    ty = "@&[3]S" if holder.startswith("mut_ref") else "*[3]S"
    copy = holder.endswith("_copy")
    return (_S + _FNS + f"fn f(q: {ty}) -> i32\n"
            + ("    let p = q\n" if copy else "")
            + body.replace("P", "p" if copy else "q")
            + "\npub fn main() -> i32\n" + _X + "    return f(@&x)\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("holder", ["param", "param_copy", "mut_ref_param", "local_copy", "mut_ref_local"])
@pytest.mark.parametrize("op", sorted(WHOLE_OPS))
def test_struct_array_pointer_whole(run_with, op, holder, compiler):
    # row_arith on mut_ref_param / mut_ref_local: `q + k` of an `@&[N]S` (#2554).
    assert run_with(compiler, f"whole_{op}_{holder}", _whole_program(holder, op)) == 6


# An `@&[3]S` param or copy into an `@[3]S` param: ref_arg_dims takes S from
# array_ptr_elem_name (#2548) and the call ptrtoints the `ptr` (#2416).
_SHARED_G = "fn g(a: @[3]S) -> i32\n    return a[1].b\n\n"
MUT_INTO_SHARED = {
    "param": "fn f(q: @&[3]S) -> i32\n    return g(q)\n",
    "param_copy": "fn f(q: @&[3]S) -> i32\n    let p = q\n    return g(p)\n",
    "local": "fn f(x: *[3]S) -> i32\n    let p: @&[3]S = x as @&[3]S\n    return g(p)\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MUT_INTO_SHARED))
def test_struct_array_mut_ref_into_shared_param(run_with, name, compiler):
    program = (_S + _SHARED_G + MUT_INTO_SHARED[name]
               + "\npub fn main() -> i32\n" + _X + "    return f(@&x)\n")
    assert run_with(compiler, f"mut_into_shared_{name}", program) == 6


# ref_behind: `*P` of a `*[3]S` is a `[3]S`, so it doesn't fit a `[3]T` return
# slot.  ritz0 refuses at the `*P`; without S, ritz1 let the return through and
# refused only a later use, if any.
_T = "struct T\n    a: i32\n    b: i32\n\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("holder", ["param", "param_copy", "local_copy"])
def test_struct_array_pointer_deref_is_its_array(run_with, holder, compiler):
    if holder == "local_copy":
        fn, line = "fn rt(x: *[3]S) -> [3]T\n    var q: *[3]S = x\n    let p = q\n    return *p\n", 12
    elif holder == "param_copy":
        fn, line = "fn rt(q: *[3]S) -> [3]T\n    let p = q\n    return *p\n", 11
    else:
        fn, line = "fn rt(q: *[3]S) -> [3]T\n    return *q\n", 10
    program = _S + _T + fn + "\npub fn main() -> i32\n    var x: [3]S\n    let y = rt(@x)\n    return y[1].b\n"
    with pytest.raises(AssertionError, match=rf":{line}:12:( error:)? an array only fits a slot of the same element type"):
        run_with(compiler, f"deref_is_array_{holder}", program)


# AGAST #2553: a `**[N]S` param, `fn f(r: **[3]S)`.  #2539/#2543 made the local
# forms work (the deref_* rows above); the param bound S in its type_name, and no
# `(*r)[i].f` or `let p = *r; p[i].f` found it: "unhandled EXPR_MEMBER".  S now
# sits in pointee_array_elem_name, as for a `*[N]S` param (#2548).  `@*[N]S` and
# `@&*[N]S` params bind on the same path.
PTR_PTR_PARAMS = {
    "ptr_ptr": ("**[3]S", "@q"),
    "ref_ptr": ("@*[3]S", "@q"),
    "mut_ref_ptr": ("@&*[3]S", "@&q"),
}


def _ptr_ptr_program(pty: str, body: str) -> str:
    ty, arg = PTR_PTR_PARAMS[pty]
    return (_S + f"fn f(r: {ty}, x: *[3]S) -> i32\n" + body
            + "\npub fn main() -> i32\n" + _FILL
            + f"    var q: *[3]S = @x\n    return f({arg}, @x)\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pty", sorted(PTR_PTR_PARAMS))
@pytest.mark.parametrize("via", ["deref", "copy", "copy_annotated"])
def test_struct_array_pointer_pointer_param_elements(run_with, via, pty, compiler):
    # `p` is `(*r)` itself (deref) or `let p = *r` / `let p: *[3]S = *r` (copy).
    if via == "deref":
        # `p2` annotated: an inferred `let p2 = *r` is the copy rows' business.
        body = _CHECKS.replace("p[", "(*r)[").replace("let p2 = p", "let p2: *[3]S = *r")
    else:
        body = ("    let p = *r\n" if via == "copy" else "    let p: *[3]S = *r\n") + _CHECKS
    assert run_with(compiler, f"ptr_ptr_elements_{pty}_{via}", _ptr_ptr_program(pty, body)) == 0


# The ticket's program: 18 on ritz0.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_array_pointer_pointer_param_ticket(run_with, compiler):
    program = (_S + "fn f(r: **[3]S) -> i32\n    let p = *r\n    p[1].b = 9\n"
               "    return (*r)[1].b + p[1].b\n\npub fn main() -> i32\n"
               "    var x: [3]S\n    var q: *[3]S = @x\n    return f(@q)\n")
    assert run_with(compiler, "ptr_ptr_ticket", program) == 18


# And `*r` is a `*[3]S`, not a `*S`: no `.b` on it, as for a local (#2543).
PTR_PTR_NOT_AN_ELEMENT = {
    "pp_deref_field": "    return (*r).b\n",
    "pp_copy_field": "    let p = *r\n    return p.b\n",
    "pp_copy_annotated_field": "    let p: *[3]S = *r\n    return p.b\n",
    "pp_deref_store_field": "    (*r).b = 4\n    return 0\n",
    "pp_copy_store_field": "    let p = *r\n    p.b = 4\n    return 0\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pty", sorted(PTR_PTR_PARAMS))
@pytest.mark.parametrize("name", sorted(PTR_PTR_NOT_AN_ELEMENT))
def test_struct_array_pointer_pointer_param_is_not_its_element(run_with, name, pty, compiler):
    program = _ptr_ptr_program(pty, PTR_PTR_NOT_AN_ELEMENT[name])
    with pytest.raises(AssertionError, match=f"failed on {name}_{pty}"):
        run_with(compiler, f"{name}_{pty}", program)


# The same `(*r)[i].f` on a `**[3]S` local: #2539/#2543 covered only `let p = *r`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("source", ["deref_inferred_r", "deref_annotated_r", "deref_mut_r"])
def test_struct_array_pointer_pointer_local_elements(run_with, source, compiler):
    setup = SOURCES[source].split("    let p{pann}")[0]
    checks = _CHECKS.replace("p[", "(*r)[").replace("let p2 = p", "let p2 = *r")
    program = _S + "pub fn main() -> i32\n" + _FILL + setup + checks
    assert run_with(compiler, f"ptr_ptr_local_{source}", program) == 0
