"""AGAST #2052: ritz1 mistypes nested type-preserving simd_* calls.

THE DEFECT

`resolve_simd_arg_type` typed idents, derefs, AES-NI calls and (#2051)
simd_clmul / simd_sad.  Any other nested simd_* call fell back to the binding
context / fn return type / nothing, while its own emitter picked a type from
its operands.  In a fn returning i32 (no return-type fallback):

    simd_storeu(a, simd_xor(x, y))          # x, y: v2i64

emitted `xor <2 x i64>` but `store <4 x i32>`, and

    simd_storeu(a, aesenc(simd_loadu(a), y))

loaded `<4 x i32>` (simd_loadu's no-context default) but passed it to aesenc
as `<2 x i64>` with no bitcast.  clang rejected both.

THE FIX

The resolver mirrors each simd_* emitter's result-type choice:
xor/add -> first, else second operand, insert/shuffle/rotl -> first operand,
load/loadu -> the context chain; each with the emitters' v4i32 default.  The
resolver and the emitters can no longer disagree.

Each program stores the nested call's result and exits with bits of it, so the
exit code is compared against ritz0's (the acceptance criterion).
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

# main(): p = [6, 0], q = [3, 0]; call use(p, q); exit with p[0] & 127.
_MAIN = """
fn main() -> i32
    var p: [2]i64
    var q: [2]i64
    zero_i64(@p[0], 2)
    zero_i64(@q[0], 2)
    p[0] = 6
    q[0] = 3
    use(@p[0], @q[0])
    (p[0] & 127) as i32
"""


def _prog(body: str) -> str:
    return (
        _ZERO_I64
        + "fn use(a: *i64, b: *i64) -> i32\n"
        + "    let x: v2i64 = simd_loadu(a)\n"
        + "    let y: v2i64 = simd_loadu(b)\n"
        + f"    {body}\n"
        + "    0\n"
        + _MAIN
    )


# name -> (program, ritz0's exit code)
PROGRAMS = {
    # The ticket's shape 1.  6 ^ 3 = 5.
    "xor": (_prog("simd_storeu(a, simd_xor(x, y))"), 5),
    # 6 + 3 = 9.
    "add": (_prog("simd_storeu(a, simd_add(x, y))"), 9),
    # Context-free simd_loadu operands default to v4i32 in the emitter and the
    # resolver alike, so the xor and its store are <4 x i32>.  6 ^ 3 = 5.
    "xor_of_loadu": (
        _prog("simd_storeu(a, simd_xor(simd_loadu(a), simd_loadu(b)))"),
        5,
    ),
    # Ticket's shape 1, second variant: xor of two v2i64 clmuls.
    # clmul(6,6)=20, clmul(6,3)=10, 20 ^ 10 = 30.
    "xor_of_clmul": (
        _prog("simd_storeu(a, simd_xor(simd_clmul(x, x, 0), simd_clmul(x, y, 0)))"),
        30,
    ),
    # Swap the two i64 lanes of x and y: lane 0 = y[0] = 3.
    "shuffle": (_prog("simd_storeu(a, simd_shuffle(x, y, 2, 1))"), 3),
    # Lane 0 replaced by 42.
    "insert": (_prog("simd_storeu(a, simd_insert(x, 0, 42))"), 42),
    # 6 rotl 1 = 12 (64-bit lanes).
    "rotl": (_prog("simd_storeu(a, simd_rotl(x, 1))"), 12),
    # Nesting through a binop: xor(xor(x, y), y) = x = 6.
    "xor_of_xor": (_prog("simd_storeu(a, simd_xor(simd_xor(x, y), y))"), 6),
    # The first operand is a user fn call the resolver cannot type, so the
    # binop takes the second operand's type.  6 ^ 3 = 5.
    "xor_of_user_call": (
        "fn ld(p: *i64) -> v2i64\n    simd_loadu(p)\n\n"
        + _prog("simd_storeu(a, simd_xor(ld(a), y))"),
        5,
    ),
    # The ticket's shape 2: context-free simd_loadu as an aesenc operand.
    "aesenc_of_loadu": (_prog("simd_storeu(a, aesenc(simd_loadu(a), y))"), None),
    # A binop as aesenc's state operand.
    "aesenc_of_xor": (_prog("simd_storeu(a, aesenc(simd_xor(x, y), y))"), None),
}


def _ritz1_compile(tmp_path: Path, name: str, program: str) -> Path:
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
    return ll


def _ritz1_run(tmp_path: Path, name: str, program: str, ritz_start: Path) -> int:
    ll = _ritz1_compile(tmp_path, name, program)
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


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_matches_ritz0(ritz1_bin, ritz_start, ritz0_oracle, tmp_path, name):
    program, expected = PROGRAMS[name]
    oracle = ritz0_oracle(program)
    assert oracle.ir_ok, f"ritz0 rejected {name}:\n{oracle.diagnostics[-2000:]}"
    if expected is not None:
        assert oracle.rc == expected
    assert _ritz1_run(tmp_path, name, program, ritz_start) == oracle.rc


# The IR-level symptom: the simd_storeu (the only align-1 vector store; the
# `let` bindings' stores carry no alignment) must be typed as its value is.
STORE_TYPE = {
    "xor": "<2 x i64>",
    "add": "<2 x i64>",
    "xor_of_loadu": "<4 x i32>",
    "xor_of_clmul": "<2 x i64>",
    "shuffle": "<2 x i64>",
    "insert": "<2 x i64>",
    "rotl": "<2 x i64>",
    "xor_of_xor": "<2 x i64>",
    "xor_of_user_call": "<2 x i64>",
    "aesenc_of_loadu": "<4 x i32>",
    "aesenc_of_xor": "<2 x i64>",
}


@pytest.mark.parametrize("name", sorted(STORE_TYPE))
def test_ritz1_storeu_typed_as_value(ritz1_bin, tmp_path, name):
    ll = _ritz1_compile(tmp_path, name, PROGRAMS[name][0])
    body = ll.read_text().split("@use(", 1)[1].split("\n}\n", 1)[0]
    stores = [ln for ln in body.splitlines() if "store <" in ln and "align 1" in ln]
    assert len(stores) == 1 and f"store {STORE_TYPE[name]}" in stores[0], stores
