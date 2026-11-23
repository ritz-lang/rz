"""A statement `if` / `else` whose value is used moves its arms' values out
(AGAST #4590; LANGUAGE_SPEC §13.6).

`fn f() -> T` ending in `if c / g() / else / h()` returns the arm's value,
as a match arm's or a plain tail's (own_arm_moves, own_tail_moves).  ritz1
walked each arm's trailing expression statement as a discarded value: a call
there was marked a temporary and dropped at the end of the arm, after its
value had gone into the phi.  The caller then owned a value whose heap was
freed: angelo's `parse_cmap` (`if fmt == 4 / parse_cmap_format4(..) / else
if ...`) returned a CmapTable whose four Vecs were already on the free list,
so `glyph_id(0x20)` read allocator links as cmap segments, and the
rasterize tests crashed.

Run rows exit with DROPS * 10 + the returned value's id: a dropped arm
value counts in DROPS before the caller reads it.  The `drops_*` rows pin
the other side: an `if` whose value nobody reads (a void fn's tail, a
statement with one after it, a `while` or `for` body's last) still drops its arm's
temporary, once.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

PRELUDE = """\
var DROPS: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1

# Drop glue only, through its field: no Drop impl of its own.
struct Holder
    t: Tracked
    n: i32

impl Holder
    fn again(self: @Holder) -> Holder
        Holder { t: make(self.n + 1), n: self.n + 1 }

fn make(id: i32) -> Tracked
    Tracked { id: id }

fn hold(id: i32) -> Holder
    Holder { t: make(id), n: id }

fn wrap(id: i32) -> Result<Holder, StrView>
    Ok(hold(id))

"""


def _run(body):
    return PRELUDE + body


ROWS = {
    # The two arms of a tail `if` / `else`, each a call.
    "tail_if_else_then": (_run(
        "fn pick(x: i32) -> Tracked\n"
        "    if x == 4\n        make(4)\n    else\n        make(5)\n\n"
        "fn main() -> i32\n    let t = pick(4)\n    DROPS * 10 + t.id\n"), 4),
    "tail_if_else_else": (_run(
        "fn pick(x: i32) -> Tracked\n"
        "    if x == 4\n        make(4)\n    else\n        make(5)\n\n"
        "fn main() -> i32\n    let t = pick(1)\n    DROPS * 10 + t.id\n"), 5),
    # An `else if` chain: the nested `if` is the outer else arm's value.
    "else_if_chain_middle": (_run(
        "fn pick(x: i32) -> Holder\n"
        "    if x == 4\n        hold(4)\n    else if x == 6\n        hold(6)\n"
        "    else\n        hold(7)\n\n"
        "fn main() -> i32\n    let h = pick(6)\n    DROPS * 10 + h.t.id\n"), 6),
    # A method call as the arm's value (ExprKind.Method marks temporaries too).
    "method_arm": (_run(
        "fn pick(x: i32, h: @Holder) -> Holder\n"
        "    if x == 4\n        h.again()\n    else\n        hold(1)\n\n"
        "fn main() -> i32\n    let h0 = hold(2)\n    let h = pick(4, @h0)\n"
        "    DROPS * 10 + h.t.id\n"), 3),
    # angelo's parse_cmap shape: a Result chain ending in a literal Err.
    "result_chain": (_run(
        "fn pick(x: i32) -> Result<Holder, StrView>\n"
        "    if x == 4\n        wrap(4)\n    else if x == 12\n        wrap(2)\n"
        "    else\n        Err(\"no\")\n\n"
        "fn main() -> i32\n    let h = pick(12).unwrap()\n    DROPS * 10 + h.t.id\n"), 2),
    # Nobody reads these values: each arm's call is a temporary, dropped once.
    "drops_void_tail": (_run(
        "fn pick(x: i32)\n"
        "    if x == 4\n        make(4)\n    else\n        make(5)\n\n"
        "fn main() -> i32\n    pick(4)\n    DROPS * 10\n"), 10),
    "drops_if_mid_block": (_run(
        "fn pick(x: i32) -> i32\n"
        "    if x == 4\n        make(4)\n    else\n        make(5)\n    7\n\n"
        "fn main() -> i32\n    let v = pick(4)\n    DROPS * 10 + v\n"), 17),
    # A loop body is never a value (AGAST #3749): ritz0's move checker took
    # its tail as used, so the arm's call was never a temporary and leaked
    # (AGAST #4592).
    "drops_loop_body_tail": (_run(
        "fn main() -> i32\n    var i: i32 = 0\n    while i < 3\n        i = i + 1\n"
        "        if i == 2\n            make(i)\n        else\n            make(0)\n"
        "    DROPS * 10\n"), 30),
    "drops_for_body_tail": (_run(
        "fn main() -> i32\n    for i in 0..3\n"
        "        if i == 1\n            make(1)\n        else\n            make(0)\n"
        "    DROPS * 10\n"), 30),
    "drops_for_each_body_tail": (_run(
        "fn main() -> i32\n    let xs: [3]i32 = [0, 1, 0]\n    for x in xs\n"
        "        if x == 1\n            make(1)\n        else\n            make(0)\n"
        "    DROPS * 10\n"), 30),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_if_arm_value_moves_out(compiler, tmp_path):
    assert_runs(compiler, tmp_path, ROWS)
