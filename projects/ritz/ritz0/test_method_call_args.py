"""A method call with the wrong arity or a wrong-typed argument is ritz0's
located refusal, in _emit_call's words (AGAST #3319).

`p.get(1, 2)` against a one-param method was an IndexError in
_dispatch_method_call, and a struct where a method takes an `i64` was a raw
llvmlite TypeError: tracebacks with no file, line or callee.  Free-fn calls
already said "`f` called with 3 argument(s) but defined with 1" and
"argument N of `f` has the wrong type".  Method and static-method calls now
say the same (and UFCS calls did, until LARB R66 deleted them, #3496).

A method call is counted as its desugaring, `get(p, 1, 2)`: the receiver is
argument 1, as the method `:&` diagnostics already number it on all three
compilers (test_bare_place_borrow METHOD_MISFITS).  A static call has no
receiver.

ritz0 only: ritz1's side of method arity is AGAST #1629.  The rows that pass
are the auto-borrows (receiver and argument) and an sret method, which the
new checks must leave alone.
"""

import pytest
from test_ref_into_value import _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

TYPES = """\
struct P
    n: i64

struct Q
    m: i64

struct Big
    a: [8]i64

enum Lv
    Lo
    Hi

impl P
    fn get(self: *P, k: i64) -> i64
        self.n + k
    fn mk(k: i64) -> P
        P { n: k }
    fn byval(self, k: i64) -> i64
        self.n + k
    fn take(self: *P, q: *Q) -> i64
        self.n + q.m
    fn eat(self: *P, q: Q) -> i64
        self.n + q.m
    fn big(self: *P, k: i64) -> Big
        var b: Big
        b.a[0] = k
        b
    fn sz(self: *P, k: u64) -> i64
        self.n
    fn bump(self: @&P, r:& i64) -> i64
        r = r + self.n
        r

"""

SETUP = "    var p: P = P { n: 1 }\n    var q: Q = Q { m: 2 }\n"


def _src(line):
    return TYPES + "pub fn main() -> i32\n" + SETUP + f"    {line}\n    0\n"


def _wrong(n, fname, want, got):
    return (f"argument {n} of `{fname}` has the wrong type: "
            f"Type of #{n} arg mismatch: {want} != {got}")


_Q = '%"struct.ritz_module_1.Q"'
_P = '%"struct.ritz_module_1.P"'

# name: (the call, `^` before the refused token, the message)
REFUSED = {
    # Arity: at the call.
    "too_many": ("^p.get(1, 2)", "`get` called with 3 argument(s) but defined with 2"),
    "too_few": ("^p.get()", "`get` called with 1 argument(s) but defined with 2"),
    "by_value_self_too_many": ("^p.byval(1, 2)",
                               "`byval` called with 3 argument(s) but defined with 2"),
    "static_too_many": ("^P.mk(1, 2)", "`mk` called with 2 argument(s) but defined with 1"),
    "static_too_few": ("^P.mk()", "`mk` called with 0 argument(s) but defined with 1"),
    # Type: at the argument.
    "struct_for_int": ("p.get(^q)", _wrong(2, "get", "i64", _Q)),
    "static_struct_for_int": ("P.mk(^q)", _wrong(1, "mk", "i64", _Q)),
    "by_value_self_struct_for_int": ("p.byval(^q)", _wrong(2, "byval", "i64", _Q)),
    "value_for_pointer": ("p.take(^p)", _wrong(2, "take", f"{_Q}*", _P)),
    # An sret method: llvmlite's `#N` counts the slot, the message doesn't.
    "sret_method": ("p.big(^q)", _wrong(2, "big", "i64", _Q)),
    # _emit_call's #3294 and #2136 words, through the method's def.
    "another_struct": ("p.eat(^p)", "parameter `q` is declared `Q` but its argument is a `P`"),
    "enum_for_int": ("p.sz(^Lo)", ("argument 2 of `sz`: expected u64, found enum 'Lv'; "
                                   "convert with `as`")),
}

# name: (the lines, the exit code)
ACCEPTED = {
    "receiver_borrowed": ("return p.get(4) as i32", 5),
    "rvalue_receiver_spilled": ("return P { n: 2 }.get(4) as i32", 6),
    "by_value_self": ("return p.byval(4) as i32", 5),
    "static": ("return P.mk(7).n as i32", 7),
    "pointer_arg": ("return p.take(@q) as i32", 3),
    "place_borrowed_for_colon_amp": ("var k: i64 = 4\n    p.bump(k)\n    return k as i32", 5),
    "sret_method": ("let b: Big = p.big(9)\n    return b.a[0] as i32", 9),
}


def _lines(body):
    return TYPES + "pub fn main() -> i32\n" + SETUP + f"    {body}\n"


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_misfit_method_call_is_located(tmp_path, name):
    marked, message = REFUSED[name]
    _assert_refused("ritz0", tmp_path, name, _src(marked), message)


@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_a_fitting_method_call_runs(tmp_path, name):
    body, code = ACCEPTED[name]
    assert _run("ritz0", tmp_path, name, _lines(body)) == code
