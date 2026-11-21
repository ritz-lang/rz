#!/usr/bin/env python3
"""`is_some` / `is_none` / `is_ok` / `is_err` on any receiver, not just a local (AGAST #3061).

ritz1 inlined the four predicates only when the receiver was a local naming an
`Option` / `Result`. On a call's result (`mk().is_some()`), a method's, or a
field it fell through to method dispatch and called `Option$i32_is_some`, which
nothing defines, so clang failed the link. ritz0 ran them all.

Each row says what the program must exit with. A `_false` row asks the
predicate whose answer is no, so a test that the tag is ever read can't pass
by answering yes every time. `test_member_through_levels.py`'s
`tag_of_a_value` has the local, which always worked.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

OPT = ("import ritzlib.option\n\n"
       "fn mk() -> Option<i32>\n    Some(9)\n\n"
       "fn nn() -> Option<i32>\n    None\n\n")
RES = ("import ritzlib.result\n\n"
       "fn ok() -> Result<i64, i32>\n    Ok(9)\n\n"
       "fn er() -> Result<i64, i32>\n    Err(4)\n\n")
HOLDER = ("struct H\n    o: Option<i32>\n\n"
          "impl H\n    fn get(self: @H) -> Option<i32>\n        self.o\n\n")


def _if(cond):
    return f"pub fn main() -> i32\n    if {cond}\n        return 3\n    1\n"


# name: (program, exit code).
ROWS = {
    # The call's by-value result, each predicate both ways.
    "call_is_some": (OPT + _if("mk().is_some()"), 3),
    "call_is_some_false": (OPT + _if("nn().is_some()"), 1),
    "call_is_none": (OPT + _if("nn().is_none()"), 3),
    "call_is_none_false": (OPT + _if("mk().is_none()"), 1),
    "call_is_ok": (RES + _if("ok().is_ok()"), 3),
    "call_is_ok_false": (RES + _if("er().is_ok()"), 1),
    "call_is_err": (RES + _if("er().is_err()"), 3),
    "call_is_err_false": (RES + _if("ok().is_err()"), 1),
    # Not a condition: the predicate as a value.
    "call_as_a_value": (OPT + "pub fn main() -> i32\n    let b: bool = mk().is_some()\n"
                              "    let c: bool = nn().is_some()\n    if b and not c\n        return 3\n    1\n", 3),
    # A method's result and a field are receivers too.
    "method_result": (OPT + HOLDER + "pub fn main() -> i32\n    let h = H { o: nn() }\n"
                                     "    if h.get().is_none()\n        return 3\n    1\n", 3),
    "field": (OPT + HOLDER + "pub fn main() -> i32\n    let h = H { o: mk() }\n"
                             "    if h.o.is_some()\n        return 3\n    1\n", 3),
    # A pointer field holds the enum's address, not the enum. Asked of a Some:
    # the tag is 0, and an address's first byte read as the tag rarely is.
    "pointer_field": (OPT + "struct P\n    p: *Option<i32>\n\n"
                            "pub fn main() -> i32\n    var o: Option<i32> = mk()\n    let w = P { p: @&o }\n"
                            "    if w.p.is_some()\n        return 3\n    1\n", 3),
}


def _params(table):
    for row in table:
        for compiler in COMPILERS:
            yield pytest.param(row, compiler, id=f"{row}-{compiler}")


@pytest.mark.parametrize("row,compiler", list(_params(ROWS)))
def test_enum_predicate_on_a_receiver(tmp_path, compiler, row):
    src, want = ROWS[row]
    assert _run(compiler, tmp_path, row, src) == want
