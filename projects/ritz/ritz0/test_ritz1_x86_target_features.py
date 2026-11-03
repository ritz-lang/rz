"""AGAST #1737: ritz1 gives a function that calls an x86 ISA-extension
intrinsic the matching "target-features", so `clang -c -O2 x.ll` can lower it.

THE DEFECT

ritz0 has done this since #1736 (and has pinned "target-cpu" since #1921), see
test_ritz0_x86_target_features.py. ritz1 emitted the same
`llvm.x86.sha256rnds2` / `llvm.x86.aesni.*` / `llvm.x86.pclmulqdq` calls in
functions carrying only `alignstack(16) "no-builtins"`. Without -msha / -maes
/ -mpclmul on clang's command line, and build.py passes none, instruction
selection aborts:

    fatal error: error in backend: Cannot select: intrinsic %llvm.x86.sha256msg2
    clang: error: clang frontend command failed with exit code 70

so `build.py --compiler ritz1` could not build cryptosec or anything that
depends on it.

THE FIX

After a fn or impl method body is emitted (ritz1/src/emitter.ritz), the body
text is scanned for calls to those intrinsics, and the define line gains
`"target-cpu"="x86-64" "target-features"="+..."` for exactly the features the
body uses, matching ritz0 attribute for attribute. Functions that call none
are left alone, so the rest of the module stays baseline x86-64 and the
runtime CPU check (cpu_has_sha_ni etc.) still decides what executes.

Same program, same clang flags and same bounds (RLIMIT_AS + timeout) as the
ritz0 test, with the compile step done by ritz1.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ritz0_x86_target_features import (
    BASELINE_CPU,
    CLANG_TIMEOUT_S,
    CRYPTOSEC,
    MASKED_NATIVE,
    OBJ_FLAGS,
    PROGRAM,
    _clang_obj,
    _crash_head,
    _disasm_by_fn,
    _limit_mem,
)

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

pytestmark = pytest.mark.integration

# The same three intrinsics called from impl methods, which ritz1 emits
# through a separate define path (emit_impl_method, mangled Type_method).
IMPL_PROGRAM = """\
struct Ctx
    pad: i64

impl Ctx
    fn sha(self: *Ctx, a: *i32, b: *i32, c: *i32) -> i32
        let x: v4i32 = simd_loadu(a)
        let y: v4i32 = simd_loadu(b)
        let z: v4i32 = simd_loadu(c)
        simd_storeu(a, sha256rnds2(x, y, z))
        0

    fn aes(self: *Ctx, a: *i32, b: *i32) -> i32
        let s: v4i32 = simd_loadu(a)
        let k: v4i32 = simd_loadu(b)
        simd_storeu(a, aesenc(s, k))
        0

    fn clmul(self: *Ctx, a: *i64, b: *i64) -> i32
        let x: v2i64 = simd_loadu(a)
        let y: v2i64 = simd_loadu(b)
        # Nested on purpose: stored as <4 x i32> before #2051.
        simd_storeu(a, simd_clmul(x, y, 0))
        0

    fn plain(self: *Ctx) -> i32
        1

fn main() -> i32
    var ctx: Ctx
    var a: [4]i32
    var b: [4]i32
    var c: [4]i32
    var p: [2]i64
    var q: [2]i64
    ctx.sha(@a[0], @b[0], @c[0])
    ctx.aes(@a[0], @b[0])
    ctx.clmul(@p[0], @q[0])
    ctx.plain()
"""

FREE_FNS = {"use_sha": "+sha", "use_aes": "+aes", "use_clmul": "+pclmul"}
IMPL_FNS = {"Ctx_sha": "+sha", "Ctx_aes": "+aes", "Ctx_clmul": "+pclmul"}
ALL_FEATURES = {"+sha", "+aes", "+pclmul"}


def _env() -> dict:
    # build.py's ritz1_env: ritzlib under ROOT, cross-project imports
    # (cryptosec.cpuid) under ROOT.parent.
    return dict(
        os.environ, RITZ_PATH=os.pathsep.join([str(RITZ_ROOT), str(RITZ_ROOT.parent)])
    )


def _ritz1(src: Path, ll: Path) -> None:
    # build.py's ritz1_compile_cmd.
    r = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        env=_env(),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0 and ll.exists(), (
        f"ritz1 failed on {src.name}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    )


def _define_attrs(ir: str, fn: str) -> str:
    """The attribute text after the parameter list of fn's `define` line.

    ritz1 spells names bare (`@use_sha(`), ritz0 quotes them; accept both.
    """
    for line in ir.splitlines():
        if not line.startswith("define"):
            continue
        for head in (f"@{fn}(", f'@"{fn}"('):
            at = line.find(head)
            if at < 0:
                continue
            # Skip to the paren closing the parameter list (attributes such
            # as alignstack(16) carry parens of their own).
            depth, i = 0, at + len(head) - 1
            while i < len(line):
                depth += {"(": 1, ")": -1}.get(line[i], 0)
                if depth == 0:
                    break
                i += 1
            return line[i + 1 :].rsplit("{", 1)[0]
    raise AssertionError(f"no define for @{fn}")


def _features(ir: str, fn: str) -> set:
    m = re.search(r'"target-features"="([^"]*)"', _define_attrs(ir, fn))
    return set(m.group(1).split(",")) if m else set()


def _cpu(ir: str, fn: str):
    m = re.search(r'"target-cpu"="([^"]*)"', _define_attrs(ir, fn))
    return m.group(1) if m else None


def _compile(tmp_path_factory, name: str, program: str) -> Path:
    d = tmp_path_factory.mktemp(name)
    src = d / f"{name}.ritz"
    src.write_text(program)
    ll = d / f"{name}.ll"
    _ritz1(src, ll)
    return ll


@pytest.fixture(scope="module")
def program_ll(ritz1_bin, tmp_path_factory) -> Path:
    return _compile(tmp_path_factory, "intrinsics", PROGRAM)


@pytest.fixture(scope="module")
def impl_ll(ritz1_bin, tmp_path_factory) -> Path:
    return _compile(tmp_path_factory, "impl_intrinsics", IMPL_PROGRAM)


def _ll(request, which: str) -> str:
    return request.getfixturevalue(which).read_text()


CASES = [("program_ll", fn, feat) for fn, feat in FREE_FNS.items()] + [
    ("impl_ll", fn, feat) for fn, feat in IMPL_FNS.items()
]
BASELINE = [
    ("program_ll", "plain"),
    ("program_ll", "main"),
    ("impl_ll", "Ctx_plain"),
    ("impl_ll", "main"),
]


@pytest.mark.parametrize("which,fn,feature", CASES)
def test_intrinsic_caller_carries_its_feature(request, which, fn, feature):
    feats = _features(_ll(request, which), fn)
    assert feature in feats, (
        f"@{fn} calls an intrinsic that needs {feature} but its "
        f"target-features are {sorted(feats) or 'absent'}"
    )


@pytest.mark.parametrize("which,fn,feature", CASES)
def test_feature_is_only_what_the_function_uses(request, which, fn, feature):
    """+sha must not leak into the AES function, and so on."""
    feats = _features(_ll(request, which), fn)
    assert feats == {feature}, f"@{fn}: want {{{feature}}}, got {sorted(feats)}"


@pytest.mark.parametrize("which,fn,feature", CASES)
def test_intrinsic_caller_pins_baseline_cpu(request, which, fn, feature):
    """AGAST #1921: target-features replaces -march's mask, so pin the CPU."""
    cpu = _cpu(_ll(request, which), fn)
    assert cpu == BASELINE_CPU, f"@{fn} has target-features but target-cpu={cpu!r}"


@pytest.mark.parametrize("which,fn", BASELINE)
def test_functions_without_intrinsics_stay_baseline(request, which, fn):
    ir = _ll(request, which)
    assert not _features(ir, fn) and _cpu(ir, fn) is None, (
        f"@{fn} calls no ISA-extension intrinsic but gained target attributes"
    )


@pytest.mark.parametrize("which", ["program_ll", "impl_ll"])
def test_define_line_keeps_its_other_attributes(request, which):
    """The attributes are spliced in, not swapped for the existing ones."""
    for fn in FREE_FNS if which == "program_ll" else IMPL_FNS:
        attrs = _define_attrs(_ll(request, which), fn)
        assert 'alignstack(16) "no-builtins"' in attrs, f"@{fn}: {attrs!r}"


@pytest.mark.parametrize("which", ["program_ll", "impl_ll"])
def test_program_compiles_at_O2_without_march_flags(request, which):
    r = _clang_obj(request.getfixturevalue(which))
    assert r.returncode == 0, (
        f"clang {' '.join(OBJ_FLAGS)} failed on ritz1 IR:\n{_crash_head(r.stderr)}"
    )


def test_intrinsic_fns_honour_masked_native_features(program_ll, tmp_path):
    """No AVX encoding in an intrinsic fn when the command line masks AVX."""
    obj = tmp_path / "masked.o"
    r = subprocess.run(
        ["clang", *OBJ_FLAGS, *MASKED_NATIVE, str(program_ll), "-o", str(obj)],
        capture_output=True,
        text=True,
        timeout=CLANG_TIMEOUT_S,
        preexec_fn=_limit_mem,
    )
    assert r.returncode == 0, _crash_head(r.stderr)
    fns = _disasm_by_fn(obj)
    for fn in FREE_FNS:
        assert fn in fns, f"no {fn} in {sorted(fns)}"
        avx = [ins for ins in fns[fn] if ins.startswith("v")]
        assert not avx, f"{fn} uses AVX under {' '.join(MASKED_NATIVE)}: {avx[:4]}"


# aes and aes_gcm import cryptosec.mem, whose mem_zero holds an `asm x86_64:`
# block that ritz1 cannot parse yet (AGAST #1455). Strict, so the test turns
# red once ritz1 has asm and it must be un-xfailed.
_NEEDS_RITZ1_ASM = pytest.mark.xfail(
    strict=True,
    reason="ritz1 cannot parse cryptosec/lib/mem.ritz's asm block (AGAST #1455)",
)


@pytest.mark.skipif(not CRYPTOSEC.is_dir(), reason="cryptosec not checked out")
@pytest.mark.parametrize(
    "name",
    [
        "sha256",
        pytest.param("aes", marks=_NEEDS_RITZ1_ASM),
        pytest.param("aes_gcm", marks=_NEEDS_RITZ1_ASM),
    ],
)
def test_cryptosec_source_compiles_at_O2_without_march_flags(ritz1_bin, tmp_path, name,
                                                           monkeypatch):
    # A private, empty store (AGAST #1901): with mem.ritz's interface text
    # stored, ritz1 parses that -- mem_zero's asm body emptied -- and never
    # meets the asm, so the xfail would depend on what the cache holds.
    monkeypatch.setenv("RITZ_CACHE_DIR", str(tmp_path / "cas"))
    ll = tmp_path / f"{name}.ll"
    _ritz1(CRYPTOSEC / "lib" / f"{name}.ritz", ll)
    r = _clang_obj(ll)
    assert r.returncode == 0, (
        f"clang -c -O2 crashed on ritz1's cryptosec/lib/{name}.ritz:\n"
        f"{_crash_head(r.stderr)}"
    )
