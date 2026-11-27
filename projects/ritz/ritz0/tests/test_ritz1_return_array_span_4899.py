"""AGAST #4899: `return @g` from a `-> [T]` fn, `g` a global `[N]T`.

ritz1 returned the array's address, an i64, where the `%Span$T` goes: SILENT,
clang refused the IR.  `let s: [u8] = @g` and `h(@g)` into a `[u8]` parameter
were right; #4778 covered `return @page.data` (an inline field), not a global.

ritz0 is the oracle.  Each program returns the value it computed: the span's
length is checked, and a store through it must reach the global (it aliases).
"""

import pytest

from test_ritz1_for_header import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

pytestmark = pytest.mark.batched

# The ticket's repro: `return @g`, a store through the span seen in `g`.
_RET = """\
var g: [512]{t}

fn f() -> [{t}]
{body}

pub fn main() -> i32
    let s: [{t}] = f()
    s[3] = 7
    if g[3] != 7
        return 1
    if s.len() != 512
        return 2
    9
"""

# A method's tail is emitted apart from a fn's.
_METHOD = """\
var g: [512]u8

struct Buf
    tag: i64

impl Buf
    fn bytes(self: @Buf) -> [u8]
        @g

pub fn main() -> i32
    let b: Buf = Buf { tag: 1 }
    let s: [u8] = b.bytes()
    s[3] = 7
    if g[3] != 7
        return 1
    if s.len() != 512
        return 2
    9
"""

PROGRAMS = {
    "return_global_u8": (_RET.format(t="u8", body="    return @g"), 9),
    "tail_global_u8": (_RET.format(t="u8", body="    @g"), 9),
    "return_global_i32": (_RET.format(t="i32", body="    return @g"), 9),
    "tail_global_i32": (_RET.format(t="i32", body="    @g"), 9),
    "method_tail_global_u8": (_METHOD, 9),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_return_global_array_as_span(run_with, name, compiler):
    program, want = PROGRAMS[name]
    assert run_with(compiler, name, program) == want
