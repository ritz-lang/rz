"""AGAST #1985: ritz1 tags every non-intrinsic `declare` "no-builtins".

The ritz1 counterpart of test_o2_libc_names.py (AGAST #1917). At -O2 LLVM's
InferFunctionAttrs recognises a *declaration* by name: a module importing
ritzlib.memory's `realloc` got libc's allocptr/allockind/noalias attributes
and `realloc(malloc(64), 0) == null` folded to false. ritz0 now tags every
non-`llvm.*` declare. ritz1 escaped only because it declares imports
`declare i64 @realloc(...)`, a prototype libc's doesn't match; the moment it
emits typed declarations the miscompile returns. So ritz1 tags them too, on
every branch of emit_extern_declarations and the concrete (#1739/#2302)
declare, and leaves `llvm.*` intrinsic declarations alone.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

# One imported fn per emit_extern_declarations branch: sret (>= 256 bytes),
# struct return, i64, i32, void, and the concrete-signature declare for a
# byval param (#1739) and a `-> [N]T` (#2302).
LIB = """\
pub struct Huge
    data: [40]i64

pub fn lib_huge() -> Huge
    var h: Huge
    h.data[0] = 9
    h

pub fn lib_take(h: Huge) -> i64
    h.data[0]

pub struct Pair
    a: i64
    b: i64

pub fn lib_pair() -> Pair
    Pair { a: 1, b: 2 }

pub fn lib_i64() -> i64
    3

pub fn lib_i32() -> i32
    4

pub fn lib_void()
    return

pub fn lib_arr() -> [3]i64
    [1, 2, 3]
"""

SRC = """\
import ritzlib.memory
import r1985lib

fn main() -> i32
    let p1: *u8 = malloc(64)
    let p2: *u8 = realloc(p1, 0)
    free(malloc(8))
    let n: u32 = 6
    if n.popcnt() != 2
        return 2
    let f: f64 = -1.5
    if f.abs() < 1.0
        return 3
    if lib_take(lib_huge()) != 9
        return 5
    let pr = lib_pair()
    let a = lib_arr()
    lib_void()
    if pr.a + lib_i64() + a[0] != 5 or lib_i32() != 4
        return 4
    if p2 == null
        return 7
    1
"""

IMPORTED = ("malloc", "realloc", "free", "lib_huge", "lib_take",
            "lib_pair", "lib_i64", "lib_i32", "lib_void", "lib_arr")


def _emit(request, compiler: str, tmp_path: Path, src_text: str = SRC,
          extra: tuple = ()) -> str:
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    (tmp_path / "r1985lib.ritz").write_text(LIB)
    src = tmp_path / "t.ritz"
    src.write_text(src_text)
    ll = tmp_path / "t.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = subprocess.run([str(binary), str(src), "-o", str(ll), *extra], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    return ll.read_text()


def _declare(ir: str, name: str) -> str:
    m = re.search(rf'^declare [^\n]*@"?{re.escape(name)}"?\(.*$', ir, re.M)
    assert m, f"no declaration of {name}"
    return m.group(0)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_imported_function_declarations_are_no_builtins(request, tmp_path, compiler):
    ir = _emit(request, compiler, tmp_path)
    for name in IMPORTED:
        assert '"no-builtins"' in _declare(ir, name), _declare(ir, name)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_test_table_main_declaration_is_no_builtins(request, tmp_path, compiler):
    # --test-table drops the file's `main` and declares the runner's.
    src = "[[test]]\nfn test_a() -> i32\n    0\n"
    ir = _emit(request, compiler, tmp_path, src, ("--test-table",))
    assert '"no-builtins"' in _declare(ir, "main"), _declare(ir, "main")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_intrinsic_declarations_are_left_alone(request, tmp_path, compiler):
    ir = _emit(request, compiler, tmp_path)
    intrinsics = re.findall(r'^declare [^\n]*@"?llvm\.[^\n]*$', ir, re.M)
    # The program calls popcnt and abs: without them this test proves nothing.
    assert len(intrinsics) >= 2, ir
    for line in intrinsics:
        assert "no-builtins" not in line, line


@pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")
def test_O2_keeps_the_realloc_call_and_its_null_check(request, tmp_path):
    _emit(request, "ritz1", tmp_path)
    opt = subprocess.run(
        ["clang", "-O2", "-S", "-emit-llvm", "-Wno-override-module",
         str(tmp_path / "t.ll"), "-o", "-"],
        capture_output=True, text=True)
    assert opt.returncode == 0, opt.stderr
    out = opt.stdout
    main = re.search(r"^define [^\n]*@main\(.*?^}", out, re.M | re.S).group(0)
    assert "@realloc(" in main, main
    assert "i32 7" in main, main
    decl = re.search(r"^declare [^\n]*@realloc\(.*$", out, re.M).group(0)
    assert "allocptr" not in decl and "noalias" not in decl, decl
