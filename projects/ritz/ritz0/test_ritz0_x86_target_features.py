"""AGAST #1736: a function that calls an x86 ISA-extension intrinsic carries
the matching "target-features", so `clang -c -O2 x.ll` can lower it.

THE DEFECT

cryptosec's sha256/aes/aes_gcm call `llvm.x86.sha256rnds2`,
`llvm.x86.aesni.*` and `llvm.x86.pclmulqdq`. ritz0 emitted those calls in
functions with no target-features, so the backend has only the baseline
x86-64 ISA. Without `-msha`, `-maes` or `-mpclmul` on the clang command line,
instruction selection aborts:

    fatal error: error in backend: Cannot select: intrinsic %llvm.x86.sha256rnds2
    clang: error: clang frontend command failed with exit code 70

build.py's link step passes `-march=native -msha`, and that is what the old
.ll fallback leaned on: the per-source `clang -c -O2` crashed, and the link
re-lowered the .ll with those flags. #1731 removed the fallback, so the crash
failed goliath, mausoleum, nexus, tome and valet on CI.

THE FIX

The emitter records the CPU features each intrinsic needs. Every function that
calls one gets `"target-features"="+..."`, the same attribute clang gives a C
function marked `__attribute__((target("sha")))`. The IR describes itself,
so any consumer can compile it whatever its flags. Only those functions gain
the feature. The rest of the module stays baseline x86-64, so the runtime
dispatch (cpu_has_sha_ni etc.) is still what decides whether the
instructions run.

Every clang run here is bounded (RLIMIT_AS + timeout) and uses exactly
build.py's object-compile flags, without -march/-msha.
"""

import json
import os
import re
import resource
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
PROJECTS = RITZ_ROOT.parent
RITZ0 = RITZ0_DIR / "ritz0.py"

# build.py's compile_ll_to_obj flags (AGAST #1731), and nothing else. In
# particular no -march=native / -msha / -maes / -mpclmul.
OBJ_FLAGS = ["-c", "-O2", "-fPIC", "-ffreestanding", "-fno-builtin",
             "-Wno-override-module"]
CLANG_TIMEOUT_S = 120
CLANG_MEM_BYTES = 2 * 1024 * 1024 * 1024

PROGRAM = """\
fn use_sha(a: *i32, b: *i32, c: *i32) -> i32
    let x: v4i32 = simd_loadu(a)
    let y: v4i32 = simd_loadu(b)
    let z: v4i32 = simd_loadu(c)
    let r1: v4i32 = sha256rnds2(x, y, z)
    let r2: v4i32 = sha256msg1(r1, y)
    let r3: v4i32 = sha256msg2(r2, z)
    simd_storeu(a, r3)
    0

fn use_aes(a: *i32, b: *i32) -> i32
    let s: v4i32 = simd_loadu(a)
    let k: v4i32 = simd_loadu(b)
    let r: v4i32 = aesenc(s, k)
    simd_storeu(a, aesenclast(r, k))
    0

fn use_clmul(a: *i64, b: *i64) -> i32
    let x: v2i64 = simd_loadu(a)
    let y: v2i64 = simd_loadu(b)
    let r: v2i64 = simd_clmul(x, y, 0)
    simd_storeu(a, r)
    0

fn plain(n: i32) -> i32
    n + 1

fn main() -> i32
    var a: [4]i32
    var b: [4]i32
    var c: [4]i32
    var p: [2]i64
    var q: [2]i64
    use_sha(@a[0], @b[0], @c[0])
    use_aes(@a[0], @b[0])
    use_clmul(@p[0], @q[0])
    plain(1)
"""


def _limit_mem() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (CLANG_MEM_BYTES, CLANG_MEM_BYTES))


def _ritz0(src: Path, ll: Path, *extra: str) -> None:
    r = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(ll), *extra],
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0 and ll.exists(), (
        f"ritz0 failed on {src.name}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")


def _clang_obj(ll: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["clang", *OBJ_FLAGS, str(ll), "-o", str(ll.with_suffix(".o"))],
            capture_output=True, text=True, timeout=CLANG_TIMEOUT_S,
            preexec_fn=_limit_mem,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([], -9, "", "clang timed out")


def _crash_head(stderr: str) -> str:
    keep = [ln for ln in stderr.splitlines()
            if re.search(r"error|Running pass|LLVM ERROR", ln)]
    return "\n".join(keep[:12]) or stderr[-2000:]


def _define_attrs(ir: str, fn: str) -> str:
    """The attribute text of `define ... @"fn"(...) <attrs>`."""
    for line in ir.splitlines():
        if line.startswith("define") and f'@"{fn}"(' in line:
            return line.split(")", 1)[1] if ")" in line else ""
    raise AssertionError(f"no define for @{fn}")


def _features(ir: str, fn: str) -> set:
    m = re.search(r'"target-features"="([^"]*)"', _define_attrs(ir, fn))
    return set(m.group(1).split(",")) if m else set()


@pytest.fixture(scope="module")
def program_ll(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("tf")
    src = d / "intrinsics.ritz"
    src.write_text(PROGRAM)
    ll = d / "intrinsics.ll"
    # --no-runtime (as build.py compiles): every fn is external, so -O2
    # cannot inline the intrinsic callers into main and delete them before
    # instruction selection ever sees the intrinsics.
    _ritz0(src, ll, "--no-runtime")
    return ll


@pytest.mark.unit
@pytest.mark.parametrize("fn,feature", [
    ("use_sha", "+sha"),
    ("use_aes", "+aes"),
    ("use_clmul", "+pclmul"),
])
def test_intrinsic_caller_carries_its_feature(program_ll, fn, feature):
    feats = _features(program_ll.read_text(), fn)
    assert feature in feats, (
        f"@{fn} calls an intrinsic that needs {feature} but its "
        f"target-features are {sorted(feats) or 'absent'}")


@pytest.mark.unit
@pytest.mark.parametrize("fn", ["use_sha", "use_aes", "use_clmul"])
def test_feature_is_only_what_the_function_uses(program_ll, fn):
    """+sha must not leak into the AES function, and so on."""
    want = {"use_sha": "+sha", "use_aes": "+aes", "use_clmul": "+pclmul"}[fn]
    feats = _features(program_ll.read_text(), fn)
    others = {"+sha", "+aes", "+pclmul"} - {want}
    assert not (feats & others), f"@{fn} gained unrelated features {feats & others}"


@pytest.mark.unit
@pytest.mark.parametrize("fn", ["plain", "main"])
def test_functions_without_intrinsics_stay_baseline(program_ll, fn):
    assert not _features(program_ll.read_text(), fn), (
        f"@{fn} calls no ISA-extension intrinsic but gained target-features")


@pytest.mark.integration
def test_program_compiles_at_O2_without_march_flags(program_ll):
    r = _clang_obj(program_ll)
    assert r.returncode == 0, (
        f"clang {' '.join(OBJ_FLAGS)} failed on ritz0 IR:\n{_crash_head(r.stderr)}")


# The ticket's crashing sources, compiled the way build.py compiles a
# dependency of goliath/mausoleum/nexus/tome/valet.
CRYPTOSEC = PROJECTS / "cryptosec"
CRYPTOSEC_DEPS = json.dumps(
    {"cryptosec": {"path": str(CRYPTOSEC), "sources": ["lib"]}})


@pytest.mark.integration
@pytest.mark.skipif(not CRYPTOSEC.is_dir(), reason="cryptosec not checked out")
@pytest.mark.parametrize("name", ["sha256", "aes", "aes_gcm"])
def test_cryptosec_source_compiles_at_O2_without_march_flags(tmp_path, name):
    ll = tmp_path / f"{name}.ll"
    _ritz0(CRYPTOSEC / "lib" / f"{name}.ritz", ll, "--no-runtime",
           "--deps", CRYPTOSEC_DEPS, "--project-root", str(CRYPTOSEC))
    r = _clang_obj(ll)
    assert r.returncode == 0, (
        f"clang -c -O2 crashed on cryptosec/lib/{name}.ritz:\n{_crash_head(r.stderr)}")
