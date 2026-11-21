"""AGAST #3420 (LARB R47b, LANGUAGE_SPEC §9.2): no argument that isn't the struct
fits a by-value struct parameter, located at the argument.

    struct S { x: i32 }    fn f(s: S) -> i32    f(n * 2) / f(true) / f(a[1]) ...

R47 (#3389, #3390) named integers because #3336 measured them; R47b widens it to
every non-struct argument: arithmetic, `bool` (and any scalar), index and member
reads, and `*e` of a non-ident.  ritz0 already refused all of them.  ritz1
refused only the integers call_check's cc_sure_int vouched for; on a method or
UFCS call it *boxed* the rest into the struct (`; newtype arg box`), and on a
free call it emitted IR clang refused.  Now every form, through every call form
(free, method, static, UFCS), is "argument N of `f` has the wrong type".

One row per form and call form, not the cross product of every combination:
the rule is one check at the argument, and the forms differ in how ritz1 types
the argument, not in how the call is made.
"""

import pytest

import batching
import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEADER = """\
import ritzlib.gvec

struct S
    x: i32

struct B
    v: bool

struct H
    n: i64
    p: *i64

struct O
    items: Vec<S>

impl S
    fn add(self: *S, t: S) -> i32
        self.x + t.x

    fn mk(t: S) -> i32
        t.x

fn f(s: S) -> i32
    s.x

fn two() -> Vec<S>
    var w: Vec<S> = vec_new<S>()
    w.push(S { x: 5 })
    w.push(S { x: 1 })
    w

fn fb(b: B) -> i32
    if b.v
        return 1
    0

pub fn main() -> i32
    var s: S = S { x: 3 }
    var n: i64 = 4
    var a: [4]i64 = [1, 2, 3, 4]
    var h: H = H { n: 5, p: @n }
    var v: Vec<S> = vec_new<S>()
"""


def wrong(n, f):
    return f"argument {n} of `{f}` has the wrong type"


# The argument expressions, `$` at the column the error names.
FORMS = {
    "arith": "$n * 2",
    "bool": "$true",
    "index": "$a[1]",
    "member": "$h.n",
    "deref_member": "$*h.p",
}

# name -> (main's next lines, message).  A method's receiver is argument 1.
REFUSED = {}
for form, arg in FORMS.items():
    REFUSED[f"free_{form}"] = (f"    return f({arg})", wrong(1, "f"))
    REFUSED[f"method_{form}"] = (f"    return s.add({arg})", wrong(2, "add"))
    REFUSED[f"ufcs_{form}"] = (f"    v.push({arg})\n    return 0", wrong(2, "push"))
# A static call, and the two scalars ritz0's oracle was probed with: a bool
# into a struct whose field is a bool, and a float.
REFUSED["static_arith"] = ("    return S.mk($n * 2)", wrong(1, "mk"))
REFUSED["static_bool"] = ("    return S.mk($false)", wrong(1, "mk"))
REFUSED["free_bool_into_bool_field"] = ("    return fb($true)", wrong(1, "fb"))
REFUSED["method_float"] = ("    return s.add($1.5)", wrong(2, "add"))
# A form call_check's cc_sure_int doesn't vouch for (`*` of an address): only
# the newtype box's own refusal catches it on a method or UFCS call.
REFUSED["method_deref_addr"] = ("    return s.add($*(@n))", wrong(2, "add"))
REFUSED["ufcs_deref_addr"] = ("    v.push($*(@n))\n    return 0", wrong(2, "push"))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_non_struct_arg_for_a_struct_param_is_refused(compile_with, name, compiler):
    marked, message = REFUSED[name]
    lines = marked.splitlines()
    at = next(k for k, text in enumerate(lines) if "$" in text)
    column = 1 + lines[at].index("$")
    program = HEADER + marked.replace("$", "", 1) + "\n"
    line = 1 + HEADER.count("\n") + at
    batch = getattr(compile_with, "batch_compile", None)
    got = batching.refused(compiler, program, batch) if batch else None  # AGAST #2806
    if got is not None:
        out = got[0]
    else:
        comp, _, _ = compile_with(compiler, name, program)
        assert comp.returncode != 0, f"{compiler} took {name}"
        out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert f"main.ritz:{line}:{column}:" in out, out[-1000:]


run_with = for_header.run_with

# The migration the error asks for, `S { x: e }`, through each call form; and
# the header itself compiles, so a refusal above is the argument's.  Each is 8.
LEGAL = {
    "free": "    return f(S { x: (n * 2) as i32 })",
    "method": "    return s.add(S { x: a[1] as i32 + 3 })",
    "static": "    return S.mk(S { x: (h.n + *h.p - 1) as i32 })",
    "ufcs": "    v.push(S { x: 8 })\n    return fb(B { v: true }) + 7",
    # An element of a Vec or array of structs is the struct, though
    # get_expr_type calls an index an i64 (angelo's `add_line(fl[j], ..)`).
    "vec_elem": "    v.push(S { x: 5 })\n    v.push(v[0])\n    return s.add(v[1]) + f(v[0]) - 5",
    # A Vec bound by an inferred `let`, as angelo's is.
    "field_vec_elem": "    var o: O = O { items: two() }\n    v.push(o.items[0])\n    return s.add(o.items[0]) + v[0].x - 5",
    "inferred_vec_elem": "    let w = two()\n    v.push(w[0])\n    return s.add(w[0]) + v[0].x - 5",
    "array_elem": "    var w: [2]S = [S { x: 5 }, S { x: 1 }]\n    v.push(w[0])\n    return s.add(w[0]) + v[0].x - 5",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_the_struct_literal_migration_runs(run_with, name, compiler):
    assert run_with(compiler, name, HEADER + LEGAL[name] + "\n") == 8
