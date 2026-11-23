"""AGAST #4577: `{n > 0}` and `{a and b}` print `true` / `false`.

THE BUG

    import ritzlib.fmt

    pub fn main(args: Span<StrView>) -> i32
        let n: i64 = 5
        print("cmp={n > 0}\\n")        # ritz0: cmp=36025540315568129

ritz0's `_infer_ritz_type` gave every BinOp its left operand's type, so a
comparison or a logical op was typed `i64` (or `i32`, `u8`, ...). With no
ritzlib in scope that never showed: the intrinsic formatter reads the LLVM
`i1` and prints a bool. With ritzlib.fmt imported, `{x}` dispatches through
`impl Display for <type>` (#202), so the `i1` was stored into an `i64`
receiver and `Display for i64` printed the garbage upper bytes. ritz1 typed
it as bool all along. LANGUAGE_SPEC §2.6 says a bool prints `true`/`false`,
and ritz0 and ritz1 must print the same bytes (#1521, #1641).

THE FIX

A comparison (`== != < <= > >=`) is typed `bool` whatever its operands
are. A logical op (`and or && ||`) still takes its left operand's type, which
is now a bool whenever that operand is a comparison; `not` / `!` inherits its
operand's. The logical rows pin that chain, the shape the ticket names.

ORACLE

One package build per compiler with ritzlib.fmt imported (the dispatch path
the bug lives on), stdout pinned to literal bytes. The first line is the
ticket's reproduction. Each operand type a row uses is a distinct `Display`
impl the old typing would have picked.
"""

import pytest
from test_format_into import _stdout
from test_ref_into_value import COMPILERS

pytestmark = [pytest.mark.usefixtures("ritz1_bin"), pytest.mark.integration]


PROGRAM = """\
import ritzlib.fmt

struct P
    x: i64

fn seven() -> i64
    return 7

pub fn main(args: Span<StrView>) -> i32
    let n: i64 = 5
    print("cmp={n > 0}\\n")

    let k: i32 = 3
    let u: u8 = 200
    var p: P
    p.x = 4
    print("eq={n == 5} ne={n != 5} lt={n < 5} le={n <= 5} gt={n > 5} ge={n >= 5}\\n")
    print("i32={k < 2} u8={u > 100} field={p.x == 4} call={seven() > n} len={args.len > 0}\\n")
    print("and={n > 0 and k > 9} or={n > 9 or k > 1} amp={n > 0 && k > 1} pipe={n > 9 || k > 9}\\n")
    print("not={not (n > 0)} bang={!(k > 9)} nested={(n > 0) == (k > 9)}\\n")
    let c = n > 0
    let d = n > 9 or k > 9
    print("let={c} {d}\\n")
    0
"""

EXPECTED = (
    b"cmp=true\n"
    b"eq=true ne=false lt=false le=true gt=false ge=true\n"
    b"i32=false u8=true field=true call=true len=true\n"
    b"and=false or=true amp=true pipe=false\n"
    b"not=false bang=true nested=false\n"
    b"let=true false\n"
)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_comparison_and_logical_placeholders_print_as_bool(tmp_path, compiler):
    got = _stdout(compiler, tmp_path, "bool_ops", PROGRAM)
    assert got == EXPECTED, f"{compiler}: {got!r}"
