"""Nothing may use a value from a call to a procedure.

AGAST #2255. A procedure returns a dummy `i32 0` at the IR level, and these
statements used to bind it: `let x: i64 = g(n)` compiled and x was a zero the
source never wrote. #1429 and #2237 judge the implicit tail only. #2260 extends
the rule from `return`/`let`/`var` to an assignment, an argument, an operand
and a call through a fn pointer typed with no return.

One table drives both compilers, so the rule cannot drift between them. Only
emission knows a method's callee, or whether a name is really a fn pointer in
this scope, so both judge the call where they resolve it. The accepted half
pins what that buys: a local fn pointer that shadows a procedure is a value,
which is the case name lookup gets wrong (#2246).

Out of scope and not pinned here: a method call as a used `if`/`match` arm
(#2256).
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
MESSAGE = "returns nothing, so its call has no value to use here"

_G = "fn g(n: i64)\n    var i: i64 = n\n"
_BOX = ("struct B\n"
        "    v: i64\n"
        "impl B\n"
        "    fn p(self)\n"
        "        var i: i64 = 1\n"
        "    fn q(self) -> i64\n"
        "        self.v\n"
        "    fn s()\n"
        "        var i: i64 = 1\n")
_TRAIT = ("trait T\n"
          "    fn t(self)\n"
          "struct C\n"
          "    v: i64\n"
          "impl T for C\n"
          "    fn t(self)\n"
          "        var i: i64 = 1\n")
_POINT = "struct P\n    x: i64\n    y: i64\n"

# name -> (source, callee named in the diagnostic (None: a nameless fn
# pointer), 1-based line of the call)
REJECTED = {
    "return_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    return g(n)\n", "g", 4),
    "typed_let_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    let x: i64 = g(n)\n"
        "    x\n", "g", 4),
    "untyped_let_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    let x = g(n)\n"
        "    7\n", "g", 4),
    "typed_var_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    var x: i64 = g(n)\n"
        "    x\n", "g", 4),
    "untyped_var_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    var x = g(n)\n"
        "    7\n", "g", 4),
    "let_in_a_procedure": (
        _G + "fn f(n: i64)\n"
        "    let x: i64 = g(n)\n", "g", 4),
    "parenthesised_return": (
        _G + "fn f(n: i64) -> i64\n"
        "    return (g(n))\n", "g", 4),
    "parenthesised_let": (
        _G + "fn f(n: i64) -> i64\n"
        "    let x: i64 = ((g(n)))\n"
        "    x\n", "g", 4),
    "return_in_a_match_arm": (
        _G + "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => return g(n)\n"
        "        _ => 1\n", "g", 5),
    "return_in_a_block_match_arm": (
        _G + "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 =>\n"
        "            return g(n)\n"
        "        _ => 1\n", "g", 6),
    "return_in_an_if_arm": (
        _G + "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        return g(n)\n"
        "    1\n", "g", 5),
    "let_in_a_loop": (
        _G + "fn f(n: i64) -> i64\n"
        "    while n > 0\n"
        "        let x: i64 = g(n)\n"
        "        return x\n"
        "    1\n", "g", 5),
    # Each of these has its own lowering, and must not get an error of its own
    # about the type first.
    "return_from_a_struct_fn": (
        _POINT + _G + "fn f(n: i64) -> P\n"
        "    return g(n)\n", "g", 7),
    "let_annotated_with_a_struct": (
        _POINT + _G + "fn f(n: i64) -> i64\n"
        "    let p: P = g(n)\n"
        "    p.x\n", "g", 7),
    "var_annotated_with_a_struct": (
        _POINT + _G + "fn f(n: i64) -> i64\n"
        "    var p: P = g(n)\n"
        "    p.x\n", "g", 7),
    "return_from_an_i8_fn": (
        _G + "fn f(n: i64) -> i8\n"
        "    return g(n)\n", "g", 4),
    "let_narrower_than_the_dummy": (
        _G + "fn f(n: i64) -> i64\n"
        "    let x: i8 = g(n)\n"
        "    7\n", "g", 4),
    "return_from_a_method": (
        _G + "struct D\n"
        "    v: i64\n"
        "impl D\n"
        "    fn m(self) -> i64\n"
        "        return g(self.v)\n", "g", 7),
    "let_in_a_method": (
        _G + "struct D\n"
        "    v: i64\n"
        "impl D\n"
        "    fn m(self) -> i64\n"
        "        let x: i64 = g(self.v)\n"
        "        x\n", "g", 7),
    "generic_callee": (
        "fn g<X>(n: X)\n"
        "    var i: X = n\n"
        "fn f(n: i64) -> i64\n"
        "    let x: i64 = g<i64>(n)\n"
        "    x\n", "g", 4),
    "return_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    return b.p()\n", "p", 11),
    "typed_let_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    let x: i64 = b.p()\n"
        "    x\n", "p", 11),
    "untyped_let_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    let x = b.p()\n"
        "    7\n", "p", 11),
    "typed_var_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    var x: i64 = b.p()\n"
        "    x\n", "p", 11),
    "untyped_var_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    var x = b.p()\n"
        "    7\n", "p", 11),
    "method_call_through_a_pointer": (
        _BOX + "fn f(b: *B) -> i64\n"
        "    return b.p()\n", "p", 11),
    "static_method_call": (
        _BOX + "fn f() -> i64\n"
        "    let x: i64 = B.s()\n"
        "    x\n", "s", 11),
    "method_call_in_a_match_arm_return": (
        _BOX + "fn f(b: B, n: i64) -> i64\n"
        "    match n\n"
        "        0 => return b.p()\n"
        "        _ => 1\n", "p", 12),
    # AGAST #2260: the value is used by something other than the statement.
    "assignment_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    var x: i64 = 0\n"
        "    x = g(n)\n"
        "    x\n", "g", 5),
    "field_assignment_of_a_named_call": (
        _POINT + _G + "fn f(n: i64) -> i64\n"
        "    var p: P = P { x: 1, y: 2 }\n"
        "    p.x = g(n)\n"
        "    p.x\n", "g", 8),
    "index_assignment_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    var a: [2]i64 = [0, 0]\n"
        "    a[0] = g(n)\n"
        "    a[0]\n", "g", 5),
    "argument_of_a_named_call": (
        _G + "fn h(n: i64) -> i64\n"
        "    n\n"
        "fn f(n: i64) -> i64\n"
        "    h(g(n))\n"
        "    7\n", "g", 6),
    "operand_of_a_named_call": (
        _G + "fn f(n: i64) -> i64\n"
        "    g(n) + 1\n"
        "    7\n", "g", 4),
    "operand_in_a_condition": (
        _G + "fn f(n: i64) -> i64\n"
        "    if g(n) == 0\n"
        "        return 1\n"
        "    7\n", "g", 4),
    "procedure_as_a_condition": (
        _G + "fn f(n: i64) -> i64\n"
        "    if g(n)\n"
        "        return 1\n"
        "    7\n", "g", 4),
    "operand_inside_a_let": (
        _G + "fn f(n: i64) -> i64\n"
        "    let x: i64 = n * g(n)\n"
        "    x\n", "g", 4),
    "argument_of_a_method_call": (
        _BOX + "fn h(n: i64) -> i64\n"
        "    n\n"
        "fn f(b: B) -> i64\n"
        "    h(b.p())\n"
        "    7\n", "p", 13),
    "argument_to_a_method": (
        _G + "struct D\n"
        "    v: i64\n"
        "impl D\n"
        "    fn w(self, n: i64) -> i64\n"
        "        n\n"
        "fn f(d: D, n: i64) -> i64\n"
        "    d.w(g(n))\n"
        "    7\n", "g", 9),
    "operand_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    return b.p() + b.q()\n", "p", 11),
    "assignment_of_a_method_call": (
        _BOX + "fn f(b: B) -> i64\n"
        "    var x: i64 = 0\n"
        "    x = b.p()\n"
        "    x\n", "p", 12),
    "assignment_in_a_used_arm_statement": (
        _G + "fn f(n: i64) -> i64\n"
        "    var x: i64 = 0\n"
        "    let y: i64 = match n\n"
        "        0 =>\n"
        "            x = g(n)\n"
        "            1\n"
        "        _ => 2\n"
        "    y\n", "g", 7),
    "let_through_a_procedure_fn_pointer": (
        _G + "fn f(n: i64) -> i64\n"
        "    let p: fn(i64) = g\n"
        "    let x: i64 = p(n)\n"
        "    x\n", "p", 5),
    "argument_through_a_procedure_fn_pointer_param": (
        "fn h(n: i64) -> i64\n"
        "    n\n"
        "fn f(p: fn(i64), n: i64) -> i64\n"
        "    return h(p(n))\n", "p", 4),
    "nameless_procedure_fn_pointer": (
        _G + "fn f(n: i64) -> i64\n"
        "    let fs: [1]fn(i64) = [g]\n"
        "    let x: i64 = fs[0](n)\n"
        "    x\n", None, 5),
    "trait_method_on_a_generic_receiver": (
        _TRAIT + "fn f<X>(x: X) -> i64\n"
        "    let r: i64 = x.t()\n"
        "    r\n"
        "fn main() -> i32\n"
        "    let c: C = C { v: 1 }\n"
        "    return f<C>(c) as i32\n", "t", 9),
}

# ritz1 has no `dyn` (test_fn_tail_requires_value.py keeps the same split).
REJECTED_RITZ0_ONLY = {
    "dyn_method_call": (
        _TRAIT + "fn f(x: *dyn T) -> i64\n"
        "    return x.t()\n", "t", 9),
}

ACCEPTED = {
    "let_of_a_call_with_a_value": (
        "fn h(n: i64) -> i64\n"
        "    n\n"
        "fn f(n: i64) -> i64\n"
        "    let x: i64 = h(n)\n"
        "    return h(x)\n"),
    "let_of_a_method_call_with_a_value": (
        _BOX + "fn f(b: B) -> i64\n"
        "    let x: i64 = b.q()\n"
        "    return x + b.q()\n"),
    # Only the call the statement takes its value from is judged.
    "procedure_called_before_the_value": (
        _G + "fn f(n: i64) -> i64\n"
        "    g(n)\n"
        "    let x: i64 = n\n"
        "    g(x)\n"
        "    return x\n"),
    "method_procedure_called_before_the_value": (
        _BOX + "fn f(b: B) -> i64\n"
        "    b.p()\n"
        "    let x: i64 = b.q()\n"
        "    b.p()\n"
        "    return x\n"),
    # A procedure hands nothing back, so nothing here uses the dummy.
    "return_of_a_procedure_call_from_a_procedure": (
        _G + "fn f(n: i64)\n"
        "    return g(n)\n"),
    "return_of_a_method_procedure_from_a_procedure": (
        _BOX + "fn f(b: B)\n"
        "    return b.p()\n"),
    "return_of_a_procedure_call_from_a_fn_spelled_void": (
        _G + "fn f(n: i64) -> void\n"
        "    return g(n)\n"),
    "return_in_a_match_arm_of_a_procedure": (
        _G + "fn f(n: i64)\n"
        "    match n\n"
        "        0 => return g(n)\n"
        "        _ => pass\n"),
    # A value-returning fn pointer that shadows a procedure is not a procedure.
    "local_fn_pointer_shadowing_a_procedure": (
        _G + "fn h(n: i64) -> i64\n"
        "    n\n"
        "fn f(n: i64) -> i64\n"
        "    let g: fn(i64) -> i64 = h\n"
        "    let x: i64 = g(n)\n"
        "    return g(x)\n"),
    "param_fn_pointer_shadowing_a_procedure": (
        _G + "fn f(g: fn(i64) -> i64, n: i64) -> i64\n"
        "    let x: i64 = g(n)\n"
        "    return g(x)\n"),
    # A method named like a procedure is judged as the method.
    "method_with_a_value_named_like_a_procedure": (
        "fn q(n: i64)\n"
        "    var i: i64 = n\n" + _BOX + "fn f(b: B) -> i64\n"
        "    let x: i64 = b.q()\n"
        "    return b.q()\n"),
    # One node, two instantiations: the `.t()` of one must not judge the other.
    "generic_receiver_whose_methods_have_values": (
        "trait T\n"
        "    fn t(self) -> i64\n"
        "struct A\n"
        "    v: i64\n"
        "struct C\n"
        "    v: i64\n"
        "impl T for A\n"
        "    fn t(self) -> i64\n"
        "        1\n"
        "impl T for C\n"
        "    fn t(self) -> i64\n"
        "        2\n"
        "fn f<X>(x: X) -> i64\n"
        "    let r: i64 = x.t()\n"
        "    return r\n"
        "fn main() -> i32\n"
        "    let a: A = A { v: 1 }\n"
        "    let c: C = C { v: 1 }\n"
        "    return (f<A>(a) + f<C>(c)) as i32\n"),
    # AGAST #2260: a statement's own value is unused, and so is each of the
    # statements inside a used arm.
    "procedure_calls_as_statements": (
        _G + "fn f(n: i64) -> i64\n"
        "    let p: fn(i64) = g\n"
        "    p(n)\n"
        "    let y: i64 = match n\n"
        "        0 =>\n"
        "            g(n)\n"
        "            1\n"
        "        _ => 2\n"
        "    if n > 0\n"
        "        g(y)\n"
        "    y\n"),
    "procedure_fn_pointer_as_an_argument": (
        _G + "fn call(p: fn(i64), n: i64) -> i64\n"
        "    p(n)\n"
        "    n\n"
        "fn f(n: i64) -> i64\n"
        "    return call(g, n)\n"),
    # #2246's question: `-> void` is left as the tail check leaves it. That
    # ticket moves this to REJECTED.
    "let_of_a_call_spelled_void": (
        "fn g(n: i64) -> void\n"
        "    var i: i64 = n\n"
        "fn f(n: i64) -> i64\n"
        "    let x: i64 = g(n)\n"
        "    7\n"),
}


def _ritz0(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
                     env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def _ritz1(ritz1_bin, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(tmp_path / "unit.ll")],
        cwd=tmp_path, capture_output=True, text=True, env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def _assert_rejected(rc, output, name, callee, line):
    assert rc != 0, f"{name} must not compile:\n{output[-1500:]}"
    named = "this fn pointer" if callee is None else f"`{callee}`"
    assert f"{named} {MESSAGE}" in output, output[-1500:]
    assert f"unit.ritz:{line}:" in output, f"expected line {line}:\n{output[-1500:]}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted({**REJECTED, **REJECTED_RITZ0_ONLY}))
def test_ritz0_rejects_a_value_from_a_procedure(tmp_path, name):
    source, callee, line = {**REJECTED, **REJECTED_RITZ0_ONLY}[name]
    _assert_rejected(*_ritz0(tmp_path, source), name, callee, line)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_ritz0_accepts_what_uses_no_dummy(tmp_path, name):
    rc, output = _ritz0(tmp_path, ACCEPTED[name])
    assert rc == 0, f"{name} must compile:\n{output[-1500:]}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_ritz1_rejects_a_value_from_a_procedure(ritz1_bin, tmp_path, name):
    source, callee, line = REJECTED[name]
    _assert_rejected(*_ritz1(ritz1_bin, tmp_path, source), name, callee, line)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_ritz1_accepts_what_uses_no_dummy(ritz1_bin, tmp_path, name):
    rc, output = _ritz1(ritz1_bin, tmp_path, ACCEPTED[name])
    assert rc == 0, f"{name} must compile:\n{output[-1500:]}"


@pytest.mark.integration
def test_ritz1_reports_one_call_once_and_writes_no_output(ritz1_bin, tmp_path):
    """A diagnostic that still leaves a .ll behind lets a build link it anyway."""
    source, _, _ = REJECTED["typed_let_of_a_named_call"]
    rc, output = _ritz1(ritz1_bin, tmp_path, source)
    assert rc != 0 and output.count(MESSAGE) == 1, output[-800:]
    assert not (tmp_path / "unit.ll").exists()


_LIB_PROC = "pub fn lp(n: i64)\n    var i: i64 = n\n"
_USES_LIB_PROC = ("import lib\n"
                  "fn f(n: i64) -> i64\n"
                  "    return lp(n)\n"
                  "fn main() -> i32\n"
                  "    0\n")
_LIB_GENERIC = ("fn lp(n: i64)\n"
                "    var i: i64 = n\n"
                "pub fn h<T>(n: T) -> T\n"
                "    let x: i64 = lp(1)\n"
                "    n\n")
_USES_LIB_GENERIC = ("import lib\n"
                     "fn main() -> i32\n"
                     "    return h<i32>(1)\n")


@pytest.mark.integration
def test_ritz0_judges_an_imported_procedure(tmp_path):
    (tmp_path / "lib.ritz").write_text(_LIB_PROC)
    _assert_rejected(*_ritz0(tmp_path, _USES_LIB_PROC), "imported", "lp", 3)


@pytest.mark.integration
def test_ritz1_judges_an_imported_procedure(ritz1_bin, tmp_path):
    (tmp_path / "lib.ritz").write_text(_LIB_PROC)
    _assert_rejected(*_ritz1(ritz1_bin, tmp_path, _USES_LIB_PROC), "imported", "lp", 3)


@pytest.mark.integration
def test_ritz1_blames_a_generic_from_another_file_on_that_file(ritz1_bin, tmp_path):
    (tmp_path / "lib.ritz").write_text(_LIB_GENERIC)
    rc, output = _ritz1(ritz1_bin, tmp_path, _USES_LIB_GENERIC)
    assert rc != 0 and f"`lp` {MESSAGE}" in output, output[-1500:]
    assert "lib.ritz:4:" in output, output[-1500:]
