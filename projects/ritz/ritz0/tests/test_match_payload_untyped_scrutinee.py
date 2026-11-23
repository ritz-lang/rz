"""A match that owns a scrutinee Sema can't type still hands its payload to
the arm's binding (AGAST #4590; LANGUAGE_SPEC §13.6).

`var src = load(0).unwrap()` leaves `src` untyped in Sema (it does not type
a carrier's `unwrap`), and so `let o = src.get(i)` and the arm binding `g`
of `match o / Some(g)`.  ritz1's move check still owned the scrutinee: it
types one through ref_check's image of its local (oc_scrut_enum).  But the
arm's binding read only Sema's scope type, found none, and was never
registered as owning the payload, so the scrutinee kept it: moving `g` out
(`slot = Some(g)`) and leaving the match dropped it as well.  angelo's
`test_rasterize_at_different_sizes` (`outline_opt = Some(g)` / `break`)
freed the outline's contours and crashed in `contour_to_edges`.

The binding now takes its payload type from the owned scrutinee's type when
Sema has none, by sema_arm_payload_ty's rules (oc_match_payload).  Each run
row exits with DROPS * 10 + the value read back; the `kept_*` rows pin that
a payload the arm does not move still drops, once.
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

struct Holder
    t: Tracked
    n: i32

enum Shape
    Box(Holder)
    Nil

struct Src
    k: i32

impl Src
    fn get(self:& Src, i: i32) -> Option<Holder>
        Some(Holder { t: Tracked { id: i }, n: i })
    fn res(self:& Src, i: i32) -> Result<Holder, StrView>
        Ok(Holder { t: Tracked { id: i }, n: i })
    fn shape(self:& Src, i: i32) -> Shape
        Shape.Box(Holder { t: Tracked { id: i }, n: i })

# `load(0).unwrap()` is what Sema leaves untyped.
fn load(k: i32) -> Result<Src, StrView>
    Ok(Src { k: k })

"""


def _run(body):
    return PRELUDE + "fn main() -> i32\n    var src = load(0).unwrap()\n" + body


ROWS = {
    # angelo's shape: the payload moves out of the arm, then `break`.
    "option_moved_then_break": (_run(
        "    var slot: Option<Holder> = None\n"
        "    for i in 1..5\n"
        "        let o = src.get(i as i32)\n"
        "        match o\n"
        "            Some(g) =>\n"
        "                if g.n > 1\n"
        "                    slot = Some(g)\n"
        "                    break\n"
        "            None => pass\n"
        "    let d = DROPS\n"
        "    let h = slot.unwrap()\n"
        "    d * 10 + h.n\n"), 12),
    "result_moved": (_run(
        "    var slot: Option<Holder> = None\n"
        "    let r = src.res(3)\n"
        "    match r\n"
        "        Ok(g) =>\n            slot = Some(g)\n"
        "        Err(_) => pass\n"
        "    let h = slot.unwrap()\n"
        "    DROPS * 10 + h.n\n"), 3),
    "user_enum_moved": (_run(
        "    var slot: Option<Holder> = None\n"
        "    let e = src.shape(4)\n"
        "    match e\n"
        "        Box(g) =>\n            slot = Some(g)\n"
        "        Nil => pass\n"
        "    let h = slot.unwrap()\n"
        "    DROPS * 10 + h.n\n"), 4),
    # Not moved: the payload drops once, at the end of the match.
    "kept_option": (_run(
        "    let o = src.get(5)\n"
        "    var n: i32 = 0\n"
        "    match o\n"
        "        Some(g) =>\n            n = g.n\n"
        "        None => pass\n"
        "    DROPS * 10 + n\n"), 15),
    "kept_user_enum": (_run(
        "    let e = src.shape(6)\n"
        "    var n: i32 = 0\n"
        "    match e\n"
        "        Box(g) =>\n            n = g.n\n"
        "        Nil => pass\n"
        "    DROPS * 10 + n\n"), 16),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_payload_of_untyped_scrutinee_moves_to_binding(compiler, tmp_path):
    assert_runs(compiler, tmp_path, ROWS)
