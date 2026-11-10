#!/usr/bin/env python3
"""A generic fn's by-value `Option<T>` / `Result<T, E>` / `Slot<T>` param (AGAST #2418).

ritz1 substituted T in a param only when the param's type was T itself, or a
pointer to something naming T. A by-value generic type kept its template name,
so the ticket's program

    fn f<T>(o: Option<T>) -> i32
        match o
            Some(v) => 1
            _ => 2
    fn main() -> i32
        let o: Option<i32> = Some(5)
        f<i32>(o)

was defined as `@f$i32(%Option$T %o.arg)`, and clang refused it. `Result<T, i32>`
in a one-parameter fn was worse: T isn't the last component, so even the
name rewrite missed it (`%Result$T$i32`).

Every row runs on ritz0, ritz1 and ritz1_selfhosted. The expected exit code
comes from what the program says, not from a compiler. Type names are more than
one letter: a one-letter real type is #2420's bug, not this one.
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

_SLOT = "struct Slot\n    a: i32\n    b: i32\n"
_PAIR = "struct Pair<T>\n    a: T\n    b: T\n"

PROGRAMS = {
    # The ticket's program.
    "option_param": ("fn f<T>(o: Option<T>) -> i32\n    match o\n        Some(v) => 1\n"
                     "        _ => 2\nfn main() -> i32\n    let o: Option<i32> = Some(5)\n"
                     "    f<i32>(o)\n", 1),
    "option_param_none": ("fn f<T>(o: Option<T>) -> i32\n    match o\n        Some(v) => 1\n"
                          "        _ => 2\nfn main() -> i32\n    let o: Option<i32> = None\n"
                          "    f<i32>(o)\n", 2),
    # The payload is read at T's width.
    "option_param_payload": ("fn f<T>(o: Option<T>, d: T) -> T\n    match o\n"
                             "        Some(v) => v\n        _ => d\nfn main() -> i32\n"
                             "    let o: Option<i32> = Some(37)\n    f<i32>(o, 9)\n", 37),
    "option_param_i64": ("fn f<T>(o: Option<T>, d: T) -> T\n    match o\n"
                         "        Some(v) => v\n        _ => d\nfn main() -> i32\n"
                         "    let o: Option<i64> = Some(4294967337)\n"
                         "    (f<i64>(o, 9) - 4294967296) as i32\n", 41),
    "option_param_struct": (_SLOT + "fn f<T>(o: Option<T>) -> i32\n    match o\n"
                            "        Some(v) => 1\n        _ => 2\nfn main() -> i32\n"
                            "    let o: Option<Slot> = Some(Slot { a: 1, b: 2 })\n"
                            "    f<Slot>(o)\n", 1),
    # T is the first of two components: not a "$T" suffix.
    "result_param_t_first": ("fn f<T>(r: Result<T, i32>) -> i32\n    match r\n"
                             "        Ok(v) => 5\n        Err(e) => e\nfn main() -> i32\n"
                             "    let r: Result<i32, i32> = Err(6)\n    f<i32>(r)\n", 6),
    "result_param_t_first_ok": ("fn f<T>(r: Result<T, i64>) -> T\n    match r\n"
                                "        Ok(v) => v\n        Err(e) => 0\nfn main() -> i32\n"
                                "    let r: Result<i32, i64> = Ok(23)\n    f<i32>(r)\n", 23),
    "result_param_t_last": ("fn f<E>(r: Result<i32, E>) -> i32\n    match r\n"
                            "        Ok(v) => v\n        Err(e) => 6\nfn main() -> i32\n"
                            "    let r: Result<i32, i64> = Ok(15)\n    f<i64>(r)\n", 15),
    "result_param_two_params": ("fn f<T, E>(r: Result<T, E>) -> i32\n    match r\n"
                                "        Ok(v) => 5\n        Err(e) => 6\nfn main() -> i32\n"
                                "    let r: Result<i32, i64> = Err(1)\n    f<i32, i64>(r)\n", 6),
    # The inner value is built first: `Some(Some(5))` itself is #2435.
    "nested_option_param": ("fn f<T>(o: Option<Option<T>>) -> i32\n    match o\n"
                            "        Some(i) => 1\n        _ => 2\nfn main() -> i32\n"
                            "    let i: Option<i32> = Some(5)\n"
                            "    let o: Option<Option<i32>> = Some(i)\n    f<i32>(o)\n", 1),
    # A generic struct by value took the same path.
    "struct_param": (_PAIR + "fn f<T>(p: Pair<T>) -> T\n    p.b\nfn main() -> i32\n"
                     "    var p: Pair<i32>\n    p.a = 4\n    p.b = 11\n    f<i32>(p)\n", 11),
    # #2275's return: T first in `Result<T, Fault>` (`%Result$T$Fault` before).
    "result_return_t_first": ("struct Page\n    id: i64\nstruct Fault\n    code: i32\n"
                              "fn first<T>(v: T) -> Result<T, Fault>\n    Ok(v)\n"
                              "fn main() -> i32\n"
                              "    let r: Result<Page, Fault> = first<Page>(Page { id: 8 })\n"
                              "    match r\n        Ok(p) => p.id as i32\n"
                              "        Err(e) => 50 + e.code\n", 8),
    "result_local_t_first": ("fn f<T>(x: T) -> i32\n    let r: Result<T, i64> = Ok(x)\n"
                             "    match r\n        Ok(v) => 3\n        Err(e) => 4\n"
                             "fn main() -> i32\n    f<i32>(7)\n", 3),
    # Already right before #2418; pinned beside the param.
    "option_return": ("fn f<T>(x: T) -> Option<T>\n    Some(x)\nfn main() -> i32\n"
                      "    match f<i32>(12)\n        Some(v) => v\n        _ => 2\n", 12),
    "option_local": ("fn f<T>(x: T) -> i32\n    let o: Option<T> = Some(x)\n    match o\n"
                     "        Some(v) => 3\n        _ => 4\nfn main() -> i32\n    f<i32>(7)\n", 3),
    "option_pointer_param": ("fn f<T>(o: *Option<T>) -> i32\n    match *o\n"
                             "        Some(v) => 1\n        _ => 2\nfn main() -> i32\n"
                             "    let o: Option<i32> = None\n    f<i32>(@o)\n", 2),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_generic_enum_param_runs(request, tmp_path, compiler, name):
    source, code = PROGRAMS[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler}, {name}:\n{out[-1500:]}"
    if compiler != "ritz0":
        # No template name may be used. The template's own signature still
        # declares one (`%Result$T$i32 = type ...`), unused; clang takes that.
        uses = [ln for ln in ll.read_text().splitlines() if not re.match(r"%\S+ = type ", ln)]
        bad = [ln for ln in uses if re.search(r"%[\w.$]*\$[TE]\b", ln)]
        assert not bad, f"{compiler}, {name}: a template name is used:\n" + "\n".join(bad[:5])
    exe = tmp_path / "unit"
    # ritz0 emits its own `_start`; ritz1 links the runtime's.
    start = [] if compiler == "ritz0" else [str(RITZ_START)]
    link = subprocess.run(["clang", "-w", str(ll), *start, "-o", str(exe), "-nostdlib"],
                          capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}, {name}: clang\n{link.stderr[-1500:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"
