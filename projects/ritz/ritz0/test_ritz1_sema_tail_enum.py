"""AGAST #3511: ritz1's tail_value and enum_as_int checks run on Sema (#1816).

THE CHANGE

tail_value (AGAST #2236: a `-> T` fn can't reach its end without a value;
#2237 / #2246 a procedure call is no value) and enum_as_int (AGAST #2136: an
enum value where an integer is expected, §10.4) were judged mid-lowering, as
`check_tail_value` / `check_tail_calls` / `enum_as_int_*(s: *EmitterState,
..)` from emit_fn, emit_impl_method, emit_stmt and emit_match_arm_body.  Both
now take `sm: *Sema` and run from sema_walk.ritz: the tail after the body is
walked (call_check notes each call it resolves to a procedure, its receiver
typed in scope), enum_as_int at each statement, at the fn's tail and at an
expression arm.  An error from either now stops the compile before
emission.

The rules and their words are the shared tables' (test_fn_tail_requires_value.py
through test_ritz1_fn_tail_requires_value.py; test_enum_discriminants.py,
test_call_misfit_pointer_and_enum.py, test_method_call_args.py), unchanged.

THE TESTS

One program, both ritz1 compilers: a tail that falls through, a tail call of
a procedure method on an arm's own local (the arm's `let` is in scope for its
value), an enum argument, an enum `return`, an enum argument in an expression
arm and an unannotated `let` of an enum passed on; then a fn whose frame is
over the stack, which is frame_limit's error, a codegen limit that stays on
the emitter: it is no longer printed.  Before the move all seven were.
And `@&` of an arm-local `let` in the arm's value, let_check's error (on Sema
since #3504), which needs the same arm scope.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

PROGRAM = """\
enum St
    A
    B

struct Box
    v: i64

impl Box
    fn touch(self)
        var i: i64 = self.v

fn take(x: u64) -> i64
    x as i64

fn gap(n: i64) -> i64
    if n > 0
        return 1

fn arm_proc(n: i64) -> i64
    match n
        0 =>
            let b: Box = Box { v: 1 }
            b.touch()
        _ => 1

fn as_arg() -> i64
    take(St.A)

fn as_return() -> i64
    return St.B

fn arm_arg(k: i64) -> i64
    match k
        0 => take(St.B)
        _ => 1

fn untyped() -> i64
    let s = St.A
    take(s)

fn huge() -> i32
    var big: [16777216]u8
    big[0] = 1
    big[0] as i32

fn main() -> i32
    huge()
"""

TAIL = "function '{}' declares a return type but can reach its end without producing a value"

# tail_value's diagnostics are `file:line:col: error: ..`, enum_as_int's
# `error: file:line:col: ..`: each keeps its own words.
WANTED = [
    ("16:5", "tail", TAIL.format("gap")),
    ("23:13", "tail", TAIL.format("arm_proc")),
    ("27:10", "enum", "argument 1 of `take`: expected u64, found enum 'St'; convert with `as`"),
    ("30:12", "enum", "expected i64, found enum 'St'; convert with `as`"),
    ("34:19", "enum", "argument 1 of `take`: expected u64, found enum 'St'; convert with `as`"),
    ("39:10", "enum", "argument 1 of `take`: expected u64, found enum 'St'; convert with `as`"),
]

# Every error is `<file>:<line>:<col>: error: <msg>` (diag; enum_as_int's
# used to put `error: ` first, AGAST #3621).
ERROR = re.compile(r"\S*main\.ritz:(\d+:\d+): error: (.*)")


def _errors(out):
    found = []
    for m in ERROR.finditer(out):
        msg = m.group(2)
        if "declares a return type" in msg:
            kind = "tail"
        elif "found enum" in msg:
            kind = "enum"
        else:
            kind = "other"
        found.append((m.group(1), kind, msg))
    return found


@pytest.mark.parametrize("compiler", COMPILERS)
def test_tail_and_enum_errors_stop_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_tail_enum", PROGRAM)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert "stack frame" not in out, f"{compiler}: the emitter ran:\n{out}"
    assert sorted(_errors(out)) == sorted(WANTED), f"{compiler}:\n{out}"


# The arm's `let`s in scope for its value reach let_check too (AGAST #2028,
# on Sema since #3504): `@&` of an arm-local `let` in the arm's value is
# refused, as the emitter and ritz0 refuse it.  With the arm's lets dropped
# before its value was walked, Sema found no `t` and ritz1 accepted this.
ARM_LET_BORROW = """\
struct P
    x: i32

fn pt_x(p: *P) -> i32
    p.x

fn f(n: i32) -> i32
    match n
        0 =>
            let t: P = P { x: 1 }
            pt_x(@&t)
        _ => 1

fn main() -> i32
    f(0)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_arm_let_is_in_scope_for_let_check(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_arm_let", ARM_LET_BORROW)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert "main.ritz:11:18: error: cannot borrow `let` binding `t` as mutable; declare it `var`" in out, f"{compiler}:\n{out}"


# The controls: an enum where an enum is expected, an explicit `as`, an enum
# tail in a procedure, a procedure called for effect before a value, and a
# `while true` with no break, all still compile.
ACCEPTED = """\
enum St
    A
    B

fn pick(s: St) -> St
    s

fn noisy()
    pass

fn proc()
    St.A

fn spin() -> i64
    while true
        noisy()

fn main() -> i32
    proc()
    noisy()
    var s: St = St.A
    s = pick(s)
    let n: i64 = s as i64
    n as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_valid_tails_and_enum_uses_compile(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_tail_enum_ok", ACCEPTED)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"
