"""AGAST #3266: ritz1 lowers every AES-NI builtin ritz0 does, incl. aeskeygenassist.

THE DEFECT

ritz0 lowers `aesenc`, `aesenclast`, `aesdec`, `aesdeclast`, `aesimc` and
`aeskeygenassist` to `@llvm.x86.aesni.*`.  ritz1 knew the first five but not
`aeskeygenassist`, so cryptosec's test_sha_ni.ritz:198

    var result: v2i64 = aeskeygenassist(v_key, 0x01)

fell through to the generic call path, `call i64 @aeskeygenassist(i64 %v,
...)` with a `<2 x i64>` operand, and clang rejected the whole file.

THE FIX

ritz1 dispatches `aeskeygenassist(key, rcon)` to
`@llvm.x86.aesni.aeskeygenassist(<2 x i64>, i8)`.  As in ritz0, `rcon` is
an `immarg` that must be an integer literal, and the result takes the key's
vector type.  `is_aesni_builtin` lists it too, so a nested call (e.g. as
`simd_storeu`'s value) is typed like the other AES-NI calls.

One row per intrinsic, each compared against ritz0's exit code (the
acceptance criterion).  The exit code folds all 128 result bits into a byte.
rcon is xored into bits 32..39 and 96..103, so the high half is multiplied
before the fold; a plain xor of both halves cancels rcon out.
"""

import subprocess
from pathlib import Path

import fast_link
import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

pytestmark = pytest.mark.integration

# `var` arrays are uninitialised; set every lane so the exit code is
# deterministic.  `fold` mixes the halves (see the docstring) to a byte.
_TEMPLATE = """\
fn fold(p: *i64) -> i32
    var v: i64 = p[0] ^ (p[1] * 7)
    v = v ^ (v >> 32)
    v = v ^ (v >> 16)
    v = v ^ (v >> 8)
    (v & 255) as i32

fn use_it(a: *i64, b: *i64) -> i32
{decls}
{body}
    0

fn main() -> i32
    var p: [2]i64
    var q: [2]i64
    p[0] = 0x0123456789abcdef
    p[1] = 0x0f1e2d3c4b5a6978
    q[0] = 0x1122334455667788
    q[1] = 0x7f6e5d4c3b2a1908
    use_it(@p[0], @q[0])
    fold(@p[0])
"""

_V2 = "    let x: v2i64 = simd_loadu(a)\n    let y: v2i64 = simd_loadu(b)"
_V4 = "    let x: v4i32 = simd_loadu(a)\n    let y: v4i32 = simd_loadu(b)"


def _prog(body: str, decls: str = _V2) -> str:
    return _TEMPLATE.format(decls=decls, body=body)


PROGRAMS = {
    "aesenc": _prog("    let r: v2i64 = aesenc(x, y)\n    simd_storeu(a, r)"),
    "aesenclast": _prog("    let r: v2i64 = aesenclast(x, y)\n    simd_storeu(a, r)"),
    "aesdec": _prog("    let r: v2i64 = aesdec(x, y)\n    simd_storeu(a, r)"),
    "aesdeclast": _prog("    let r: v2i64 = aesdeclast(x, y)\n    simd_storeu(a, r)"),
    "aesimc": _prog("    let r: v2i64 = aesimc(x)\n    simd_storeu(a, r)"),
    # The ticket's shape (cryptosec test_sha_ni.ritz:198): v2i64, hex rcon.
    "aeskeygenassist": _prog(
        "    var r: v2i64 = aeskeygenassist(x, 0x01)\n    simd_storeu(a, r)"
    ),
    # ritz0 also takes a v4i32 key and returns v4i32 (bitcasts round it).
    "aeskeygenassist_v4i32": _prog(
        "    let r: v4i32 = aeskeygenassist(x, 0x36)\n    simd_storeu(a, r)", _V4
    ),
    # No binding: simd_storeu must type the nested call from its key.
    "aeskeygenassist_nested": _prog("    simd_storeu(a, aeskeygenassist(x, 0x80))"),
}


def _ritz1_run(tmp_path: Path, name: str, program: str, ritz_start: Path) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.r1.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}.r1"
    link = fast_link.clang(
        [
            "clang",
            "-nostdlib",
            "-Wno-override-module",
            str(ll),
            str(ritz_start),
            "-o",
            str(exe),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert link.returncode == 0, f"ritz1 IR for {name} rejected:\n{link.stderr[-2000:]}"
    return subprocess.run(
        [str(exe)], check=False, capture_output=True, timeout=60
    ).returncode


def _has_aes() -> bool:
    try:
        return " aes " in f" {Path('/proc/cpuinfo').read_text()} "
    except OSError:
        return False


@pytest.mark.skipif(not _has_aes(), reason="CPU lacks AES-NI")
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_matches_ritz0(ritz1_bin, ritz_start, ritz0_oracle, tmp_path, name):
    oracle = ritz0_oracle(PROGRAMS[name])
    assert oracle.ir_ok, f"ritz0 rejected {name}:\n{oracle.diagnostics[-2000:]}"
    assert _ritz1_run(tmp_path, name, PROGRAMS[name], ritz_start) == oracle.rc


def test_ritz1_aeskeygenassist_ir(ritz1_bin, tmp_path):
    """IR shape, CPU-independent: the intrinsic takes an i8 immediate."""
    src = tmp_path / "k.ritz"
    src.write_text(PROGRAMS["aeskeygenassist"])
    ll = tmp_path / "k.ll"
    subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        capture_output=True,
        timeout=300,
        check=True,
    )
    ir = ll.read_text()
    assert "declare <2 x i64> @llvm.x86.aesni.aeskeygenassist(<2 x i64>, i8)" in ir
    assert "call <2 x i64> @llvm.x86.aesni.aeskeygenassist(<2 x i64> %" in ir
    assert ", i8 1)" in ir
    assert "@aeskeygenassist(" not in ir
