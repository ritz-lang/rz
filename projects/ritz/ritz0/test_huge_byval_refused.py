#!/usr/bin/env python3
"""A by-value param of 4 GiB or more is ritz0's located refusal (AGAST #3668).

A struct or `[N]T` param at the sret threshold is passed `ptr byval(%T)`
(#1739, #2306).  LLVM's verifier refuses a byval type whose alloc size is
2^32 bytes or more ("huge 'byval' arguments are unsupported"), so lexis's
`Stylesheet` (`[4096]CssRule` + i32) crashed clang's backend with "Broken
module found" and no source location.

ritz0 now refuses the param at its declaration, every function and extern
alike, called or not, and names the reference it should be.  Anything below
4 GiB keeps its byval ABI; a reference (`@H`, `@&H`) is a plain pointer.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

# 1073741825 i32s: 4 GiB + 4 bytes, the smallest i32 array past the limit.
_H = "struct H\n    a: [1073741825]i32\n"
_HUGE_BYTES = 4294967300


def _main(*lines, pre=""):
    return pre + "fn main() -> i32\n" + "".join(f"    {line}\n" for line in lines)


# Each row: the source, the refused param's name, its type as written, and
# the text just before the param that locates it.
REFUSED = {
    "struct_param": ("fn f(h: H) -> i32\n    0\n" + _main("0", pre=_H), "h", "H", "fn f("),
    "array_param": ("fn f(a: [1073741825]i32) -> i32\n    0\n" + _main("0"),
                    "a", "[1073741825]i32", "fn f("),
    "second_param": ("fn f(n: i32, h: H) -> i32\n    n\n" + _main("0", pre=_H),
                     "h", "H", "n: i32, "),
    "method_self": ("impl H\n    fn get(self: H) -> i32\n        0\n" + _main("0", pre=_H),
                    "self", "H", "fn get("),
    "extern_param": ("extern fn g(h: H) -> i32\n" + _main("0", pre=_H), "h", "H", "fn g("),
}

# Still compiles, and runs to the code main returns.
KEPT = {
    "const_ref": ("fn f(h: @H) -> i32\n    7\n" + _main("7", pre=_H), 7),
    "mut_ref": ("fn f(h: @&H) -> i32\n    7\n" + _main("7", pre=_H), 7),
}

# 1 GiB by value: a byval LLVM takes.  Compiled to IR, never run.
_ONE_GIB = "struct G\n    a: [268435456]i32\n" + "fn f(g: G) -> i32\n    0\n" + _main("0")


def _ritz0(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    return proc, ll


def _refusal(source, name, type_text, before):
    for line, text in enumerate(source.split("\n"), 1):
        if before in text:
            col = text.index(before) + len(before) + 1
            break
    else:
        raise AssertionError(f"{before!r} not in source")
    return (rf"unit\.ritz:{line}:{col}: parameter `{re.escape(name)}` is {_HUGE_BYTES} bytes, "
            rf"too large to pass by value \(LLVM's byval limit is 4 GiB\); take it by "
            rf"reference: `{re.escape(name)}: @{re.escape(type_text)}` or "
            rf"`{re.escape(name)}: @&{re.escape(type_text)}`")


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses_a_huge_by_value_param(tmp_path, name):
    source, param, type_text, before = REFUSED[name]
    proc, ll = _ritz0(tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}:\n{out[-800:]}"
    hits = re.findall(_refusal(source, param, type_text, before), out)
    assert len(hits) == 1, f"{name}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"ritz0 wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz0_keeps_a_huge_param_by_reference(tmp_path, name):
    source, code = KEPT[name]
    proc, ll = _ritz0(tmp_path, source)
    assert proc.returncode == 0, f"{name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "unit"
    fast_link.clang(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, name


@pytest.mark.integration
def test_ritz0_keeps_byval_below_4_gib(tmp_path):
    proc, ll = _ritz0(tmp_path, _ONE_GIB)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    assert re.search(r"define .*@\"?f\"?\(%\"?struct\.[^ ]*G\"?\* byval", ll.read_text()), \
        "the 1 GiB param should stay byval"
