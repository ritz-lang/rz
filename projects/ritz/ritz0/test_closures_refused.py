"""LARB R56 / AGAST #3470: closures are gone; ritz0 refuses them at the parse.

LANGUAGE_SPEC §5.6.  `|x| e`, `|| e`, `|x: T| e` and an anonymous
`fn(…) e` used as an expression are each a located parse error at the `|`
or `fn` that opens them.  ritz0 used to lower them to anonymous fns, and a
capturing one to a per-instance thunk over a 16-slot global environment
ring (the 17th live instance overwrote the 1st).  That lowering is deleted.
Write a named fn and pass it by name (§5.5); for state, a struct holding
a fn field (R41's `h.f(x)`), as examples/58_closures does.

The rows replace test_closure_param_type.py (#2230: each typed-param shape
was a separate parser path), test_closure_needs_expected_type.py (#3302)
and test_closure_error_state.py (#2276).  ritz1's refusal is #3471.
"""

import os
from pathlib import Path

import pytest
from parser import parse, ParseError
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

MSG = "closures aren't supported: write a named fn and pass it by name (§5.5)"

_LET = "fn main() -> i32\n    let g: fn(i32) -> i32 = {}\n    0\n"

# name -> (source, line, column) of the `|` or `fn` that opens the closure.
REFUSED = {
    "pipe": (_LET.format("|x| x * 2"), 2, 29),
    "pipe_no_params": ("fn main() -> i32\n    let g: fn() -> i32 = || 42\n    0\n", 2, 26),
    "pipe_typed_param": (_LET.format("|x: i32| x + 1"), 2, 29),
    # #2230's hardest shape: an undelimited fn type as the param's type.
    "pipe_fn_typed_param": (_LET.format("|f: fn(i32) -> i32| f(1) + 1"), 2, 29),
    "anon_fn": (_LET.format("fn(x: i32) -> i32 x * 2"), 2, 29),
    "anon_fn_no_ret": ("fn main() -> i32\n    let g: fn() = fn() 0\n    0\n", 2, 19),
    # As an argument: the closure is refused where it stands, not at the call.
    "pipe_as_arg": ("fn apply(f: fn(i32) -> i32, x: i32) -> i32\n    f(x)\n"
                    "fn main() -> i32\n    apply(|x| x + 1, 2)\n", 4, 11),
    # A closure as a fn's tail value (58_closures' old `make_adder`).
    "pipe_as_tail": ("fn make() -> fn(i32) -> i32\n    |x| x + 1\n", 2, 5),
    # The #3302 shape: no expected type.  Refused at the parse all the same.
    "pipe_untyped_let": ("fn main() -> i32\n    let g = |x| x + 1\n    0\n", 2, 13),
}

# Not closures: `|` and `||` as binary operators, `fn(...)` as a type.
KEPT = {
    "bitwise_or": "fn f(a: i32, b: i32) -> i32\n    a | b\n",
    "logical_or": "fn f(a: bool, b: bool) -> bool\n    a || b\n",
    "fn_type_annotation": ("fn dbl(x: i32) -> i32\n    x * 2\n"
                           "fn main() -> i32\n    let g: fn(i32) -> i32 = dbl\n    g(1)\n"),
    "fn_type_alias": "type F = fn(i32) -> i32\n",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses_closure_at_its_opener(name):
    src, line, column = REFUSED[name]
    with pytest.raises(ParseError) as info:
        parse(src)
    assert info.value.message == MSG
    assert (info.value.span.line, info.value.span.column) == (line, column)


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz0_keeps_non_closures(name):
    parse(KEPT[name])


@pytest.mark.integration
def test_ritz0_cli_reports_closure_at_file_line_col(tmp_path):
    """The driver prints the located message and fails: no traceback, no .ll."""
    src = tmp_path / "closure.ritz"
    src.write_text(REFUSED["pipe"][0])
    ll = tmp_path / "closure.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert f"closure.ritz:2:29" in out and MSG in out, out
    assert "Traceback" not in out, out
    assert not ll.exists()
