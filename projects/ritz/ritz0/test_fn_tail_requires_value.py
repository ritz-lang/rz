"""A fn that declares a return type must not reach its end without a value.

AGAST #1429. The emitter used to fall through to an implicit zero, so a fn
promising an `i64` could quietly return 0 from a tail `if`, a tail loop, a
`pass` arm or a call to a procedure, named or a method (AGAST #2237). That is
now a hard error.

The accepted half matters as much as the rejected half. Every earlier attempt
at this check (#1406 v2-v4) redded live code by rejecting shapes that are fine:
a procedure's tail runs for effect, an if/else whose arms all return never
reaches the end, and a `while true` with no `break` never leaves.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
MESSAGE = "can reach its end without producing a value"


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    out = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(out), "--no-runtime"], env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


_BOX = "struct B\n    v: i64\nimpl B\n    fn p(self)\n        var i: i64 = 1\n"
_TRAIT = ("trait T\n"
          "    fn t(self)\n"
          "struct B\n"
          "    v: i64\n"
          "impl T for B\n"
          "    fn t(self)\n"
          "        var i: i64 = 1\n")

# name -> (source, 1-based line the diagnostic must point at)
REJECTED = {
    "tail_if_no_else": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        return 1\n", 2),
    "tail_while": (
        "fn f(n: i64) -> i64\n"
        "    var i: i64 = 0\n"
        "    while i < n\n"
        "        i = i + 1\n", 3),
    "tail_for": (
        "fn f(n: i64) -> i64\n"
        "    var a: i64 = 0\n"
        "    for i in 0..n\n"
        "        a = a + 1\n", 3),
    "tail_loop_with_break": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        if n > 0\n"
        "            break\n", 2),
    "break_nested_in_a_match_arm": (
        "fn f(n: i64) -> i64\n"
        "    while true\n"
        "        match n\n"
        "            0 => break\n"
        "            _ => pass\n", 2),
    "tail_assignment": (
        "fn f(n: i64) -> i64\n"
        "    var a: i64 = 0\n"
        "    a = n\n", 3),
    "empty_arm_of_if_else": (
        "fn f(n: i64) -> i64\n"
        "    var a: i64 = 0\n"
        "    if n > 0\n"
        "        a = 1\n"
        "    else\n"
        "        return 2\n", 4),
    "else_if_chain_with_no_final_else": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        1\n"
        "    else if n < 0\n"
        "        2\n", 4),
    "pass_arm_of_if": (
        "fn f(c: bool) -> i32\n"
        "    if c\n"
        "        pass\n"
        "    else\n"
        "        7\n", 3),
    "pass_arm_of_match": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => 5\n"
        "        _ => pass\n", 4),
    "tail_call_to_a_procedure": (
        "fn g(n: i64)\n"
        "    var i: i64 = n\n"
        "fn f(n: i64) -> i64\n"
        "    g(n)\n", 4),
    # AGAST #2237: a method call resolves only as it is emitted, so these reach
    # the check by every route `_emit_method_call` has to a procedure.
    "tail_method_call_to_a_procedure": (
        _BOX + "fn f(b: B) -> i64\n"
        "    b.p()\n", 7),
    "method_call_to_a_procedure_through_a_pointer": (
        _BOX + "fn f(b: *B) -> i64\n"
        "    b.p()\n", 7),
    "static_method_call_to_a_procedure": (
        "struct B\n"
        "    v: i64\n"
        "impl B\n"
        "    fn s()\n"
        "        var i: i64 = 1\n"
        "fn f() -> i64\n"
        "    B.s()\n", 7),
    "method_call_to_a_procedure_in_an_if_arm": (
        _BOX + "fn f(b: B, c: i64) -> i64\n"
        "    if c > 0\n"
        "        b.p()\n"
        "    else\n"
        "        7\n", 8),
    "method_call_to_a_procedure_in_an_else_arm": (
        _BOX + "fn f(b: B, c: i64) -> i64\n"
        "    if c > 0\n"
        "        return 7\n"
        "    else\n"
        "        b.p()\n", 10),
    "method_call_to_a_procedure_in_a_match_arm": (
        _BOX + "fn f(b: B, n: i64) -> i64\n"
        "    match n\n"
        "        0 => b.p()\n"
        "        _ => 1\n", 8),
    # The receiver is a local of the arm, so no walk before emission can type it.
    "method_call_on_a_local_of_the_arm": (
        _BOX + "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 =>\n"
        "            let b: B = B { v: 1 }\n"
        "            b.p()\n"
        "        _ => 1\n", 10),
    "parenthesised_method_call_to_a_procedure": (
        _BOX + "fn f(b: B) -> i64\n"
        "    (b.p())\n", 7),
    "method_call_to_a_procedure_on_a_call_result": (
        _BOX + "fn mk() -> B\n"
        "    B { v: 1 }\n"
        "fn f() -> i64\n"
        "    mk().p()\n", 9),
    "method_call_to_a_procedure_on_a_field": (
        _BOX + "struct O\n"
        "    b: B\n"
        "fn f(o: O) -> i64\n"
        "    o.b.p()\n", 9),
    "method_call_to_a_procedure_on_a_generic_struct": (
        "struct W<T>\n"
        "    v: T\n"
        "impl<T> W<T>\n"
        "    fn p(self)\n"
        "        var i: i64 = 1\n"
        "fn f(w: W<i64>) -> i64\n"
        "    w.p()\n"
        "fn main() -> i32\n"
        "    return 0\n", 7),
    "trait_method_call_to_a_procedure": (
        _TRAIT + "fn f(b: B) -> i64\n"
        "    b.t()\n", 9),
    "method_call_to_a_procedure_on_a_generic_receiver": (
        _TRAIT + "fn f<T>(x: T) -> i64\n"
        "    x.t()\n"
        "fn main() -> i32\n"
        "    let b: B = B { v: 1 }\n"
        "    return f<B>(b) as i32\n", 9),
    "ufcs_method_call_to_a_procedure": (
        "struct S\n"
        "    v: i64\n"
        "fn span_touch<T>(s: *Span<T>)\n"
        "    var i: i64 = 1\n"
        "fn f(s: Span<i64>) -> i64\n"
        "    s.touch()\n"
        "fn main() -> i32\n"
        "    return 0\n", 6),
    "method_call_to_a_procedure_in_a_method": (
        "struct B\n"
        "    v: i64\n"
        "impl B\n"
        "    fn p(self)\n"
        "        var i: i64 = 1\n"
        "    fn m(self) -> i64\n"
        "        self.p()\n", 7),
    "method_call_to_a_procedure_returning_a_struct": (
        _BOX + "fn f(b: B) -> B\n"
        "    b.p()\n", 7),
    "pointer_return": (
        "struct E\n"
        "    v: i64\n"
        "fn touch(e: *E, c: i64) -> *E\n"
        "    if c == 1\n"
        "        e.v = 1\n", 4),
    "impl_method": (
        "struct B\n"
        "    v: i64\n"
        "impl B\n"
        "    fn m(self, n: i64) -> i64\n"
        "        while n > 0\n"
        "            return 1\n", 5),
    "instantiated_generic": (
        "fn f<T>(n: T, c: i64) -> T\n"
        "    if c > 0\n"
        "        return n\n"
        "fn main() -> i32\n"
        "    return f<i32>(1, 1)\n", 2),
    "while_false": (
        "fn f(n: i64) -> i64\n"
        "    while false\n"
        "        return 1\n", 2),
    "assignment_arm_of_match": (
        "fn f(n: i64) -> i64\n"
        "    var a: i64 = 0\n"
        "    match n\n"
        "        0 => a = 1\n"
        "        _ => return 2\n", 4),
    # One arm leaves and the other carries on, so the `var` is reachable.
    "code_after_an_if_with_one_endless_arm": (
        "fn f(n: i64) -> i64\n"
        "    var a: i64 = 0\n"
        "    if n > 0\n"
        "        loop\n"
        "            a = a + 1\n"
        "    else\n"
        "        a = 1\n"
        "    var z: i64 = a\n", 8),
    "code_after_a_match_with_one_returning_arm": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => return 1\n"
        "        _ => pass\n"
        "    var z: i64 = n\n", 5),
    "while_condition_that_is_only_true_at_runtime": (
        "fn f(n: i64) -> i64\n"
        "    while 1 == 1\n"
        "        if n > 0\n"
        "            return 1\n", 2),
}

# ritz1's grammar has no `dyn`, so its differential does not read this table.
REJECTED_RITZ0_ONLY = {
    "dyn_method_call_to_a_procedure": (
        _TRAIT + "fn f(b: *dyn T) -> i64\n"
        "    b.t()\n", 9),
}

ACCEPTED = {
    "if_else_every_arm_returns": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        return 1\n"
        "    else\n"
        "        return 2\n"),
    "if_else_every_arm_has_a_value": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        1\n"
        "    else\n"
        "        2\n"),
    "arm_returning_next_to_arm_with_a_value": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        return 1\n"
        "    else\n"
        "        2\n"),
    "match_every_arm_returns": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => return 1\n"
        "        _ => return 2\n"),
    "while_true_without_break": (
        "fn f(n: i64) -> i64\n"
        "    while true\n"
        "        if n > 0\n"
        "            return 1\n"),
    "loop_without_break": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        if n > 0\n"
        "            return 1\n"),
    "break_belongs_to_an_inner_loop": (
        "fn f(n: i64) -> i64\n"
        "    while true\n"
        "        while n > 0\n"
        "            break\n"
        "        return 1\n"),
    "ends_in_return_after_a_loop": (
        "fn f(n: i64) -> i64\n"
        "    while n > 0\n"
        "        return 1\n"
        "    return 0\n"),
    "parenthesised_true": (
        "fn f(n: i64) -> i64\n"
        "    while (true)\n"
        "        if n > 0\n"
        "            return 1\n"),
    "endless_loop_in_an_unsafe_block": (
        "fn f(n: i64) -> i64\n"
        "    unsafe\n"
        "        loop\n"
        "            if n > 0\n"
        "                return 1\n"),
    "if_arm_is_an_endless_loop": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        loop\n"
        "            if n > 1\n"
        "                return 1\n"
        "    else\n"
        "        return 2\n"),
    # Nothing reaches the `var`, so nothing reaches the end.
    "dead_code_after_an_if_whose_arms_all_leave": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        loop\n"
        "            if n > 1\n"
        "                return 1\n"
        "    else\n"
        "        return 2\n"
        "    var z: i64 = n\n"),
    "dead_code_after_a_match_whose_arms_all_leave": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => return 1\n"
        "        _ =>\n"
        "            loop\n"
        "                if n > 1\n"
        "                    return 2\n"
        "    var z: i64 = n\n"),
    "void_return_type": (
        "fn f(n: i64) -> void\n"
        "    var i: i64 = n\n"),
    "void_return_ending_in_a_guard": (
        "fn f(n: i64) -> void\n"
        "    if n > 0\n"
        "        var i: i64 = n\n"),
    "procedure_ending_in_a_guard": (
        "fn f(n: i64)\n"
        "    if n > 0\n"
        "        var i: i64 = n\n"),
    "procedure_ending_in_a_loop": (
        "fn f(n: i64)\n"
        "    var i: i64 = 0\n"
        "    while i < n\n"
        "        i = i + 1\n"),
    # ritzlib/hashmap.ritz:210, which redded #1406 v2.
    "procedure_ending_in_if_else_of_assignments": (
        "fn f(n: i64)\n"
        "    var a: i64 = 0\n"
        "    if n > 0\n"
        "        a = 1\n"
        "    else\n"
        "        a = 2\n"),
    # AGAST #2237: only a call that ends up in value position is judged.
    "tail_method_call_with_a_value": (
        "struct B\n"
        "    v: i64\n"
        "impl B\n"
        "    fn g(self) -> i64\n"
        "        self.v\n"
        "fn f(b: B) -> i64\n"
        "    b.g()\n"),
    "tail_method_call_in_a_procedure": (
        _BOX + "fn f(b: B)\n"
        "    b.p()\n"),
    "tail_method_call_in_a_fn_spelled_void": (
        _BOX + "fn f(b: B) -> void\n"
        "    b.p()\n"),
    "method_call_to_a_procedure_before_the_value": (
        _BOX + "fn f(b: B) -> i64\n"
        "    b.p()\n"
        "    7\n"),
    "method_call_to_a_procedure_before_a_return_in_an_arm": (
        _BOX + "fn f(b: B, c: i64) -> i64\n"
        "    if c > 0\n"
        "        b.p()\n"
        "        return 1\n"
        "    else\n"
        "        2\n"),
    "method_call_to_a_procedure_in_a_guard_before_the_tail": (
        _BOX + "fn f(b: B, c: i64) -> i64\n"
        "    if c > 0\n"
        "        b.p()\n"
        "    7\n"),
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
        "    x.t()\n"
        "fn main() -> i32\n"
        "    let a: A = A { v: 1 }\n"
        "    let c: C = C { v: 1 }\n"
        "    return (f<A>(a) + f<C>(c)) as i32\n"),
    "u8_is_not_mistaken_for_void": (
        "fn f(n: u8) -> u8\n"
        "    n\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted({**REJECTED, **REJECTED_RITZ0_ONLY}))
def test_reaching_the_end_without_a_value_is_rejected(tmp_path, name):
    source, line = {**REJECTED, **REJECTED_RITZ0_ONLY}[name]
    rc, output = _compile(tmp_path, source)
    assert rc != 0, f"{name} must not compile:\n{output}"
    assert MESSAGE in output, output
    assert f"unit.ritz:{line}:" in output, f"expected line {line}:\n{output}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_a_fn_that_cannot_fall_off_its_end_still_compiles(tmp_path, name):
    rc, output = _compile(tmp_path, ACCEPTED[name])
    assert rc == 0, f"{name} must compile:\n{output}"
