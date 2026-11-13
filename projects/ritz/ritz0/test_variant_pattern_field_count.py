"""A variant pattern lists as many fields as its variant has (AGAST #2408).

ritz0's `_emit_enum_match` zipped a pattern's fields against the variant's, so a
mismatch was cut to the shorter of the two:

    Two(a) => a      # on Two(i32, i32): compiled, and covered Two
    Some(a, b) => a  # KeyError: 'b', no location
    Z(a) => 3        # on a bare Z: KeyError: 'a', no location

ritz1 compiled `Z(a)` and `None(k)` on a bare variant, binding nothing. Each is now
a located error at the pattern, naming both counts, on every compiler that can
read the program. It comes before coverage, so `Two(a)` covers nothing.

ritz1's grammar takes one name in a variant pattern and one type in a tuple
variant (#1295), so the only mismatch it can read is a name on a variant with none, or on
a struct variant with more than one field. The rest are ritz0's rows alone.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
ALL = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ALL[1:]

_P = "enum P\n    Two(i32, i32)\n    One(i32)\n    Z\n"
_Q = "enum Q\n    One(i32)\n    Z\n"
_S = "enum S\n    V\n        x: i32\n        y: i32\n    W\n"


def _on(ty, arms, arg):
    """`f(arg)` over `ty`; the first of `arms` is on line 3 of this text."""
    body = "".join(f"        {arm}\n" for arm in arms)
    return f"fn f(e: {ty}) -> i32\n    match e\n{body}fn main() -> i32\n    f({arg})\n"


def _lines(prefix):
    return prefix.count("\n")


# name -> (source, line, variant, has, lists, compilers).  Every pattern starts at
# column 9.  The count is the only error said, ahead of any missing arm.
ROWS = {
    # Fewer: compiled, read the first field, and covered Two.
    "fewer": (_P + _on("P", ["Two(a) => a", "One(x) => 2", "Z => 3"], "P.Two(1, 5)"),
              _lines(_P) + 3, "Two", 2, 1, ["ritz0"]),
    "more": (_on("Option<i32>", ["Some(a, b) => a", "None => 2"], "Some(1)"),
             3, "Some", 1, 2, ["ritz0"]),
    # A literal in a surplus field is the count's error, not #2350's.
    "more_with_a_literal": (_on("Option<i32>", ["Some(a, 0) => a", "None => 2"], "Some(1)"),
                            3, "Some", 1, 2, ["ritz0"]),
    "a_literal_on_a_bare_variant": (_P + _on("P", ["Z(0) => 1", "_ => 2"], "P.Z"),
                                    _lines(_P) + 3, "Z", 0, 1, ["ritz0"]),
    "on_a_bare_variant": (_Q + _on("Q", ["One(x) => 2", "Z(a) => 3"], "Q.Z"),
                          _lines(_Q) + 4, "Z", 0, 1, ALL),
    "qualified_on_a_bare_variant": (_Q + _on("Q", ["One(x) => 2", "Q.Z(a) => 3"], "Q.Z"),
                                    _lines(_Q) + 4, "Z", 0, 1, ALL),
    "on_none": (_on("Option<i32>", ["Some(x) => 2", "None(k) => 3"], "None"),
                4, "None", 0, 1, ALL),
    "fewer_on_a_struct_variant": (_S + _on("S", ["V(a) => a", "W => 3"], "S.W"),
                                  _lines(_S) + 3, "V", 2, 1, ALL),
    # An arm missing too: the count is said, and coverage isn't.
    "fewer_with_an_arm_missing": (_P + _on("P", ["Two(a) => a", "One(x) => 2"], "P.Z"),
                                  _lines(_P) + 3, "Two", 2, 1, ["ritz0"]),
    "on_a_bare_variant_with_an_arm_missing": (_Q + _on("Q", ["Z(a) => 3"], "Q.Z"),
                                              _lines(_Q) + 3, "Z", 0, 1, ALL),
}


def _fields(n):
    return f"{n} field" + ("" if n == 1 else "s")


def _message(variant, has, lists):
    return f"variant '{variant}' has {_fields(has)}, but this pattern lists {lists}"


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    args = [str(src), "-o", str(ll)]
    if compiler == "ritz0":
        return run_ritz0(args, cwd=tmp_path, env=env, timeout=300), ll
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary)] + args, cwd=tmp_path, env=env, capture_output=True, check=False,
                          text=True, timeout=300), ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", [
    pytest.param(c, n, id=f"{c}-{n}") for n, row in sorted(ROWS.items()) for c in row[5]])
def test_a_variant_pattern_lists_every_field(request, tmp_path, compiler, name):
    source, line, variant, has, lists, _ = ROWS[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    sep = "" if compiler == "ritz0" else "error: "
    message = _message(variant, has, lists)
    hits = re.findall(rf"unit\.ritz:{line}:9: {sep}{re.escape(message)}$", out, re.MULTILINE)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:9:\n{out[-1500:]}"
    assert "Traceback" not in out and "non-exhaustive" not in out, out[-1500:]
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
def test_ritz0_still_binds_every_field(tmp_path, request):
    """The count is the variant's: all of them bind, and `_` takes one."""
    source = _P + _on("P", ["Two(_, b) => b", "One(x) => 2", "Z => 3"], "P.Two(1, 5)")
    proc, ll = _compile(request, "ritz0", tmp_path, source)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]
    exe = tmp_path / "unit"
    fast_link.clang(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)], timeout=60, check=False).returncode == 5


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_cannot_parse_a_second_field(request, tmp_path, compiler):
    """Goes red when ritz1 learns one, which must then count it as ritz0 does."""
    source = _on("Option<i32>", ["Some(a, b) => a", "None => 2"], "Some(1)")
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Parse error" in out, f"{compiler}:\n{out[-800:]}"
    assert not ll.exists()
