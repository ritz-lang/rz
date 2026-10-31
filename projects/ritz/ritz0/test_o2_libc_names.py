"""AGAST #1917: -O2 must not treat Ritz functions as libc builtins by name.

Ritz links -nostdlib; `malloc`, `realloc` and `free` are ritzlib.memory's
own functions. A module that imports them *declares* them. At -O2 LLVM's
InferFunctionAttrs pass recognises a declaration by name alone (TLI built
from the declaration's own attributes) and gives `realloc` libc's
allocator attributes (`allocptr`, `allockind`, `noalias`). With those,
`p = malloc(64); q = realloc(p, 0); q == null` was folded: the pair was
elided and the elided allocation assumed non-null, so ritzlib's documented
`realloc(p, 0) -> null` read as non-null (ritzlib test_realloc_zero).

"no-builtins" on definitions (#1313) only covers callers; the declarations
need it too.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

SRC = """\
import ritzlib.memory

fn main() -> i32
    let p1: *u8 = malloc(64)
    let p2: *u8 = realloc(p1, 0)
    if p2 == null
        return 7
    1
"""


def _emit(tmp_path: Path) -> str:
    src = tmp_path / "t.ritz"
    src.write_text(SRC)
    ll = tmp_path / "t.ll"
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path,
                     env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ll.read_text()


def _declare(ir: str, name: str) -> str:
    m = re.search(rf'^declare [^\n]*@"{name}"\(.*$', ir, re.M)
    assert m, f"no declaration of {name}"
    return m.group(0)


def test_imported_function_declarations_are_no_builtins(tmp_path):
    ir = _emit(tmp_path)
    for name in ("malloc", "realloc", "free"):
        assert '"no-builtins"' in _declare(ir, name), _declare(ir, name)


def test_intrinsic_declarations_are_left_alone(tmp_path):
    ir = _emit(tmp_path)
    for line in re.findall(r'^declare [^\n]*@"?llvm\.[^\n]*$', ir, re.M):
        assert "no-builtins" not in line, line


@pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")
def test_O2_keeps_the_realloc_call_and_its_null_check(tmp_path):
    _emit(tmp_path)
    opt = subprocess.run(
        ["clang", "-O2", "-S", "-emit-llvm", "-Wno-override-module",
         str(tmp_path / "t.ll"), "-o", "-"],
        capture_output=True, text=True)
    assert opt.returncode == 0, opt.stderr
    out = opt.stdout
    main = re.search(r"^define [^\n]*@main\(.*?^}", out, re.M | re.S).group(0)
    # Before the fix main was `ret i32 1`: realloc gone, null check folded.
    assert "@realloc(" in main, main
    assert re.search(r"icmp eq ptr %[\w.]+, null", main), main
    assert "i32 7" in main, main
    decl = re.search(r"^declare [^\n]*@realloc\(.*$", out, re.M).group(0)
    assert "allocptr" not in decl and "noalias" not in decl, decl
