"""`h.f(args)` calls a `fn(...)` field `f` (LARB R41, AGAST #3380/#3381, LANGUAGE_SPEC §5.5).

THE DEFECT

ritz0 and ritz1 refused `h.f(1)` on a struct whose field `f` is a function pointer,
"no method `f` on `H`", and accepted only `(h.f)(1)`. lexis calls
`element.get_attribute(attr_name)` through such a field
(lib/style/matching.ritz).

THE RULE (LARB R41)

A method `f` wins; otherwise a `fn(...)` field `f` is called with exactly the
written arguments (`h` isn't passed). A type with both a method and a fn field
named `f` refuses `h.f(...)` at `f`, naming `(h.f)(...)`, which always calls
the field. Each row runs on ritz0, ritz1 and ritz1_selfhosted (#3381).
"""

import pytest

from ref_rules import method_and_field, no_method
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

FNS = """\
fn dbl(x: i32) -> i32
    x * 2

fn add(a: i32, b: i32) -> i32
    a + b

struct H
    f: fn(i32) -> i32
    g: fn(i32, i32) -> i32
    n: i32
"""

# name -> (program, exit status)
RUNS = {
    # The ticket's form: no method `f`, so the field is called with `20`.
    "field_call": FNS + """
pub fn main() -> i32
    let h = H { f: dbl, g: add, n: 0 }
    h.f(20) + 1
""",
    # Exactly the written arguments, through a pointer receiver (lexis's
    # `element` is a `*Element`).
    "field_call_through_pointer": FNS + """
fn go(h: *H) -> i32
    h.g(30, 4)

pub fn main() -> i32
    var h = H { f: dbl, g: add, n: 0 }
    go(@h)
""",
    # A method wins over a field of the same name that isn't a fn.
    "method_wins": FNS + """
impl H
    fn n(self: @H) -> i32
        self.n + 5

pub fn main() -> i32
    let h = H { f: dbl, g: add, n: 2 }
    h.n()
""",
    # `(h.f)(1)` always calls the field, even beside a method `f`.
    "parenthesised_beside_method": FNS + """
impl H
    fn f(self: @H, x: i32) -> i32
        99

pub fn main() -> i32
    let h = H { f: dbl, g: add, n: 0 }
    (h.f)(8)
""",
}
WANT = {
    "field_call": 41,
    "field_call_through_pointer": 34,
    "method_wins": 7,
    "parenthesised_beside_method": 16,
}

# name -> (program with `^` at the error, message)
REFUSED = {
    "method_and_fn_field": (
        FNS + """
impl H
    fn f(self: @H, x: i32) -> i32
        99

pub fn main() -> i32
    let h = H { f: dbl, g: add, n: 0 }
    h.^f(1)
""",
        method_and_field("f", "H", "(h.f)(1)"),
    ),
    # A field that isn't a fn is not called: still no method.
    "non_fn_field": (
        FNS + """
pub fn main() -> i32
    let h = H { f: dbl, g: add, n: 0 }
    h.^n(1)
""",
        no_method("n", "H"),
    ),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_fn_field_called_like_a_method(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, RUNS[name]) == WANT[name]


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_fn_field_call_refused(tmp_path, compiler, name):
    program, message = REFUSED[name]
    _assert_refused(compiler, tmp_path, name, program, message)
