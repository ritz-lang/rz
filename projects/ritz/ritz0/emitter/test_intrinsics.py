"""The SIMD / AES-NI / SHA-NI / BitOps intrinsic tables (AGAST #1826).

`_try_emit_simd_builtin` was a 139-branch if/elif chain and is now a table in
emitter/intrinsics.py.  The corpus IR stayed byte-identical through the move;
these tests pin what the corpus does not reach: every table entry's arity
diagnostic (so a dropped or misspelled entry falls through to "Unknown
function"), xgetbv's lowering, and the u8 swap_bytes no-op.
"""

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emitter import intrinsics  # noqa: E402
from ritz0_inproc import run_ritz0  # noqa: E402

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
LOCATED = r"main\.ritz:\d+:\d+: "

# builtin -> its arity diagnostic when called with no arguments
SIMD_ARITY = {
    'simd_load': "simd_load() requires exactly 1 argument (pointer)",
    'simd_loadu': "simd_loadu() requires exactly 1 argument (pointer)",
    'simd_store': "simd_store() requires 2 arguments (pointer, value)",
    'simd_storeu': "simd_storeu() requires 2 arguments (pointer, value)",
    'simd_extract': "simd_extract() requires 2 arguments (vector, index)",
    'simd_insert': "simd_insert() requires 3 arguments (vector, index, value)",
    'simd_shuffle': "simd_shuffle() requires at least 3 arguments (vec, vec, mask...)",
    'simd_sad': "simd_sad() requires 2 arguments (vec<16, i8>, vec<16, i8>)",
    'simd_clmul': "simd_clmul() requires 3 arguments (v2i64, v2i64, imm8)",
    'simd_add': "simd_add() requires 2 arguments (vector, vector)",
    'simd_xor': "simd_xor() requires 2 arguments (vector, vector)",
    'simd_rotl': "simd_rotl() requires 2 arguments (vector, shift)",
    'xgetbv': "xgetbv() requires 1 argument (xcr)",
    'aesenc': "aesenc() requires 2 arguments (state, key)",
    'aesenclast': "aesenclast() requires 2 arguments (state, key)",
    'aesdec': "aesdec() requires 2 arguments (state, key)",
    'aesdeclast': "aesdeclast() requires 2 arguments (state, key)",
    'aesimc': "aesimc() requires 1 argument (key)",
    'aeskeygenassist': "aeskeygenassist() requires 2 arguments (key, rcon)",
    'sha256rnds2': "sha256rnds2() requires 3 arguments (cdgh, abef, wk)",
    'sha256msg1': "sha256msg1() requires 2 arguments (w0, w1)",
    'sha256msg2': "sha256msg2() requires 2 arguments (w0, w1)",
}

BITOPS_ARITY = {
    'rotl': ("rotl()", "rotl() requires exactly 1 argument"),
    'rotr': ("rotr()", "rotr() requires exactly 1 argument"),
    'clz': ("clz(1)", "clz() takes no arguments"),
    'ctz': ("ctz(1)", "ctz() takes no arguments"),
    'popcnt': ("popcnt(1)", "popcnt() takes no arguments"),
    'swap_bytes': ("swap_bytes(1)", "swap_bytes() takes no arguments"),
}


def _compile(tmp_path, src):
    (tmp_path / "main.ritz").write_text(src)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0(["main.ritz", "-o", str(tmp_path / "main.ll"), "--no-runtime"],
                     cwd=tmp_path, env=env, timeout=300)


@pytest.mark.unit
def test_tables_cover_exactly_the_documented_builtins():
    assert set(intrinsics.SIMD_BUILTINS) == set(SIMD_ARITY)
    assert set(intrinsics.BITOPS_METHODS) == set(BITOPS_ARITY)


@pytest.mark.parametrize("name", sorted(SIMD_ARITY))
def test_simd_builtin_arity_is_located(tmp_path, name):
    comp = _compile(tmp_path, f"fn f() -> i32\n    {name}()\n    0\n\nfn main() -> i32\n    0\n")
    assert comp.returncode != 0
    assert "Traceback" not in comp.stderr, comp.stderr[-3000:]
    assert re.search(LOCATED + re.escape(SIMD_ARITY[name]), comp.stderr), comp.stderr[-3000:]


@pytest.mark.parametrize("method", sorted(BITOPS_ARITY))
def test_bitops_arity_is_located(tmp_path, method):
    call, message = BITOPS_ARITY[method]
    comp = _compile(tmp_path, f"fn main() -> i32\n    let a: u32 = 5\n    let b = a.{call}\n    0\n")
    assert comp.returncode != 0
    assert "Traceback" not in comp.stderr, comp.stderr[-3000:]
    assert re.search(LOCATED + re.escape(message), comp.stderr), comp.stderr[-3000:]


def test_xgetbv_combines_edx_eax_into_u64(tmp_path):
    comp = _compile(tmp_path, "fn f(x: u32) -> u64\n    xgetbv(x)\n\nfn main() -> i32\n    0\n")
    assert comp.returncode == 0, comp.stderr[-3000:]
    ll = (tmp_path / "main.ll").read_text()
    assert 'asm sideeffect "xgetbv", "={ax},={dx},{cx},~{dirflag},~{fpsr},~{flags}"' in ll
    assert re.search(r"shl i64 %\S+, 32", ll) and "or i64" in ll


def test_swap_bytes_of_u8_is_the_value(tmp_path):
    comp = _compile(tmp_path, "fn f(x: u8) -> u8\n    x.swap_bytes()\n\n"
                              "fn g(x: u16) -> u16\n    x.swap_bytes()\n\nfn main() -> i32\n    0\n")
    assert comp.returncode == 0, comp.stderr[-3000:]
    ll = (tmp_path / "main.ll").read_text()
    assert "llvm.bswap.i16" in ll and "llvm.bswap.i8" not in ll
