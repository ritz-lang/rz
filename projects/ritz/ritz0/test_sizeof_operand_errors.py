"""AGAST #2124: a `sizeof` operand that names no type, or whose type can't be
determined, is a compile error in ritz0 and ritz1 alike (LANGUAGE_SPEC §7.9).

Before the fix both compilers answered 8 for anything they couldn't size, so
`sizeof(Nope)` and `sizeof(h.typo)` compiled. The happy paths (locals,
fields, globals, `[N]T`, no move, no evaluation) are the three-compiler
matrix file ritz0/test/test_issue_sizeof_expr.ritz.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

PRELUDE = """\
struct Holder
    tag: i32
    arr: [48]u8

"""

# name -> (last line of main, substring both errors must contain). The
# sizeof is on line 8: PRELUDE is 4 lines, then `fn main`, `var h`, `h.tag`.
FAIL = {
    "unknown_name": ("    return sizeof(Nope) as i32\n", "Nope"),
    "unknown_array_elem": ("    return sizeof([4]Nope) as i32\n", "sizeof"),
    "unknown_pointee_name": ("    return sizeof(*Nope) as i32\n", "sizeof"),
    "unknown_field": ("    return sizeof(h.nope) as i32\n", "sizeof"),
    "two_args": ("    return sizeof(i32, i64) as i32\n", "sizeof"),
}


def _program(body: str) -> str:
    return PRELUDE + "fn main() -> i32\n    var h: Holder\n    h.tag = 0\n" + body


SIZEOF_LINE = 8


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    return subprocess.run([str(RITZ1_BIN), str(src), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)


def _assert_rejected(proc, compiler: str, needle: str):
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted it:\n{out[-2000:]}"
    assert needle in out, f"{compiler} error lacks {needle!r}:\n{out[-2000:]}"
    assert f":{SIZEOF_LINE}:" in out, f"{compiler} error names no line {SIZEOF_LINE}:\n{out[-2000:]}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FAIL))
def test_ritz0_rejects_unsizable_operand(tmp_path, name):
    body, needle = FAIL[name]
    _assert_rejected(_compile("ritz0", tmp_path, name, _program(body)), "ritz0", needle)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FAIL))
def test_ritz1_rejects_unsizable_operand(ritz1_bin, tmp_path, name):
    body, needle = FAIL[name]
    _assert_rejected(_compile("ritz1", tmp_path, name, _program(body)), "ritz1", needle)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_array_type_operand_only_for_sizeof(request, tmp_path, compiler):
    """`[N]T` reads as a type only as sizeof's operand: `f([8]u8)` is no call."""
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    program = "fn f(n: i64) -> i64\n    return n\n\nfn main() -> i32\n    return f([8]u8) as i32\n"
    proc = _compile(compiler, tmp_path, "not_sizeof", program)
    assert proc.returncode != 0, f"{compiler} accepted f([8]u8):\n{proc.stdout}{proc.stderr}"
