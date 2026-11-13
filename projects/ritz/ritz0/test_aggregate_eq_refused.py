#!/usr/bin/env python3
"""`==` / `!=` on a payload enum or a struct is ritz0's located refusal on ritz1 (AGAST #2510).

#2454 refused `==` on an Option or a Result.  Two neighbours were left:

1. a user enum whose variants carry a payload was compared by its tag (#1660's
   unit_enum_tag_to_i64 doesn't tell it from a fieldless one), so
   `Circle(1) == Circle(2)` was true;
2. a struct was an `icmp eq i64 %P-value`, which clang rejects.

ritz0 refuses both at the comparison (_reject_aggregate_compare); ritz1 and
ritz1_selfhosted now do too, with the same hint: tags-only for a payload enum,
strview_eq / string_eq_string for a StrView / String.

What still compiles: a fieldless enum's tags (#1660), pointers to structs, and
a payload enum's variant tested with `match`.  Their exit codes come from what
each program says, not from a compiler.
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
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_SHAPE = "enum Shape\n    Circle(i32)\n    Dot\n"
_P = "struct P\n    a: i32\n"
_W = "struct W\n    s: Shape\n    p: P\n"


def _main(*lines, pre=""):
    return pre + "fn main() -> i32\n" + "".join(f"    {line}\n" for line in lines)


_TAGS = "a variant carries a payload, so `==` would compare tags only; use `match` to test the variant"
_STRVIEW = "use strview_eq(@a, @b) from ritzlib.strview"

# Each row: the source, the type the refusal names, and the hint it gives ("" for none).
# The refusal is at the comparison's left operand, the token after `if `.
PAYLOAD_ENUM = {
    "local_eq_unit_variant": (_main("let o: Shape = Dot", "if o == Dot", "    return 2", "5",
                                    pre=_SHAPE), "Shape", _TAGS),
    "unit_variant_eq_local": (_main("let o: Shape = Dot", "if Dot == o", "    return 2", "5",
                                    pre=_SHAPE), "Shape", _TAGS),
    "two_ctors": (_main("if Circle(1) == Circle(2)", "    return 2", "5", pre=_SHAPE),
                  "Shape", _TAGS),
    "ne_locals": (_main("let o: Shape = Circle(1)", "let q: Shape = Circle(2)", "if o != q",
                        "    return 5", "2", pre=_SHAPE), "Shape", _TAGS),
    "param": ("fn f(o: Shape) -> i32\n    if o == Dot\n        return 2\n    5\n"
              + _main("f(Dot)", pre=_SHAPE), "Shape", _TAGS),
    "field": (_main("let w: W = W { s: Dot, p: P { a: 1 } }", "if w.s == Dot", "    return 2",
                    "5", pre=_SHAPE + _P + _W), "Shape", _TAGS),
    "qualified_variant": (_main("let o: Shape = Dot", "if o == Shape.Dot", "    return 2", "5",
                               pre=_SHAPE), "Shape", _TAGS),
    "two_fields": (_main("let w: W = W { s: Dot, p: P { a: 1 } }", "if w.s == w.s", "    return 2",
                         "5", pre=_SHAPE + _P + _W), "Shape", _TAGS),
    "two_qualified_variants": (_main("if Shape.Dot == Shape.Dot", "    return 2", "5", pre=_SHAPE),
                               "Shape", _TAGS),
}
STRUCT = {
    "two_locals": (_main("let o: P = P { a: 1 }", "let q: P = P { a: 1 }", "if o == q",
                         "    return 2", "5", pre=_P), "P", ""),
    "ne_locals": (_main("let o: P = P { a: 1 }", "let q: P = P { a: 2 }", "if o != q",
                        "    return 5", "2", pre=_P), "P", ""),
    "untyped_lets": (_main("let o = P { a: 1 }", "let q = P { a: 1 }", "if o == q",
                           "    return 2", "5", pre=_P), "P", ""),
    "call_result": ("fn mk() -> P\n    P { a: 1 }\n"
                    + _main("let q: P = P { a: 1 }", "if mk() == q", "    return 2", "5", pre=_P),
                    "P", ""),
    "field": (_main("let w: W = W { s: Dot, p: P { a: 1 } }", "let q: P = P { a: 1 }",
                    "if w.p == q", "    return 2", "5", pre=_SHAPE + _P + _W), "P", ""),
    "two_fields": (_main("let w: W = W { s: Dot, p: P { a: 1 } }", "if w.p == w.p",
                         "    return 2", "5", pre=_SHAPE + _P + _W), "P", ""),
    "strview": (_main('let a: StrView = "x"', 'let b: StrView = "x"', "if a == b",
                      "    return 2", "5"), "StrView", _STRVIEW),
}
REFUSED = {**{f"enum_{k}": v for k, v in PAYLOAD_ENUM.items()},
           **{f"struct_{k}": v for k, v in STRUCT.items()}}

_COLOR = "enum Color\n    Red\n    Green\n"
# Still compiles, and runs to the code the program says.
KEPT = {
    "fieldless_enum": (_main("let c: Color = Green", "if c == Green", "    return 5", "2",
                             pre=_COLOR), 5),
    "fieldless_enum_ne": (_main("let c: Color = Green", "if c != Color.Red", "    return 5", "2",
                                pre=_COLOR), 5),
    "struct_pointers": (_main("var o: P = P { a: 1 }", "let p: *P = @o", "let q: *P = @o",
                              "if p == q", "    return 5", "2", pre=_P), 5),
    "struct_pointer_null": (_main("var o: P = P { a: 1 }", "let p: *P = @o",
                                  "if p != null", "    return 5", "2", pre=_P), 5),
    "struct_fields": (_main("let o: P = P { a: 1 }", "let q: P = P { a: 1 }",
                            "if o.a == q.a", "    return 5", "2", pre=_P), 5),
    "payload_enum_match": (_main("let o: Shape = Circle(5)", "match o",
                                 "    Circle(v) => v", "    Dot => 2", pre=_SHAPE), 5),
}


def _ritz1(request, compiler, tmp_path, source):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _where(source, needle, offset=0):
    """1-based line and column of `needle`'s first occurrence, plus `offset`."""
    for line, text in enumerate(source.split("\n"), 1):
        if needle in text:
            return line, text.index(needle) + 1 + offset
    raise AssertionError(f"{needle!r} not in source")


def _refusal(source, type_name, hint):
    line, col = _where(source, "if ", 3)
    op = "!=" if " != " in source else "=="
    # ritz0 names the LLVM type (`struct.ritz_module_1.P`), ritz1 the Ritz one.
    tail = f" — {re.escape(hint)}" if hint else ""
    return (rf"unit\.ritz:{line}:{col}: .*'{re.escape(op)}' is not supported for struct type "
            rf"'[^']*\b{re.escape(type_name)}'{tail}$")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_refuses_eq_on_an_aggregate(request, tmp_path, compiler, name):
    source, type_name, hint = REFUSED[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    hits = re.findall(_refusal(source, type_name, hint), out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz1_keeps_scalar_compares(request, tmp_path, compiler, name):
    source, code = KEPT[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "unit"
    fast_link.clang(["clang", "-w", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"],
                   check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


# ritz0 is the reference: each refused row is its refusal too.  A builtin StrView
# is a literal `{i8*, i64}` there, so ritz0 neither names it nor gives its hint.
ON_RITZ0 = sorted(set(REFUSED) - {"struct_strview"})


@pytest.mark.integration
@pytest.mark.parametrize("name", ON_RITZ0)
def test_ritz0_refuses_eq_on_an_aggregate(tmp_path, name):
    source, type_name, hint = REFUSED[name]
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll")], cwd=tmp_path, env=env,
                     timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}"
    assert re.search(_refusal(source, type_name, hint), out, re.M), out[-800:]
