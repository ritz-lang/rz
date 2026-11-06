#!/usr/bin/env python3
"""ritz1 rejects a `-> T` fn that can reach its end without a value (AGAST #2236).

#1429 made this a hard error in ritz0. This is the differential that keeps ritz1
in step: every case in ritz0's own tables (test_fn_tail_requires_value.py, the
single source of truth for the rule) goes through ritz1 and must get the same
verdict, at the same line. Taking the tables from that file, rather than
copying them, means a change to the rule cannot silently skip ritz1.

ritz1's AST lost three things ritz0's keeps, and each needed marking at parse
time, so each has cases in the extra tables below:

* `true` and `1` are the same int literal, but only `while true` is endless;
* `pass` and `0` are the same int literal, but only `0` is a value;
* `fn g()` and `fn g() -> void` are both TYPE_VOID, but only the first counts
  as a procedure call in a tail. ritz0 lets the second through.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import _run
from test_ritz1_method_tail_return import _block_shape_errors

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent

_spec = importlib.util.spec_from_file_location(
    "_ritz0_tail_value_rule", HERE / "test_fn_tail_requires_value.py")
RULE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RULE)

# ritz1's grammar has no `unsafe` block (AGAST #2248), so this case fails at the
# parser and never reaches the check. test_ritz1_still_cannot_parse_the_held_back_cases
# goes red when that changes, so the case cannot stay held back by accident.
RITZ1_CANNOT_PARSE = {"endless_loop_in_an_unsafe_block"}


def _ritz1(ritz1_bin, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(tmp_path / "unit.ll")],
        cwd=tmp_path, capture_output=True, text=True, env=env, timeout=300)


def _ritz0(tmp_path, source):
    src = tmp_path / "oracle.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "oracle.ll"), "--no-runtime"],
                     env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def _assert_rejected(r, name, line):
    assert r.returncode != 0, f"{name}: ritz1 compiled it, ritz0 rejects it"
    assert RULE.MESSAGE in r.stderr, (
        f"{name}: rejected, but not by this check:\n{r.stderr[-1500:]}")
    assert f"unit.ritz:{line}:" in r.stderr, (
        f"{name}: expected line {line}:\n{r.stderr[-1500:]}")


def _assert_accepted(r, name, tmp_path):
    assert r.returncode == 0, f"{name}: ritz1 rejected it:\n{r.stderr[-1500:]}"
    shape = _block_shape_errors((tmp_path / "unit.ll").read_text())
    assert not shape, f"{name}: malformed blocks:\n" + "\n".join(shape)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RULE.REJECTED))
def test_ritz1_rejects_what_ritz0_rejects(ritz1_bin, tmp_path, name):
    source, line = RULE.REJECTED[name]
    _assert_rejected(_ritz1(ritz1_bin, tmp_path, source), name, line)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(set(RULE.ACCEPTED) - RITZ1_CANNOT_PARSE))
def test_ritz1_accepts_what_ritz0_accepts(ritz1_bin, tmp_path, name):
    """The load-bearing controls: without them, rejecting everything passes."""
    _assert_accepted(_ritz1(ritz1_bin, tmp_path, RULE.ACCEPTED[name]), name, tmp_path)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_CANNOT_PARSE))
def test_ritz1_still_cannot_parse_the_held_back_cases(ritz1_bin, tmp_path, name):
    r = _ritz1(ritz1_bin, tmp_path, RULE.ACCEPTED[name])
    assert r.returncode != 0 and "Parse error" in r.stderr + r.stdout, (
        f"{name}: ritz1 parses this now; drop it from RITZ1_CANNOT_PARSE:\n"
        f"{r.stderr[-800:]}")


@pytest.mark.integration
def test_ritz1_diagnostic_words_match_ritz0(ritz1_bin, tmp_path):
    source, _ = RULE.REJECTED["tail_if_no_else"]
    r = _ritz1(ritz1_bin, tmp_path, source)
    assert ("unit.ritz:2:5: error: function 'f' declares a return type but can "
            "reach its end without producing a value\n") in r.stderr, r.stderr[-800:]


@pytest.mark.integration
@pytest.mark.parametrize("name", ["tail_if_no_else", "tail_method_call_to_a_procedure"])
def test_ritz1_reports_a_gap_once(ritz1_bin, tmp_path, name):
    """The check runs before and after the body; one gap is one diagnostic."""
    r = _ritz1(ritz1_bin, tmp_path, RULE.REJECTED[name][0])
    assert r.stderr.count(RULE.MESSAGE) == 1, r.stderr[-800:]


@pytest.mark.integration
def test_ritz1_rejection_writes_no_output(ritz1_bin, tmp_path):
    """A diagnostic that still leaves a .ll behind lets a build link it anyway."""
    source, _ = RULE.REJECTED["tail_if_no_else"]
    assert _ritz1(ritz1_bin, tmp_path, source).returncode != 0
    assert not (tmp_path / "unit.ll").exists()


_PROC = "fn g(n: i64)\n    var i: i64 = n\n"

# name -> (source, line). ritz0 is checked first, so a wrong case fails as one.
RITZ1_EXTRA_REJECTED = {
    # `true` and `1` share an int literal in ritz1.
    "while_one_is_not_while_true": (
        "fn f(n: i64) -> i64\n"
        "    while 1\n"
        "        if n > 0\n"
        "            return 1\n", 2),
    "while_not_false_is_not_while_true": (
        "fn f(n: i64) -> i64\n"
        "    while !false\n"
        "        return 1\n", 2),
    # `pass` and `0` share an int literal in ritz1.
    "tail_pass": (
        "fn f(n: i64) -> i64\n"
        "    pass\n", 2),
    "pass_in_an_inline_if": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0 then pass else 2\n", 2),
    # A `break` reached through an expression still leaves the loop.
    "break_in_a_let_match_arm": (
        "fn f(n: i64) -> i64\n"
        "    while true\n"
        "        let x: i64 = match n\n"
        "            0 =>\n"
        "                break\n"
        "            _ => 1\n", 2),
    "break_in_a_returned_match_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        return match n\n"
        "            0 =>\n"
        "                break\n"
        "            _ => 1\n", 2),
    "break_in_an_if_arm_of_a_let": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        let x: i64 = if n > 0\n"
        "            break\n"
        "        else\n"
        "            2\n", 2),
    "break_in_a_nested_if_inside_a_match_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        match n\n"
        "            0 =>\n"
        "                if n > 1\n"
        "                    break\n"
        "            _ => pass\n", 2),
    "break_in_an_arm_of_an_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        let x: i64 = match n\n"
        "            0 => match n\n"
        "                1 =>\n"
        "                    break\n"
        "                _ => 2\n"
        "            _ => 1\n", 2),
    "break_in_a_let_inside_a_block_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        let x: i64 = match n\n"
        "            0 =>\n"
        "                let y: i64 = match n\n"
        "                    1 =>\n"
        "                        break\n"
        "                    _ => 2\n"
        "                y\n"
        "            _ => 1\n", 2),
    "break_in_an_inline_if_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        let x: i64 = if n > 1 then match n\n"
        "            0 =>\n"
        "                break\n"
        "            _ => 1\n"
        "        else 2\n", 2),
    "break_in_an_else_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        if n > 0\n"
        "            return 1\n"
        "        else\n"
        "            break\n", 2),
    "break_in_an_inline_if_statement": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        if n > 0 then match n\n"
        "            0 =>\n"
        "                break\n"
        "            _ => 1\n"
        "        else 2\n"
        "        return 3\n", 2),
    "guard_at_the_end_of_a_block_arm": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 =>\n"
        "            var a: i64 = 1\n"
        "            return a\n"
        "        _ =>\n"
        "            if n > 1\n"
        "                return 2\n", 7),
    "tail_call_to_an_extern_procedure": (
        "extern fn g(n: i64)\n"
        "fn f(n: i64) -> i64\n"
        "    g(n)\n", 3),
    "tail_call_to_a_generic_procedure": (
        "fn g<T>(n: T)\n"
        "    var i: T = n\n"
        "fn f(n: i64) -> i64\n"
        "    g<i64>(n)\n"
        "fn main() -> i32\n"
        "    return f(1) as i32\n", 4),
    "parenthesised_tail_call_to_a_procedure": (
        _PROC + "fn f(n: i64) -> i64\n"
        "    (g(n))\n", 4),
    "procedure_call_in_an_if_arm": (
        _PROC + "fn f(n: i64) -> i64\n"
        "    if n > 0\n"
        "        g(n)\n"
        "    else\n"
        "        1\n", 5),
    "procedure_call_in_a_match_arm": (
        _PROC + "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => g(n)\n"
        "        _ => 1\n", 5),
    "bool_return": (
        "fn f(n: i64) -> bool\n"
        "    if n > 0\n"
        "        return true\n", 2),
    "struct_return": (
        "struct S\n"
        "    v: i64\n"
        "fn f(n: i64) -> S\n"
        "    if n > 0\n"
        "        return S { v: 1 }\n", 4),
}

RITZ1_EXTRA_ACCEPTED = {
    # A literal 0 in the place a `pass` would be rejected.
    "zero_arm_is_a_value": (
        "fn f(c: bool) -> i32\n"
        "    if c\n"
        "        0\n"
        "    else\n"
        "        7\n"),
    "zero_match_arm_is_a_value": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => 0\n"
        "        _ => 1\n"),
    "zero_tail_is_a_value": (
        "fn f(n: i64) -> i64\n"
        "    0\n"),
    # Dead code after a `return` in an arm does not need a value either.
    "procedure_call_after_a_return_in_a_block_arm": (
        _PROC + "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 =>\n"
        "            return 1\n"
        "            g(n)\n"
        "        _ => 2\n"),
    "dead_code_after_a_match_with_a_match_arm": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => match n\n"
        "            1 => return 1\n"
        "            _ => return 2\n"
        "        _ => return 3\n"
        "    var z: i64 = n\n"),
    # A nameless callee is not an identifier, so ritz0 does not judge it even
    # though ritz1 knows its signature.
    "tail_call_through_a_fn_field": (
        _PROC + "struct T\n"
        "    f: fn(i64)\n"
        "fn f(t: T, n: i64) -> i64\n"
        "    (t.f)(n)\n"),
    "tail_call_through_a_fn_array": (
        _PROC + "fn f(n: i64) -> i64\n"
        "    var fs: [1]fn(i64)\n"
        "    fs[0] = g\n"
        "    fs[0](n)\n"),
    "inline_if": (
        "fn f(n: i64) -> i64\n"
        "    if n > 0 then 1 else 2\n"),
    "break_belongs_to_an_inner_for": (
        "fn f(n: i64) -> i64\n"
        "    while true\n"
        "        for i in 0..n\n"
        "            break\n"
        "        return 1\n"),
    "break_belongs_to_an_inner_loop_in_a_match_arm": (
        "fn f(n: i64) -> i64\n"
        "    loop\n"
        "        match n\n"
        "            0 =>\n"
        "                loop\n"
        "                    break\n"
        "            _ => return 1\n"),
    # ritz0 walks the bodies it instantiates, and so does ritz1.
    "generic_that_is_never_instantiated": (
        "fn g<T>(n: T, c: i64) -> T\n"
        "    if c > 0\n"
        "        return n\n"
        "fn main() -> i32\n"
        "    return 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_EXTRA_REJECTED))
def test_ritz1_extra_shapes_rejected_by_both(ritz1_bin, tmp_path, name):
    source, line = RITZ1_EXTRA_REJECTED[name]
    rc, output = _ritz0(tmp_path, source)
    assert rc != 0 and RULE.MESSAGE in output, (
        f"{name}: ritz0 is the oracle and did not reject it -- fix the case:\n"
        f"{output[-800:]}")
    assert f"oracle.ritz:{line}:" in output, f"{name}: fix the line:\n{output[-800:]}"
    _assert_rejected(_ritz1(ritz1_bin, tmp_path, source), name, line)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_EXTRA_ACCEPTED))
def test_ritz1_extra_shapes_accepted_by_both(ritz1_bin, tmp_path, name):
    source = RITZ1_EXTRA_ACCEPTED[name]
    rc, output = _ritz0(tmp_path, source)
    assert rc == 0, f"{name}: ritz0 is the oracle and rejected it:\n{output[-800:]}"
    _assert_accepted(_ritz1(ritz1_bin, tmp_path, source), name, tmp_path)


# Verdict only: ritz1 accepts these, and the IR it writes is not this ticket's.
RITZ1_EXTRA_ACCEPTED_VERDICT_ONLY = {
    # ritz1 writes a second `ret` into the block, which clang tolerates.
    "dead_code_after_a_return": (
        "fn f(n: i64) -> i64\n"
        "    return 1\n"
        "    return 2\n"),
    # AGAST #2246: `-> void` is not a procedure to ritz0's `_is_void_call`.
    # ritz1's IR for these was already invalid (`ret i64 %.0`) before #2236.
    "tail_call_to_a_fn_spelled_void": (
        "fn g(n: i64) -> void\n"
        "    var i: i64 = n\n"
        "fn f(n: i64) -> i64\n"
        "    g(n)\n"),
    "tail_method_call_to_a_method_spelled_void": (
        "struct B\n"
        "    v: i64\n"
        "impl B\n"
        "    fn p(self) -> void\n"
        "        var i: i64 = 1\n"
        "fn f(b: B) -> i64\n"
        "    b.p()\n"),
    # The `-> void` mark has to reach the clone the call resolves to.
    "tail_call_to_a_generic_spelled_void": (
        "fn g<T>(n: T) -> void\n"
        "    var i: T = n\n"
        "fn f(n: i64) -> i64\n"
        "    g<i64>(n)\n"
        "fn main() -> i32\n"
        "    return 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_EXTRA_ACCEPTED_VERDICT_ONLY))
def test_ritz1_extra_verdicts_accepted_by_both(ritz1_bin, tmp_path, name):
    source = RITZ1_EXTRA_ACCEPTED_VERDICT_ONLY[name]
    rc, output = _ritz0(tmp_path, source)
    assert rc == 0, f"{name}: ritz0 is the oracle and rejected it:\n{output[-800:]}"
    r = _ritz1(ritz1_bin, tmp_path, source)
    assert r.returncode == 0, f"{name}: ritz1 rejected it:\n{r.stderr[-1500:]}"


@pytest.mark.integration
def test_pass_arm_inside_a_generic_keeps_its_line(ritz1_bin, tmp_path):
    """A clone's arms must keep the span of the `pass` the diagnostic names."""
    source = ("fn f<T>(n: T, c: i64) -> T\n"
              "    match c\n"
              "        0 => return n\n"
              "        _ => pass\n"
              "fn main() -> i32\n"
              "    return f<i32>(1, 1)\n")
    rc, output = _ritz0(tmp_path, source)
    assert rc != 0 and "oracle.ritz:4:" in output, output[-800:]
    _assert_rejected(_ritz1(ritz1_bin, tmp_path, source), "generic_pass_arm", 4)


@pytest.mark.integration
def test_a_generic_from_another_file_is_blamed_on_that_file(ritz1_bin, tmp_path):
    (tmp_path / "lib.ritz").write_text(
        "pub fn h<T>(n: T, c: i64) -> T\n"
        "    if c > 0\n"
        "        return n\n")
    r = _ritz1(ritz1_bin, tmp_path,
               "import lib\n"
               "fn main() -> i32\n"
               "    return h<i32>(1, 1)\n")
    assert r.returncode != 0 and RULE.MESSAGE in r.stderr, r.stderr[-1500:]
    assert "lib.ritz:2:" in r.stderr, r.stderr[-1500:]


# Ends that never arrive still need a terminator on the dead block after them,
# at every return shape the emitter treats differently: narrow ints, bool, a
# named struct, and one big enough to go through sret.
DIVERGING_TAILS = """\
struct Small
    v: i64

struct Large
    a: [64]i64
    d: i64

fn wi(n: i64) -> i32
    loop
        if n > 0
            return 1

fn wb(n: i64) -> bool
    while true
        if n > 0
            return true

fn wu(n: i64) -> u8
    if n > 0
        return 3
    else
        return 4

fn ws(n: i64) -> Small
    if n > 0
        return Small { v: n }
    else
        return Small { v: 0 }

fn wl(n: i64) -> Large
    var l: Large
    l.d = n
    loop
        return l

pub fn main() -> i32
    let s: Small = ws(5)
    let l: Large = wl(10)
    var r: i64 = wi(1) as i64 + wu(1) as i64 + s.v + l.d
    if wb(1)
        r = r + 20
    return r as i32
"""

# AGAST #2247: ritz0 writes `ret i32 0` into the dead merge block of a
# multi-field struct return, which clang refuses, so this shape has no oracle
# and ritz1 is pinned to its own value.
STRUCT_IF_ELSE_RETURNS = """\
struct Pair
    a: i64
    b: i64

fn wp(n: i64) -> Pair
    if n > 0
        return Pair { a: n, b: 2 }
    else
        return Pair { a: 0, b: 0 }

pub fn main() -> i32
    let p: Pair = wp(40)
    return (p.a + p.b) as i32
"""


@pytest.mark.integration
def test_diverging_tails_run_the_same_on_both(ritz1_bin, tmp_path):
    expected = _run("ritz0", tmp_path, "diverging", DIVERGING_TAILS)
    got = _run("ritz1", tmp_path, "diverging", DIVERGING_TAILS)
    shape = _block_shape_errors((tmp_path / "diverging_ritz1.ll").read_text())
    assert not shape, "malformed blocks in ritz1 IR:\n" + "\n".join(shape)
    assert got == expected == 39, f"ritz1 exit {got}, ritz0 exit {expected}"


@pytest.mark.integration
def test_struct_return_from_every_arm_of_an_if_else(ritz1_bin, tmp_path):
    got = _run("ritz1", tmp_path, "struct_arms", STRUCT_IF_ELSE_RETURNS)
    shape = _block_shape_errors((tmp_path / "struct_arms_ritz1.ll").read_text())
    assert not shape, "malformed blocks in ritz1 IR:\n" + "\n".join(shape)
    assert got == 42, f"ritz1 exit {got}"
