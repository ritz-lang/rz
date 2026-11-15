"""A generic struct literal nested three or more levels deep (AGAST #3342).

    let c = Cell<Cell<Cell<i32>>> { v: Cell<Cell<i32>> { v: Cell<i32> { v: 9 } } }

ritz0 keys an instance by `mangle_type_name` of its type arguments
(`Cell<Cell<Cell<i32>>>` is the instance `Cell$Cell_Cell_i32`), and rewrites
every generic type it names to that instance.  A field typed by a type
parameter (`v: T`) was the exception: substituting T handed back the raw
`Cell<Cell<i32>>`, which the emitter spelled its own way, `Cell$Cell$i32`, found
no struct of that name and lowered the field as i8.  Two levels happened to
work because `Cell<i32>` is spelled `Cell$i32` both ways.  The literal then died
in the emitter with a Python TypeError; ritz1 compiled it.

The same goes for a type parameter's value inside a generic body: `Cell<T>`
with T = `Cell<i32>` must key the instance as `Cell_Cell_i32`, not by its
already-mangled spelling, for a struct literal and a generic call alike.

Each program reads the innermost value back at run time, on all three
compilers.
"""

import pytest

from test_right_shift import _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

CELL = "struct Cell<T>\n    v: T\n"
PAIR = "struct Pair<A, B>\n    a: A\n    b: B\n"

PROGRAMS = {
    # The ticket's program.
    "cell3": (CELL + """\
fn main() -> i32
    let c = Cell<Cell<Cell<i32>>> { v: Cell<Cell<i32>> { v: Cell<i32> { v: 9 } } }
    c.v.v.v
""", 9),
    "cell4": (CELL + """\
fn main() -> i32
    let c = Cell<Cell<Cell<Cell<i32>>>> { v: Cell<Cell<Cell<i32>>> { v: Cell<Cell<i32>> { v: Cell<i32> { v: 11 } } } }
    c.v.v.v.v
""", 11),
    # Two type parameters, one of them itself an instance, under two Cells.
    "mixed": (CELL + PAIR + """\
fn main() -> i32
    let p = Pair<i32, Cell<i64>> { a: 5, b: Cell<i64> { v: 7 } }
    let c = Cell<Cell<Pair<i32, Cell<i64>>>> { v: Cell<Pair<i32, Cell<i64>>> { v: p } }
    c.v.v.a + (c.v.v.b.v as i32)
""", 12),
    # The nest built inside a generic body, where T is itself an instance.
    "generic_body": (CELL + """\
fn wrap<T>(x: T) -> Cell<Cell<T>>
    Cell<Cell<T>> { v: Cell<T> { v: x } }
fn main() -> i32
    let c = wrap<Cell<i32>>(Cell<i32> { v: 13 })
    c.v.v.v
""", 13),
    # A generic call there keys its instance the same way: wrap's
    # mk<Cell<T>> and main's mk<Cell<Cell<i32>>> are one function.
    "generic_call": (CELL + """\
fn mk<T>(x: T) -> Cell<T>
    Cell<T> { v: x }
fn wrap<T>(x: T) -> Cell<Cell<T>>
    mk<Cell<T>>(mk<T>(x))
fn main() -> i32
    let c = wrap<Cell<i32>>(Cell<i32> { v: 15 })
    let d = mk<Cell<Cell<i32>>>(Cell<Cell<i32>> { v: Cell<i32> { v: 2 } })
    c.v.v.v + d.v.v.v
""", 17),
    # The same call as a `let` initialiser: ritz1 typed `mk<Cell<T>>(..)` by
    # its unsubstituted type args, `Cell$Cell$T`, and refused the annotation
    # `Cell<Cell<T>>` = `Cell$Cell$Cell$i32` (AGAST #3355).
    "generic_call_let": (CELL + """\
fn mk<T>(x: T) -> Cell<T>
    Cell<T> { v: x }
fn wrap<T>(x: T) -> Cell<Cell<T>>
    let r: Cell<Cell<T>> = mk<Cell<T>>(mk<T>(x))
    r
fn main() -> i32
    let c = wrap<Cell<i32>>(Cell<i32> { v: 15 })
    let d = mk<Cell<Cell<i32>>>(Cell<Cell<i32>> { v: Cell<i32> { v: 2 } })
    c.v.v.v + d.v.v.v
""", 17),
    # T a scalar: `mk<Cell<T>>` must still be `Cell$Cell$i32`, not `Cell$Cell$T`.
    "generic_call_i32": (CELL + """\
fn mk<T>(x: T) -> Cell<T>
    Cell<T> { v: x }
fn wrap<T>(x: T) -> Cell<Cell<T>>
    let r: Cell<Cell<T>> = mk<Cell<T>>(mk<T>(x))
    r
fn main() -> i32
    let c = wrap<i32>(19)
    c.v.v
""", 19),
}


# ritz1 typed `mk<Cell<T>>(..)` in a generic body as `Cell$Cell$T` until
# #3343 substituted T inside a nested call type arg (AGAST #3355).
GAPS = {}


def _cases():
    for name in sorted(PROGRAMS):
        for compiler in COMPILERS:
            gap = GAPS.get((name, compiler))
            marks = [pytest.mark.xfail(strict=True, reason=f"#{gap}")] if gap else []
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.integration
@pytest.mark.parametrize("name,compiler", list(_cases()))
def test_nested_generic_struct_lit_reads_back(request, compiler, name, tmp_path):
    source, want = PROGRAMS[name]
    assert _run(request, compiler, tmp_path, source) == want
