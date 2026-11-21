"""AGAST #2544: `*X` loads the aggregate X points at, for every shape below.

With `struct D { a: i64, b: i64 }`, ritz1 typed these derefs non-struct and
emitted `load i64`, which clang rejects as soon as the value meets a `%D`
slot ("'%.N' defined with type 'i64' but expected '%D'"):

    let d: D = **gpp()                    # gpp() -> **D
    let d: D = *(*gpp() + 1)
    let d: D = **(g_pp as **D)
    let d: D = *(*(g_pp as **D) + 1)
    let d: D = *(if c then gp() + 1 else gp())
    let v: G<i64> = *((@g_g) + 0)         # a generic struct global
    let v: E = *(h.pe)                    # a tagged-enum field pointee

deref_pointee_struct_name could not name the pointee of a `**S` call or
cast, an if-expression, an `@x` of a generic struct global or a parenthesised
tagged-enum field pointee.

A row table, not a matrix: every program returns 7 only when the right
aggregate was read in full.  ritz0 is the oracle.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
EXPECTED = 7

PRELUDE_D = """\
struct D
    a: i64
    b: i64

var g_arr: [3]D
var g_x: *D = null
var g_pp: **D = null

fn gp() -> *D
    return g_x

fn gpp() -> **D
    return @g_x

fn fill()
    g_arr[0].a = 1
    g_arr[0].b = 1
    g_arr[1].a = 3
    g_arr[1].b = 4
    g_x = @g_arr[0]
    g_pp = @g_x

"""

PRELUDE_G = """\
struct D
    a: i64
    b: i64

struct G<T>
    a: T
    b: T

var g_g: G<i64>
var g_d: D

fn fill()
    g_g.a = 3
    g_g.b = 4
    g_d.a = 3
    g_d.b = 4

"""

PRELUDE_E = """\
enum E
    X(i64)
    Y

struct H
    pe: *E

fn fill()
    pass

fn pick(v: E) -> i32
    match v
        E.X(n) => n as i32
        E.Y => 0

"""


def _main(prelude: str, body: str) -> str:
    lines = "\n".join("    " + ln for ln in body.strip("\n").split("\n"))
    return prelude + "pub fn main() -> i32\n    fill()\n" + lines + "\n"


# (prelude, body): the ticket's seven shapes, then the neighbours they share.
ROWS = {
    "call_ptr_ptr": (PRELUDE_D, "g_x = @g_arr[1]\nlet d: D = **gpp()\nreturn (d.a + d.b) as i32"),
    "call_ptr_ptr_add": (PRELUDE_D, "let d: D = *(*gpp() + 1)\nreturn (d.a + d.b) as i32"),
    "cast_ptr_ptr": (
        PRELUDE_D,
        "g_x = @g_arr[1]\nlet d: D = **(g_pp as **D)\nreturn (d.a + d.b) as i32",
    ),
    "cast_ptr_ptr_add": (PRELUDE_D, "let d: D = *(*(g_pp as **D) + 1)\nreturn (d.a + d.b) as i32"),
    "if_expr": (
        PRELUDE_D,
        "let d: D = *(if true then gp() + 1 else gp())\nreturn (d.a + d.b) as i32",
    ),
    "if_expr_else": (
        PRELUDE_D,
        "let d: D = *(if false then gp() else gp() + 1)\nreturn (d.a + d.b) as i32",
    ),
    "generic_global_addr": (
        PRELUDE_G,
        "let v: G<i64> = *((@g_g) + 0)\nreturn (v.a + v.b) as i32",
    ),
    "generic_global_addr_bare": (PRELUDE_G, "let v: G<i64> = *(@g_g)\nreturn (v.a + v.b) as i32"),
    "struct_global_addr": (PRELUDE_G, "let v: D = *((@g_d) + 0)\nreturn (v.a + v.b) as i32"),
    "tagged_enum_field": (
        PRELUDE_E,
        "var e: E = E.X(7)\nvar h: H\nh.pe = @e\nlet v: E = *(h.pe)\nreturn pick(v)",
    ),
    # The `**S` call/cast as a member receiver.
    "call_ptr_ptr_member": (PRELUDE_D, "return ((*(*gpp() + 1)).a + (**gpp()).b + 3) as i32"),
}

ALL = {k: _main(p, b) for k, (p, b) in ROWS.items()}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ALL))
def test_deref_reads_the_aggregate_pointee(run_with, compiler, name):
    assert run_with(compiler, name, ALL[name]) == EXPECTED


# Arms pointing at different struct types name none; the deref must reach
# #1505's located error rather than emit `load i64` into a %D slot.
MIXED_IF = PRELUDE_D + """\
struct F
    a: i64
    b: i64

var g_f: F

pub fn main() -> i32
    fill()
    let d: D = *(if true then gp() else (@g_f) as *D as *F)
    return (d.a + d.b) as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_unnameable_if_deref_is_a_located_error(compile_with, compiler):
    comp, _, _ = compile_with(compiler, "mixed_if", MIXED_IF)
    assert comp.returncode != 0
    assert "cannot determine the struct type loaded by this '*' deref" in comp.stdout + comp.stderr
