#!/usr/bin/env python3
"""A local can't reuse a name already bound in its fn (AGAST #2395, Aaron 2026-11-06,
extended 2026-11-08 on #2455; LANGUAGE_SPEC §4.3).

Shadowing had a different meaning on each compiler:

    fn g(b: i32) -> i32
        let r: i32 = 1
        if b > 0
            let r: i32 = 2
            r
        r

`g(1)*10 + g(0)` is 11 under block scope.  ritz1 gave 22, its inner `r` replacing
the outer for the rest of the fn; ritz0's emitter failed in clang ("Instruction
does not dominate all uses").  The ruling removes the question: a binding (`let`,
`var`, a param, a `for` variable, a tuple `let`'s names, a match arm's name, a
variant payload's name) that reuses a name still in scope at that point, in a
nested block or the same one, is a located error at the new name on all three
compilers.  `_` binds nothing, so it's exempt.  A name whose binding has gone out
of scope (a sibling block, an earlier arm, a finished loop) is free again.

The expected exit codes come from what each program says, not from a compiler.
Every row runs on ritz0, ritz1 and ritz1_selfhosted.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


def _message(name, line, col):
    return (f"a local can't reuse a name bound earlier in its fn: '{name}' "
            f"(at {line}:{col}) — rename the local")


# name -> (source, (line, col) of the reuse, (line, col) of the earlier binding, name)
REFUSED = {
    # Aaron's original ruling: a nested `let`/`var` over an enclosing one.
    "nested_let_in_if": (
        "fn g(b: i32) -> i32\n    let r: i32 = 1\n    if b > 0\n        let r: i32 = 2\n"
        "        return r\n    r\nfn main() -> i32\n    g(1) * 10 + g(0)\n", (4, 13), (2, 9), "r"),
    "nested_var_in_else": (
        "fn g(b: i32) -> i32\n    let r: i32 = 1\n    if b > 0\n        return 0\n    else\n"
        "        var r: i32 = 2\n        r = 3\n    r\nfn main() -> i32\n    g(0)\n",
        (6, 13), (2, 9), "r"),
    "nested_let_in_while": (
        "fn main() -> i32\n    var t: i32 = 0\n    while t < 3\n        let t: i32 = 9\n"
        "        break\n    t\n", (4, 13), (2, 9), "t"),
    "nested_let_in_loop": (
        "fn main() -> i32\n    let t: i32 = 0\n    loop\n        let t: i32 = 9\n"
        "        break\n    t\n", (4, 13), (2, 9), "t"),
    "nested_let_in_for_body": (
        "fn main() -> i32\n    let t: i32 = 0\n    for i in 0..3\n        let t: i32 = i\n"
        "    t\n", (4, 13), (2, 9), "t"),
    "nested_let_in_arm_body": (
        "fn f(o: Option<i32>) -> i32\n    let t: i32 = 0\n    match o\n        Some(v) =>\n"
        "            let t: i32 = v\n            t\n        _ => t\n"
        "fn main() -> i32\n    f(Some(5))\n", (5, 17), (2, 9), "t"),
    "nested_two_deep": (
        "fn main() -> i32\n    let t: i32 = 0\n    if t == 0\n        if t == 0\n"
        "            let t: i32 = 1\n    t\n", (5, 17), (2, 9), "t"),
    # #1756's first program: a `var` in a block over the fn's `let`.
    "issue_1756_block_var": (
        "fn main() -> i32\n    let v: i32 = 5\n    var t: i32 = 0\n    if t == 0\n"
        "        var v: i32 = 100\n        v = v + 1\n        t = v\n    return v + t\n",
        (5, 13), (2, 9), "v"),
    # Extended: the same block.
    "same_block_let_let": (
        "fn main() -> i32\n    let x: i32 = 1\n    let x: i32 = 2\n    x\n", (3, 9), (2, 9), "x"),
    "same_block_var_let": (
        "fn main() -> i32\n    var x: i32 = 1\n    let x: i32 = 2\n    x\n", (3, 9), (2, 9), "x"),
    "same_block_let_var": (
        "fn main() -> i32\n    let x: i32 = 1\n    var x: i32 = 2\n    x\n", (3, 9), (2, 9), "x"),
    "same_block_untyped": (
        "fn main() -> i32\n    let x = 1\n    let x = x + 1\n    x\n", (3, 9), (2, 9), "x"),
    "same_block_in_nested_block": (
        "fn main() -> i32\n    var t: i32 = 0\n    if t == 0\n        let y: i32 = 1\n"
        "        let y: i32 = 2\n        t = y\n    t\n", (5, 13), (4, 13), "y"),
    # Extended: a param.
    "let_over_param": (
        "fn g(a: i32) -> i32\n    let a: i32 = 3\n    a\nfn main() -> i32\n    g(1)\n",
        (2, 9), (1, 6), "a"),
    "var_over_param": (
        "fn g(a: i32) -> i32\n    var a: i32 = 3\n    a\nfn main() -> i32\n    g(1)\n",
        (2, 9), (1, 6), "a"),
    "nested_let_over_param": (
        "fn g(a: i32) -> i32\n    if a > 0\n        let a: i32 = 3\n        return a\n    a\n"
        "fn main() -> i32\n    g(1)\n", (3, 13), (1, 6), "a"),
    "param_over_param": (
        "fn g(a: i32, a: i32) -> i32\n    a\nfn main() -> i32\n    g(1, 2)\n",
        (1, 14), (1, 6), "a"),
    "method_let_over_param": (
        "struct T\n    v: i32\nimpl T\n    fn m(self, a: i32) -> i32\n        let a: i32 = 2\n"
        "        self.v + a\nfn main() -> i32\n    let t = T { v: 1 }\n    t.m(2)\n",
        (5, 13), (4, 16), "a"),
    "let_over_self": (
        "struct T\n    v: i32\nimpl T\n    fn m(self) -> i32\n        let self: i32 = 2\n"
        "        self\nfn main() -> i32\n    let t = T { v: 1 }\n    t.m()\n",
        (5, 13), (4, 10), "self"),
    # #2340's `shadowed_in_arm` (test_borrow_param_ref_slot.py), which ritz1 left
    # unjudged in ref_check.ritz: a `let` in an arm over a lent param.
    "let_in_arm_over_a_lent_param": (
        "struct C\n    x: i32\nvar G: C\nfn go(c:& C, k: i32) -> *C\n    if k == 0\n"
        "        let c: *C = @G\n        c\n    else\n        @c\n"
        "fn main() -> i32\n    var c: C = C { x: 9 }\n    go(@&c, 0).x\n", (6, 13), (4, 7), "c"),
    # Extended: a `for` variable.
    "for_over_local": (
        "fn main() -> i32\n    var x: i32 = 100\n    var s: i32 = 0\n    for x in 0..3\n"
        "        s = s + x\n    s + x\n", (4, 9), (2, 9), "x"),
    # #1756's second program.
    "issue_1756_for_over_var": (
        "fn main() -> i32\n    var x: i32 = 100\n    var arr: [3]i32 = [1, 2, 3]\n"
        "    var s: i32 = 0\n    for x in arr\n        s = s + x\n    return s + x\n",
        (5, 9), (2, 9), "x"),
    "for_over_param": (
        "fn g(i: i32) -> i32\n    var s: i32 = 0\n    for i in 0..3\n        s = s + i\n    s\n"
        "fn main() -> i32\n    g(1)\n", (3, 9), (1, 6), "i"),
    "nested_for_over_for": (
        "fn main() -> i32\n    var s: i32 = 0\n    for i in 0..3\n        for i in 0..2\n"
        "            s = s + i\n    s\n", (4, 13), (3, 9), "i"),
    "let_in_for_over_its_var": (
        "fn main() -> i32\n    var s: i32 = 0\n    for i in 0..3\n        let i: i32 = 1\n"
        "        s = s + i\n    s\n", (4, 13), (3, 9), "i"),
    # Extended: a payload, or an arm's own name.
    "payload_over_local": (
        "fn f(o: Option<i32>) -> i32\n    let v: i32 = 1\n    match o\n        Some(v) => v\n"
        "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", (4, 14), (2, 9), "v"),
    "payload_over_param": (
        "fn f(o: Option<i32>, v: i32) -> i32\n    match o\n        Some(v) => v\n"
        "        _ => 2\nfn main() -> i32\n    f(Some(5), 1)\n", (3, 14), (1, 22), "v"),
    "payload_over_outer_payload": (
        "fn f(o: Option<i32>, p: Option<i32>) -> i32\n    match o\n        Some(v) =>\n"
        "            match p\n                Some(v) => v\n                _ => 1\n"
        "        _ => 2\nfn main() -> i32\n    f(Some(5), Some(6))\n", (5, 22), (3, 14), "v"),
    "let_in_arm_over_payload": (
        "fn f(o: Option<i32>) -> i32\n    match o\n        Some(v) =>\n"
        "            let v: i32 = 3\n            v\n        _ => 2\n"
        "fn main() -> i32\n    f(Some(5))\n", (4, 17), (3, 14), "v"),
    "arm_name_over_local": (
        "fn f(x: i32) -> i32\n    let n: i32 = 1\n    match x\n        0 => 1\n        n => n\n"
        "fn main() -> i32\n    f(5)\n", (5, 9), (2, 9), "n"),
    # The tuple `let`'s names, each at its own place.
    "tuple_second_over_local": (
        "struct P\n    a: i32\n    b: i32\nfn p() -> P\n    P { a: 1, b: 2 }\n"
        "fn main() -> i32\n    let b: i32 = 0\n    let (a, b) = p()\n    a + b\n",
        (8, 13), (7, 9), "b"),
    "tuple_names_same": (
        "struct P\n    a: i32\n    b: i32\nfn p() -> P\n    P { a: 1, b: 2 }\n"
        "fn main() -> i32\n    let (a, a) = p()\n    a\n", (7, 13), (7, 10), "a"),
    # In an `if` expression's arm.
    "let_in_if_expression": (
        "fn g(b: i32) -> i32\n    let r: i32 = 1\n    let q: i32 = if b > 0\n"
        "        let r: i32 = 2\n        r\n    else\n        3\n    q + r\n"
        "fn main() -> i32\n    g(1)\n", (4, 13), (2, 9), "r"),
    # A generic fn is judged though nothing instantiates it.
    "generic_fn_never_called": (
        "fn g<T>(x: T) -> i32\n    let n: i32 = 3\n    let n: i32 = 4\n    n\n"
        "fn main() -> i32\n    0\n", (3, 9), (2, 9), "n"),
}


# name -> (source, exit code): each keeps running, on all three.
KEPT = {
    # A name out of scope is free: the other arm of an `if`.
    "sibling_if_arms": (
        "fn g(b: i32) -> i32\n    var s: i32 = 0\n    if b > 0\n        let t: i32 = 1\n        s = t\n"
        "    else\n        let t: i32 = 2\n        s = t\n    s\n"
        "fn main() -> i32\n    g(1) * 10 + g(0)\n", 12),
    # ...a block that has ended, then the same name in the fn's block.
    "after_the_block": (
        "fn g(b: i32) -> i32\n    var s: i32 = 0\n    if b > 0\n        let t: i32 = 4\n"
        "        s = t\n    let t: i32 = 7\n    s + t\n"
        "fn main() -> i32\n    g(1) * 10 + g(0)\n", 117),
    # ...a different type the second time.
    "after_the_block_other_type": (
        "fn g(b: i32) -> i64\n    var s: i64 = 0\n    if b > 0\n        let t: i32 = 4\n"
        "        s = t as i64\n    let t: i64 = 7\n    s + t\n"
        "fn main() -> i32\n    (g(1) * 10 + g(0)) as i32\n", 117),
    # ...each arm of a match.
    "each_arm_binds_v": (
        "fn f(r: Result<i32, i32>) -> i32\n    match r\n        Ok(v) => v\n        Err(v) => v + 1\n"
        "fn main() -> i32\n    f(Ok(5)) * 10 + f(Err(5))\n", 56),
    # ...two matches in a row.
    "two_matches_bind_v": (
        "fn f(o: Option<i32>, p: Option<i32>) -> i32\n    var s: i32 = 0\n    match o\n"
        "        Some(v) => s = s + v\n        _ => s = s\n    match p\n"
        "        Some(v) => s = s + v * 10\n        _ => s = s\n    s\n"
        "fn main() -> i32\n    f(Some(1), Some(2))\n", 21),
    # ...two loops in a row.
    "two_fors_bind_i": (
        "fn main() -> i32\n    var s: i32 = 0\n    for i in 0..3\n        s = s + i\n"
        "    for i in 0..4\n        s = s + i * 10\n    s\n", 63),
    # ...a loop's body, each time round.
    "let_in_a_loop_body": (
        "fn main() -> i32\n    var s: i32 = 0\n    for i in 0..3\n        let t: i32 = (i * 2) as i32\n"
        "        s = s + t\n    s\n", 6),
    # ...another fn's names.
    "other_fns_names": (
        "fn g(x: i32) -> i32\n    let y: i32 = x\n    y\n"
        "fn main() -> i32\n    let x: i32 = 2\n    let y: i32 = 3\n    g(x) + y\n", 5),
    # `_` binds nothing, so it can come twice.
    "wildcard_payload_twice": (
        "fn f(o: Option<i32>, p: Option<i32>) -> i32\n    match o\n        Some(_) =>\n"
        "            match p\n                Some(_) => 1\n                _ => 2\n"
        "        _ => 3\nfn main() -> i32\n    f(Some(1), None)\n", 2),
    "let_wildcard_twice": (
        "fn one() -> i32\n    1\nfn main() -> i32\n    let _ = one()\n    let _ = one()\n    2\n", 2),
    # A variant or const arm compares; it binds nothing.
    "arm_variant_compares": (
        "enum C\n    R\n    S\nfn f(c: C) -> i32\n    let k: i32 = 1\n    match c\n"
        "        R => k\n        S => 2\nfn main() -> i32\n    f(C.S)\n", 2),
    # Assignment isn't a binding.
    "assign_reuses_nothing": (
        "fn main() -> i32\n    var x: i32 = 1\n    if x == 1\n        x = 2\n    x\n", 2),
}


def _write(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return src, tmp_path / "unit.ll"


def _compile(request, compiler, tmp_path, source):
    src, ll = _write(tmp_path, source)
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _located(compiler, out, line, col, message):
    """ritz1 says `error:` after the place; ritz0 doesn't."""
    sep = "" if compiler == "ritz0" else "error: "
    return re.findall(rf"unit\.ritz:{line}:{col}: {sep}{re.escape(message)}$", out, re.M)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_local_cant_reuse_a_name_in_scope(request, tmp_path, compiler, name):
    source, (line, col), (bline, bcol), shown = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    message = _message(shown, bline, bcol)
    hits = _located(compiler, out, line, col, message)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(KEPT))
def test_a_name_out_of_scope_is_free(request, tmp_path, compiler, name):
    source, code = KEPT[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(3, str(RITZ_START))
    subprocess.run(link, check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_reuse_is_reported(request, tmp_path, compiler):
    """Two in one fn: both named, so a fix can be done at once."""
    source = ("fn main() -> i32\n    let x: i32 = 1\n    let y: i32 = 2\n    let x: i32 = 3\n"
              "    let y: i32 = 4\n    x + y\n")
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert _located(compiler, out, 4, 9, _message("x", 2, 9)), out[-1500:]
    assert _located(compiler, out, 5, 9, _message("y", 3, 9)), out[-1500:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_module_value_name_is_r12s_error_alone(request, tmp_path, compiler):
    """`let K` twice over a const: R12 names each; neither is also called a reuse."""
    source = "const K: i32 = 7\nfn main() -> i32\n    let K: i32 = 1\n    let K: i32 = 2\n    0\n"
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "can't reuse" not in out, out[-1500:]
    r12 = "a local can't take the name of a const: 'K' — rename the local"
    assert _located(compiler, out, 3, 9, r12) and _located(compiler, out, 4, 9, r12), out[-1500:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_reuse_comes_before_match_coverage(request, tmp_path, compiler):
    """The first error agrees: a match that also misses an arm names the reuse first."""
    source = ("fn f(o: Option<i32>) -> i32\n    let v: i32 = 1\n    match o\n"
              "        Some(v) => v\nfn main() -> i32\n    f(Some(5))\n")
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    first = next(line for line in out.splitlines() if "unit.ritz:" in line)
    assert _message("v", 2, 9) in first, out[-1500:]
