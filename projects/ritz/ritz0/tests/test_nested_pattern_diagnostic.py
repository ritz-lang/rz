#!/usr/bin/env python3
"""A variant's payload pattern is a name or `_` (LARB R76, AGAST #4001; §8.2).

`Ok(Simple(x))` and `Some(0)` are no Ritz patterns: the arm is chosen by the
variant's tag alone, so anything inside it that would test the payload is
refused, on all three compilers, with one message at the inner pattern:

    a variant's payload pattern is a name or `_`: match the inner value in its own `match`

History: ritz0 once let the nested pattern bind nothing, and the arm failed
with the red herring `Unknown identifier: x` (angelo's font.ritz, #1321); a
literal was dropped and `Some(0)` took every `Some` (#2350). ritz1's grammar
takes only a name there, so its parse fails at the inner pattern and the
parse recovery gives that failure ritz0's words, as it does for R52's "a type
isn't a pattern". A type there is R52's own error: test_variant_payload_refused.py.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

MESSAGE = ("a variant's payload pattern is a name or `_`: "
           "match the inner value in its own `match`")


def _opt(ty, pattern, arg):
    """`f(Some(arg))`, with `pattern` on line 3 of this text, payload at column 14."""
    return (f"fn f(o: Option<{ty}>) -> i32\n    match o\n        {pattern} => 1\n"
            f"        _ => 2\nfn main() -> i32\n    f(Some({arg}))\n")


# The reduced font.ritz `glyph_outline_with_depth` shape: matching through a
# Result into an inner enum in one pattern. `Ok(Empty)` in place of `Ok(_)`
# would be refused first, as a payload named like a variant (LARB R12).
NESTED_USER_ENUM = """\
enum Shape
    Simple(i32)
    Empty

enum Res
    Ok(Shape)
    Err(i32)

fn get() -> Res
    return Res.Ok(Shape.Simple(3))

fn main() -> i32
    match get()
        Ok(Simple(x)) => x
        Ok(_) => 1
        Err(e) => e
"""

# name -> (source, line, col): line and column of the inner pattern.
ROWS = {
    "nested_user_enum": (NESTED_USER_ENUM, 14, 12),
    "nested_option": (_opt("Option<i32>", "Some(Some(x))", "None"), 3, 14),
    "nested_wildcard": (_opt("Option<i32>", "Some(Some(_))", "None"), 3, 14),
    "nested_in_a_statement_match": (
        ("fn main() -> i32\n    var r: i32 = 2\n    let o: Option<Option<i32>> = None\n"
         "    match o\n        Some(Some(v)) => r = v\n        _ => pass\n    r\n"), 5, 14),
    "literal_int": (_opt("i32", "Some(0)", "5"), 3, 14),
    "literal_bool": (_opt("bool", "Some(true)", "false"), 3, 14),
    "literal_string": (_opt("StrView", 'Some("a")', '"b"'), 3, 14),
    "literal_in_result_err": (
        ("fn f(r: Result<i32, i32>) -> i32\n    match r\n        Err(7) => 1\n"
         "        _ => 2\nfn main() -> i32\n    f(Err(5))\n"), 3, 13),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll), "--no-runtime"], cwd=tmp_path)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300, check=False)
    return proc, ll


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_a_payload_pattern_is_a_name_or_wildcard(request, tmp_path, compiler, name):
    """One message, at the inner pattern, and no IR."""
    source, line, col = ROWS[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert "Unknown identifier" not in out, f"{compiler}, {name}: the binder's red herring:\n{out}"
    sep = "" if compiler == "ritz0" else "error: "
    hits = re.findall(rf"unit\.ritz:{line}:{col}: {sep}{re.escape(MESSAGE)}$", out, re.MULTILINE)
    assert len(hits) == 1, f"{compiler}, {name}: want one {MESSAGE!r} at {line}:{col}:\n{out[-1500:]}"
    assert out.count(MESSAGE) == 1, f"{compiler}, {name}: reported more than once:\n{out}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
