#!/usr/bin/env python3
"""A call through a fn type with a by-value param of 4 GiB or more is refused at
the fn type (AGAST #3690).

#3668 refuses such a param on a fn definition or extern.  A fn-pointer TYPE
(`fn(H) -> i32`) slipped past it: every indirect call through one is a
`call ... (ptr byval(%H) ...)`, which LLVM's verifier refuses ("huge 'byval'
arguments are unsupported"), so clang crashed with no source location.

ritz0, ritz1 and ritz1_selfhosted now refuse the call at the fn type's `fn`
(the alias's, for a call through an alias), in #3668's words, naming the
reference to take instead, and write no IR.  A fn type that is never called
lowers to a plain `ptr` and passes nothing byval, so it stays legal.  A
`fn(@H)` / `fn(@&H)` slot is a plain pointer.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# 1073741825 i32s: 4 GiB + 4 bytes, the smallest i32 array past the limit.
_H = "struct H\n    a: [1073741825]i32\n\n"
_HUGE_BYTES = 4294967300
_MAIN = "\nfn main() -> i32\n    0\n"

# Each row: the source, the refused param's 1-based index, its type as
# written, and the source line holding the fn type (it is located at `fn(`).
# The rows separate the code paths: a fn-typed local / param (ident callee),
# a struct field (expression callee) whose huge param is a second, array
# param, and an alias, whose fn type is written away from the call.
REFUSED = {
    "param": (_H + "fn use_it(cb: fn(H) -> i32, h: *H) -> i32\n    cb(*h)\n" + _MAIN,
              1, "H", "fn use_it(cb: "),
    "field_array": ("struct S\n    cb: fn(i32, [1073741825]i32) -> i32\n\n"
                    "fn use_it(s: *S, a: *[1073741825]i32) -> i32\n    (s.cb)(1, *a)\n" + _MAIN,
                    2, "[1073741825]i32", "    cb: "),
    "alias": (_H + "type CB = fn(H) -> i32\n\nfn use_it(cb: CB, h: *H) -> i32\n    cb(*h)\n"
              + _MAIN, 1, "H", "type CB = "),
}

# Compiles, links and runs to 7: a reference slot, and an uncalled fn type.
_KEPT = (_H + "fn by_ref(cb: fn(@H) -> i32, h: @H) -> i32\n    cb(h)\n\n"
         "fn by_mut(cb: fn(@&H) -> i32, h: @&H) -> i32\n    cb(h)\n\n"
         "fn uncalled(cb: fn(H) -> i32) -> i32\n    7\n\n"
         "fn main() -> i32\n    7\n")


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
        return proc, ll
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


def _refusal(source, index, type_text, before):
    for line, text in enumerate(source.split("\n"), 1):
        if text.startswith(before):
            col = len(before) + 1
            break
    else:
        raise AssertionError(f"{before!r} not in source")
    t = re.escape(type_text)
    return (rf"unit\.ritz:{line}:{col}: (?:error: )?parameter #{index} of this fn type is {_HUGE_BYTES} "
            rf"bytes, too large to pass by value \(LLVM's byval limit is 4 GiB\); take it by "
            rf"reference: `@{t}` or `@&{t}`$")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_refuses_a_call_through_a_huge_by_value_fn_type(request, tmp_path, compiler, name):
    source, index, type_text, before = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    hits = re.findall(_refusal(source, index, type_text, before), out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one located refusal:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_keeps_a_huge_fn_type_param_by_reference(request, tmp_path, compiler):
    proc, ll = _compile(request, compiler, tmp_path, _KEPT)
    assert proc.returncode == 0, f"{compiler}:\n{(proc.stdout + proc.stderr)[-800:]}"
    assert "byval" not in ll.read_text(), f"{compiler}: nothing here passes byval"
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(3, str(RITZ_START))
    fast_link.clang(link, check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == 7, compiler

