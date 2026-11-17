"""AGAST #3503: ritz1's call_check runs on Sema, before emission (#1816).

THE CHANGE

call_check (AGAST #1629: a call's arguments fit its callee; #3255 an unknown
fn; #3419 a private fn of another file; #3420 the newtype box) was five
`pub fn call_check_*(s: *EmitterState, ..)` called mid-lowering from
emit_expr_call, emit_expr_method and the UFCS / method argument cascades.  It
now takes `sm: *Sema` and runs from sema_walk.ritz at each call: a free call
before its arguments, a method call after its receiver (emit_expr_method
lowers that first) and before its arguments.  Sema resolves the callee the
way the emitter dispatches it, so the reports are the emitter's; the emitter
lowers only calls Sema passed.  A call error now stops the compile before
emission.

The diagnostics themselves are the shared tables' (test_call_arity_and_type.py,
test_method_call_args.py, test_int_arg_for_struct_param.py,
test_ritz1_private_fn_cross_file.py, test_ritz1_unknown_generic_call.py, ..),
unchanged; the commit compared every file of ritz0/test, ritzlib, examples and
ritz1/src, and every program the ritz1 pytest files compile, against the
pre-move compilers: the same IR, and the same words for each refusal.

THE TESTS

One program, both ritz1 compilers: each kind of call error (a static call's,
a free call's and a method's count, an argument's kind, an unknown fn), then
a fn whose frame is over the stack, which is frame_limit's error, a codegen
limit that stays on the emitter: it is no longer printed.  Before the move all
six were.  (It was a write to a `let` until #3504, then a literal that doesn't
fit its slot until #3510.)

`sizeof(f(1))` never evaluates its operand, so its call isn't judged, as on
the emitter and in ritz0.

`W_bump<i32>(c)` names a generic impl's method: generic_method_check says so
(LARB R37), and it is that one error, not also "Unknown function: W_bump".
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

PROGRAM = """\
struct P
    x: i64

impl P
    fn get(self: *P, k: i64) -> i64
        self.x + k
    fn mk(x: i64) -> P
        P { x: x }

fn two(a: i64, b: i64) -> i64
    a + b

fn takes(p: P) -> i64
    p.x

fn main() -> i32
    let p: P = P.mk(1, 2)
    let a: i64 = two(1)
    let b: i64 = p.get()
    let c: i64 = takes(5)
    let d: i64 = nope(3)
    var m: i32 = huge()
    0

fn huge() -> i32
    var big: [16777216]u8
    big[0] = 1
    big[0] as i32
"""

WANTED = [
    ("17:16", "`mk` called with 2 argument(s) but defined with 1"),
    ("18:18", "`two` called with 1 argument(s) but defined with 2"),
    ("19:18", "`get` called with 1 argument(s) but defined with 2"),
    ("20:24", "argument 1 of `takes` has the wrong type: parameter `p` is declared `P` but its argument is an integer"),
    ("21:18", "Unknown function: nope"),
]

SIZEOF = """\
fn two(a: i64, b: i64) -> i64
    a + b

fn main() -> i32
    let s: i64 = sizeof(two(1))
    if s == 8
        return 0
    1
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_call_errors_stop_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_call", PROGRAM)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == WANTED, f"{compiler}:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sizeof_operand_call_is_not_judged(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_call_sizeof", SIZEOF)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"


GENERIC_METHOD = """\
struct W<T>
    x: T
    y: T

impl<T> W<T>
    fn bump(self:&)
        self.x = self.x + 1

pub fn main() -> i32
    var c: W<i32> = W<i32> { x: 3, y: 0 }
    W_bump<i32>(c)
    c.x
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_generic_method_by_symbol_is_one_error(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_call_generic", GENERIC_METHOD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == [("11:5", "`bump` is a method of generic `W<T>`: call it as `w.bump()`")], f"{compiler}:\n{out}"
