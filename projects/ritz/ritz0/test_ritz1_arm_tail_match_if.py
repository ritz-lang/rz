#!/usr/bin/env python3
"""A block's tail `match` or `if`/`else` is the block's value (AGAST #2429).

    match o
        Some(v) =>
            match v
                5 => 7
                _ => 3
        _ => 2

ritz1 gave 0 here, silently; ritz0 gives 7.  The grammar parses a nested
`match` or `if` at the end of a block as a statement (STMT_MATCH / STMT_IF), and
match_arm_set_block only took a bare expression statement as the arm's value,
so the arm was valueless and fed the outer phi a zero.  An if-expression's arms
(if_arm_from_block) already turned a trailing `if`/`else` statement into its
value, but not a trailing `match`.

Each program exits 7 when its value survives.  Every shape runs on ritz0,
ritz1 and ritz1_selfhosted, which must agree.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_MAIN = "fn main() -> i32\n"
_O = "    let o: Option<i64> = Some(5)\n"
_INNER_MATCH = ("            match v\n"
                "                5 => 7\n"
                "                _ => 3\n")
_INNER_IF = ("            if v == 5\n"
             "                7\n"
             "            else\n"
             "                3\n")


def _outer(tail, head="    match o\n"):
    """`match o` whose `Some(v)` arm is a block ending in `tail`."""
    return head + "        Some(v) =>\n" + tail + "        _ => 2\n"


# A block-bodied arm whose tail is a match or an if, in each position.
SHAPES = {
    # The ticket's two.
    "match_tail": _MAIN + _O + _outer(_INNER_MATCH),
    "if_tail": _MAIN + _O + _outer(_INNER_IF),
    "else_if_tail": _MAIN + _O + _outer(
        "            if v == 1\n                3\n"
        "            else if v == 5\n                7\n"
        "            else\n                4\n"),
    "after_statements": _MAIN + _O + _outer(
        "            let w: i64 = v + 1\n"
        "            match w\n                6 => 7\n                _ => 3\n"),
    "not_the_first_arm": _MAIN + "    let o: Option<i64> = None\n    let x: i64 = 5\n"
    "    match o\n        Some(v) => 2\n        _ =>\n"
    "            if x == 5\n                7\n            else\n                3\n",
    # Two levels deep.
    "match_in_match_in_match": _MAIN + _O + _outer(
        "            match v\n                5 =>\n"
        "                    match v + 1\n                        6 => 7\n"
        "                        _ => 4\n                _ => 3\n"),
    "if_in_match_in_match": _MAIN + _O + _outer(
        "            match v\n                5 =>\n"
        "                    if v > 4\n                        7\n"
        "                    else\n                        4\n                _ => 3\n"),
    "match_in_if_in_match": _MAIN + _O + _outer(
        "            if v > 4\n                match v\n                    5 => 7\n"
        "                    _ => 4\n            else\n                3\n"),
    # An if-expression's block whose tail is a match.
    "match_in_if_expression": _MAIN + "    let x: i64 = 5\n    let r: i64 = if x > 4\n"
    "        match x\n            5 => 7\n            _ => 4\n    else\n        3\n"
    "    r as i32\n",
    # The outer match as a `let` initialiser.
    "typed_let_match_tail": _MAIN + _O + _outer(_INNER_MATCH, "    let r: i64 = match o\n")
    + "    r as i32\n",
    "untyped_let_if_tail": _MAIN + _O + _outer(_INNER_IF, "    let r = match o\n")
    + "    r as i32\n",
    # The outer match as a fn's tail.
    "fn_tail_match_tail": "fn f(o: Option<i64>) -> i64\n" + _outer(_INNER_MATCH)
    + _MAIN + _O + "    f(o) as i32\n",
    "fn_tail_if_tail": "fn f(o: Option<i64>) -> i64\n" + _outer(_INNER_IF)
    + _MAIN + _O + "    f(o) as i32\n",
    # The phi's type comes from the nested tail.
    "struct_tail": "struct Pair\n    a: i32\n    b: i32\n" + _MAIN + _O + _outer(
        "            match v\n                5 => Pair { a: 3, b: 4 }\n"
        "                _ => Pair { a: 1, b: 1 }\n", "    let p: Pair = match o\n")
    .replace("_ => 2", "_ => Pair { a: 0, b: 2 }") + "    p.a + p.b\n",
    "float_tail": _MAIN + _O + _outer(
        "            if v == 5\n                3.5\n            else\n                1.0\n",
        "    let f: f64 = match o\n").replace("_ => 2", "_ => 0.5")
    + "    (f * 2.0) as i32\n",
    # The statement forms, which already ran, still do.
    "statement_form": _MAIN + _O + "    var r: i64 = 0\n" + _outer(
        "            match v\n                5 =>\n                    r = 7\n"
        "                _ =>\n                    r = 3\n").replace("_ => 2", "_ =>\n            r = 2")
    + "    r as i32\n",
    "void_calls_as_a_statement": "var G: i32 = 0\nfn say(n: i64)\n    G = n as i32\n"
    + _MAIN + "    let o: Option<i64> = Some(7)\n" + _outer(
        "            match v\n                7 => say(v)\n                _ => say(3)\n"
    ).replace("_ => 2", "_ => say(2)") + "    G\n",
    "else_less_if_as_a_statement": _MAIN + _O + "    var r: i64 = 0\n" + _outer(
        "            if v == 5\n                r = 7\n").replace("_ => 2", "_ =>\n            r = 2")
    + "    r as i32\n",
}


def _compile_and_run(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    exe = tmp_path / "unit"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
        link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
        link = ["clang", "-w", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"]
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]
    linked = fast_link.clang(link, capture_output=True, text=True)
    assert linked.returncode == 0, linked.stderr[-1500:]
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_a_blocks_tail_match_or_if_is_its_value(request, tmp_path, compiler, name):
    assert _compile_and_run(request, compiler, tmp_path, SHAPES[name]) == 7, f"{compiler}, {name}"


# A tail `match` whose arms call fns that return nothing has no value: in a match
# used as a value that is the located error a `=> match` arm gets (#2046), not a 0.
VALUELESS = ("fn say(n: i64)\n    pass\n" + _MAIN + _O + _outer(
    "            match v\n                5 => say(v)\n                _ => say(3)\n",
    "    let r: i64 = match o\n") + "    r as i32\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_a_valueless_tail_match_is_refused_where_a_value_is_wanted(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    src = tmp_path / "unit.ritz"
    src.write_text(VALUELESS)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out[-800:]
    assert "unit.ritz:8:22: error: this arm calls a fn that returns nothing" in out, out[-800:]
    assert not ll.exists()
