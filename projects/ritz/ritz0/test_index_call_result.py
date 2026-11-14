"""AGAST #2428: an index into a field of a call's result, `mk().m[1]`.

    struct R
        m: [2][3]i32
    fn mk() -> R
    for v in mk().m[1]          # ritz0: ValueError: Cannot get address of: Call
    mk().m[1][2]                # the same: any read, not only a `for`

ritz0's _emit_index took the field's address with _emit_lvalue_addr, which had
no case for a call. A read now spills the call's value to a slot and indexes
it there, as if a local held it, and evaluates the call once. A store or `@`
into a call's value still isn't a place (#2518 wants a located refusal).

ritz1 and ritz1_selfhosted read an element of a by-value call's field rows, and
walk a row with `for` (#2410).  AGAST #2517: they also copy a whole row into a
`let` (`let row: [3]i32 = mk().m[1]`), from any N-D array a row of which they
can address, and read any field through a call returning `*R`, which is the
struct it points at, not a copy.

Each program returns 0, or the number of the first check that failed.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


# Every element is distinct and set, so a wrong row, column or field offset
# reads a different number, never a lucky zero. `calls` counts evaluations.
# The canaries either side of the arrays show up a wrong offset.
PRELUDE = """struct R
    lo: i64
    m: [2][3]i32
    n: [3]i32
    c: [2][2][2]i32
    hi: i64

var gr: R
var calls: i32 = 0

fn fill(r: *R)
    r.lo = 77
    r.m[0][0] = 1
    r.m[0][1] = 2
    r.m[0][2] = 3
    r.m[1][0] = 4
    r.m[1][1] = 5
    r.m[1][2] = 6
    r.n[0] = 10
    r.n[1] = 20
    r.n[2] = 30
    r.c[1][0][1] = 40
    r.c[1][1][0] = 50
    r.c[1][1][1] = 51
    r.hi = 88

fn mk() -> R
    calls = calls + 1
    var r: R
    fill(@r)
    return r

fn mkg<T>(a: T) -> R
    calls = calls + 1
    var r: R
    fill(@r)
    return r

fn mkp() -> *R
    calls = calls + 1
    return @gr

impl R
    fn me(self) -> R
        calls = calls + 1
        var r: R
        fill(@r)
        return r

fn two() -> i32
    return 2

pub fn main() -> i32
    fill(@gr)
    var k: R
    fill(@k)
"""

# Check the call ran exactly once, as code 9.
ONCE = "    if calls != 1\n        return 9\n    return 0\n"


def _prog(body: str) -> str:
    return PRELUDE + "".join("    " + line + "\n" for line in body.splitlines()) + ONCE


def _reads(call: str) -> str:
    """One read of `call`'s field rows, by each route _emit_index takes."""
    return {
        "row_elem": f"if {call}.n[1] != 20\n    return 1",
        "row_of_rows": f"if {call}.m[1][2] != 6\n    return 1",
        "first_row": f"if {call}.m[0][0] != 1\n    return 1",
        "local_index": f"let i: i32 = two()\nif {call}.m[1][i] != 6\n    return 1",
        "call_index": f"if {call}.n[two()] != 30\n    return 1",
        "whole_row": (f"let row: [3]i32 = {call}.m[1]\n"
                      "if row[0] != 4\n    return 1\nif row[2] != 6\n    return 2"),
        "in_sum": f"if {call}.m[1][1] + 1 != 6\n    return 1",
        "three_deep": f"if {call}.c[1][1][0] != 50\n    return 1",
    }


def _walk(call: str) -> str:
    return (f"var s: i32 = 0\nvar t: i32 = 0\nfor v in {call}.m[1]\n"
            "    s = s + v\n    t = t + 1\n"
            "if s != 15\n    return 1\nif t != 3\n    return 2")


BY_VALUE = {"call": "mk()", "generic_call": "mkg<i32>(1)", "method": "k.me()"}

# Runs on all three.
RUNS = {f"{root}_{shape}": _prog(body)
        for root, call in BY_VALUE.items() for shape, body in _reads(call).items()
        if shape != "whole_row"}
# A field that isn't an array falls through _emit_index to a later route,
# which must reuse the value rather than call again.
RUNS["call_pointer_field"] = PRELUDE.replace(
    "    hi: i64\n", "    hi: i64\n    q: *i32\n", 1).replace(
    "    r.hi = 88\n", "    r.hi = 88\n    r.q = @gr.n[0]\n", 1) + (
    "    if mk().q[2] != 30\n        return 1\n" + ONCE)

# A generic body is emitted once per instantiation, from the same AST: each
# must call again, in its own function, not reuse the other's value.
RUNS["generic_body_twice"] = PRELUDE.replace(
    "fn two() -> i32\n", "fn row<T>(a: T) -> i32\n    return mk().m[1][2]\n\nfn two() -> i32\n", 1) + (
    "    if row<i32>(1) != 6\n        return 1\n    if row<i64>(1) != 6\n        return 2\n"
    "    if calls != 2\n        return 9\n    return 0\n")

# AGAST #2410: a `for` over a row walks it where it is, here in the call's temporary.
RUNS.update({f"{root}_for": _prog(_walk(call)) for root, call in BY_VALUE.items()})
# AGAST #2517: a whole row into a `let`, from each root.
RUNS.update({f"{root}_whole_row": _prog(_reads(call)["whole_row"])
             for root, call in BY_VALUE.items()})
# Through a call returning `*R`: every read, and the row a `for` walks (#2426).
RUNS.update({f"pointer_call_{shape}": _prog(body)
             for shape, body in _reads("mkp()").items()})
RUNS["pointer_call_for"] = _prog(_walk("mkp()"))
# A `*R` result is the struct it points at, not a copy: a write shows.
RUNS["pointer_call_is_live"] = _prog(
    "gr.m[1][2] = 60\nif mkp().m[1][2] != 60\n    return 1")
# A scalar field through `*R`, each side of the arrays: the offsets are right.
RUNS["pointer_call_scalar"] = _prog(
    "if mkp().lo != 77\n    return 1\nif mkp().hi != 88\n    return 2").replace(
    "    if calls != 1\n", "    if calls != 2\n", 1)
# The same rule holds for a row of any N-D array: a local, a global's field,
# and the last row of a rank-3 field.
RUNS.update({f"{name}_whole_row": _prog(body) for name, body in {
    "local": "var g: [2][3]i32\ng[1][0] = 4\ng[1][2] = 6\nlet row: [3]i32 = g[1]\nif row[0] != 4\n    return 1\nif row[2] != 6\n    return 2\ncalls = 1",
    "global_field": "let row: [3]i32 = gr.m[1]\nif row[0] != 4\n    return 1\nif row[2] != 6\n    return 2\ncalls = 1",
    "rank3_call": "let row: [2]i32 = mk().c[1][1]\nif row[0] != 50\n    return 1\nif row[1] != 51\n    return 2",
}.items()})

# A row of the wrong length is still refused, as ritz0 refuses it.
REFUSED = {"call_row_wrong_length": _prog("let row: [2]i32 = mk().m[1]\nif row[0] != 4\n    return 1")}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_row_of_a_calls_value_reads(run_with, compiler, name):
    assert run_with(compiler, name, RUNS[name]) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_row_that_does_not_fit_is_refused(compile_with, compiler, name):
    """Fail closed, no IR, no traceback."""
    comp, ll, _ = compile_with(compiler, name, REFUSED[name])
    assert comp.returncode != 0 and not ll.exists(), comp.stdout + comp.stderr
    assert "Traceback" not in comp.stderr
