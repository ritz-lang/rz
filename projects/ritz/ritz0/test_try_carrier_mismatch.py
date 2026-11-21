#!/usr/bin/env python3
"""AGAST #4455: `?` outside a matching carrier fn is a located refusal.

LANGUAGE_SPEC §14.2: the enclosing function must return the same carrier as
the `?` operand — an `Option` for an `Option`, a `Result` for a `Result`.
ritz0 refuses at the emitter. ritz1 and ritz1_selfhosted did not check:
the early return lowered to `ret % %.N` (an empty type name), clang rejected
the IR, and the compiler still exited 0 — so check_doc_examples counted the
program as COMPILED and the §14.2 expect-error block was a known failure.

Each `MISMATCHES` row must exit non-zero, write no `.ll`, and print ritz0's
message at the operand's `line:col`. Each `MATCHES` row is the same `?` in a
function whose carrier does match; it must keep compiling and running.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

OPT_PRELUDE = """\
import ritzlib.option

fn find(x: i32) -> Option<i32>
    if x > 0
        return Some(x)
    None

"""

RES_PRELUDE = """\
import ritzlib.result

fn parse(x: i32) -> Result<i32, i32>
    if x > 0
        return Ok(x)
    return Err(1)

"""

# `^` marks the operand's start: where ritz0 locates the diagnostic. The
# message is ritz0's, verbatim (emitter_llvmlite: _emit_try_op_option and
# _emit_try_op); `got None` / `got i32` are what it renders for these returns.
MISMATCHES = {
    "option_outside_option": (
        OPT_PRELUDE + "fn twice(x: i32) -> i32\n    let v = ^find(x)?\n    v + v\n",
        "Try operator on an Option used in a function that does not return an Option (got None)",
    ),
    "result_outside_result": (
        RES_PRELUDE + "fn twice(x: i32) -> i32\n    let v = ^parse(x)?\n    v + v\n",
        "Try operator used in function not returning Result type (got i32)",
    ),
}

# The legitimate same-carrier `?`, including a different Ok payload type than
# the enclosing fn's — it must stay accepted (exit code 3 on success).
MATCHES = {
    "option_inside_option": (
        OPT_PRELUDE
        + "fn twice(x: i32) -> Option<i32>\n"
        "    let v = find(x)?\n"
        "    Some(v + v)\n"
        "\n"
        "fn main() -> i32\n"
        "    if twice(3).unwrap_or(-1) == 6\n"
        "        return 3\n"
        "    1\n"
    ),
    "result_inside_result": (
        RES_PRELUDE
        + "fn twice(x: i32) -> Result<i32, i32>\n"
        "    let v = parse(x)?\n"
        "    Ok(v + v)\n"
        "\n"
        "fn main() -> i32\n"
        "    match twice(3)\n"
        "        Ok(v) => v - 3\n"
        "        Err(e) => 2\n"
    ),
}


def _located(marked):
    """`marked` without its `^`, and where the `^` was as `line:col`."""
    before = marked[: marked.index("^")]
    line = before.count("\n") + 1
    return marked.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


def _emit(compiler, work, src):
    binary = RITZ1_BUILD / compiler
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    comp = subprocess.run(
        [str(binary), str(path), "-o", str(ll)],
        cwd=work,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    return comp, ll


def _workdir(tmp_path, row, compiler):
    work = tmp_path / f"{row}_{compiler}"
    work.mkdir()
    return work


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(MISMATCHES))
def test_try_outside_its_carrier_is_refused(request, tmp_path, compiler, row):
    request.getfixturevalue("ritz1_bin")
    marked, message = MISMATCHES[row]
    src, where = _located(marked)
    comp, ll = _emit(compiler, _workdir(tmp_path, row, compiler), src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {row}:\n{src}\n{out[-2000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for refused {row}:\n{out[-2000:]}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert (where, message) in found, (
        f"{compiler}: {row}, wanted {where}: {message}\n{out[-2000:]}"
    )


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(MATCHES))
def test_try_inside_its_carrier_still_compiles_and_runs(request, tmp_path, compiler, row):
    request.getfixturevalue("ritz1_bin")
    src = MATCHES[row]
    work = _workdir(tmp_path, row, compiler)
    comp, ll = _emit(compiler, work, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {row}:\n{out[-2000:]}"
    exe = work / "main"
    link = subprocess.run(
        [
            "clang",
            "-Wno-override-module",
            str(RITZ_START),
            str(ll),
            "-o",
            str(exe),
            "-nostdlib",
            "-no-pie",
        ],
        cwd=work,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert link.returncode == 0, f"{compiler}: {row} would not link:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], capture_output=True, timeout=60).returncode == 3
