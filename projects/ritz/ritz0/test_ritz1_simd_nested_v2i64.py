"""AGAST #2051: ritz1 stores a nested v2i64-returning SIMD call as <4 x i32>.

THE DEFECT

`simd_storeu(p, v)` picks the store's vector type from `resolve_simd_arg_type`
on `v` and falls back to v4i32 when that cannot type it.  The resolver typed
idents, derefs and AES-NI calls, but not `simd_clmul` / `simd_sad`, which
always return <2 x i64>.  So with no `let r: v2i64 = ...` in between:

    simd_storeu(a, simd_clmul(x, y, 0))

ritz1 emitted `store <4 x i32> %r` for a `<2 x i64>` %r and clang rejected the
IR ("defined with type '<2 x i64>' but expected '<4 x i32>'").  An AES-NI call
whose state operand is one of those calls inherited the same miss.

THE FIX

The resolver types `simd_clmul(...)` and `simd_sad(...)` as v2i64 - the type
their emitters always produce - so every consumer (storeu, AES-NI operands,
binary ops) agrees with the emitted value.

Each program stores the nested call's result and exits with bits of it, so
the exit code is compared against ritz0's (the acceptance criterion).
"""

import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

pytestmark = pytest.mark.integration

# Arrays are zeroed in full: ritz `var` arrays are uninitialised, and the
# exit code must be deterministic for the ritz0 comparison to mean anything.
_ZERO_I64 = """\
fn zero_i64(p: *i64, n: i32)
    var i: i32 = 0
    while i < n
        p[i] = 0
        i = i + 1

"""

PROGRAMS = {
    # The ticket's repro, plus an exit code: clmul(3, 3) = 0b101 = 5.
    "clmul": _ZERO_I64
    + """\
fn use_clmul(a: *i64, b: *i64) -> i32
    let x: v2i64 = simd_loadu(a)
    let y: v2i64 = simd_loadu(b)
    simd_storeu(a, simd_clmul(x, y, 0))
    0

fn main() -> i32
    var p: [2]i64
    var q: [2]i64
    zero_i64(@p[0], 2)
    zero_i64(@q[0], 2)
    p[0] = 3
    q[0] = 3
    use_clmul(@p[0], @q[0])
    p[0] as i32
""",
    # simd_sad: v16i8 operands, <2 x i64> result.  |9 - 2| = 7.
    "sad": _ZERO_I64
    + """\
fn use_sad(a: *i64, b: *u8, c: *u8) -> i32
    let x: v16i8 = simd_loadu(b)
    let y: v16i8 = simd_loadu(c)
    simd_storeu(a, simd_sad(x, y))
    0

fn main() -> i32
    var p: [2]i64
    var b: [2]i64
    var c: [2]i64
    zero_i64(@p[0], 2)
    zero_i64(@b[0], 2)
    zero_i64(@c[0], 2)
    b[0] = 9
    c[0] = 2
    use_sad(@p[0], @b[0] as *u8, @c[0] as *u8)
    p[0] as i32
""",
    # An AES-NI call takes its state operand's type; here that operand is a
    # nested simd_clmul, so the clmul typing must flow through aesenc.
    "aesenc_of_clmul": _ZERO_I64
    + """\
fn use_aes(a: *i64, b: *i64) -> i32
    let x: v2i64 = simd_loadu(a)
    let y: v2i64 = simd_loadu(b)
    simd_storeu(a, aesenc(simd_clmul(x, y, 0), y))
    0

fn main() -> i32
    var p: [2]i64
    var q: [2]i64
    zero_i64(@p[0], 2)
    zero_i64(@q[0], 2)
    p[0] = 3
    q[0] = 3
    use_aes(@p[0], @q[0])
    (p[0] & 127) as i32
""",
    # AES-NI nested in AES-NI on v2i64 locals: already typed before #2051,
    # pinned so the clmul/sad change cannot disturb it.
    "aes_of_aes": _ZERO_I64
    + """\
fn use_aes(a: *i64, b: *i64) -> i32
    let x: v2i64 = simd_loadu(a)
    let y: v2i64 = simd_loadu(b)
    simd_storeu(a, aesenclast(aesimc(x), y))
    0

fn main() -> i32
    var p: [2]i64
    var q: [2]i64
    zero_i64(@p[0], 2)
    zero_i64(@q[0], 2)
    p[0] = 3
    q[0] = 5
    use_aes(@p[0], @q[0])
    (p[0] & 127) as i32
""",
}


def _ritz1_run(tmp_path: Path, name: str, program: str, ritz_start: Path) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.r1.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}.r1"
    link = subprocess.run(
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
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# Exit codes ritz0 produces; asserted against the oracle below so a drift in
# either compiler is visible, not just a disagreement between them.
EXPECTED = {"clmul": 5, "sad": 7}


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_matches_ritz0(ritz1_bin, ritz_start, ritz0_oracle, tmp_path, name):
    oracle = ritz0_oracle(PROGRAMS[name])
    assert oracle.ir_ok, f"ritz0 rejected {name}:\n{oracle.diagnostics[-2000:]}"
    if name in EXPECTED:
        assert oracle.rc == EXPECTED[name]
    assert _ritz1_run(tmp_path, name, PROGRAMS[name], ritz_start) == oracle.rc


@pytest.mark.parametrize("name", ["clmul", "sad"])
def test_ritz1_stores_nested_v2i64_as_v2i64(ritz1_bin, tmp_path, name):
    """The IR-level symptom: the store must be typed <2 x i64>."""
    src = tmp_path / f"{name}.ritz"
    src.write_text(PROGRAMS[name])
    ll = tmp_path / f"{name}.ll"
    subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        capture_output=True,
        timeout=300,
        check=True,
    )
    body = ll.read_text().split(f"@use_{name}(", 1)[1].split("\n}\n", 1)[0]
    # simd_storeu is the only align-1 vector store (the `let` bindings'
    # stores carry no alignment).
    stores = [ln for ln in body.splitlines() if "store <" in ln and "align 1" in ln]
    assert len(stores) == 1 and "store <2 x i64>" in stores[0], stores
