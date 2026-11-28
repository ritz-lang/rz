"""AGAST #4912, #4965: a Harland [[bin]] compiles for a fixed, AVX-free CPU.

Harland's kernel enables SSE only (it never sets CR4.OSXSAVE or XCR0), so any
VEX/EVEX instruction is #UD in a Harland process: buddhafinger died at
startup on a 256-byte `vmovdqu %ymm` struct copy.

#4912 added -mno-avx after -march=native. That is not enough: on an AVX10
build host (skronk-5's Xeon 6975P-C) -march=native passes `+avx10.1-512`,
which keeps AVX-512 on after `-avx`, and clang still copies with %ymm (#4965).
It also made an object depend on the build host while its store key said
only "-march=native". A Harland binary now names a fixed baseline,
HARLAND_MARCH, and no flag that reads the build host; other freestanding
binaries keep their flags and store keys.
"""

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))


@pytest.fixture(scope="module")
def buildpy():
    spec = importlib.util.spec_from_file_location("ritz_buildpy_4912", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bin(buildpy, tmp_path: Path, target_os: str):
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text("fn start() -> i32\n    0\n")
    os_line = f'target_os = "{target_os}"\n' if target_os else ""
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "pkg"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "b"\nentry = "main::start"\n'
        'target = "x86_64-unknown-none"\nfreestanding = true\n' + os_line)
    config = tomllib.loads((pkg / "ritz.toml").read_text())
    (bin_config,) = buildpy.get_binaries(pkg, config)
    return bin_config


def _harland_flags(buildpy, tmp_path):
    return list(buildpy.freestanding_target(_bin(buildpy, tmp_path / "h", "harland")).clang_flags)


@pytest.mark.unit
def test_harland_binaries_name_a_fixed_cpu_not_the_build_host(buildpy, tmp_path):
    flags = _harland_flags(buildpy, tmp_path)
    assert not any("native" in f for f in flags), flags
    assert [f for f in flags if f.startswith("-march=")] == [f"-march={buildpy.HARLAND_MARCH}"]
    assert "-mno-avx" in flags


@pytest.mark.unit
def test_harland_baseline_has_no_avx(buildpy):
    # x86-64-v3 and up are AVX2; v1/v2 are SSE-only.
    assert buildpy.HARLAND_MARCH in ("x86-64", "x86-64-v2")


@pytest.mark.unit
def test_harland_store_key_differs_from_the_native_one(buildpy, tmp_path):
    # An object compiled -march=native (any host, any #4912-era entry) can
    # never answer a Harland module's key.
    target = buildpy.freestanding_target(_bin(buildpy, tmp_path / "h", "harland"))
    assert "-march=native" not in target.key_flags["clang"]


@pytest.mark.unit
def test_other_freestanding_binaries_keep_their_flags(buildpy, tmp_path):
    flags = buildpy.freestanding_target(_bin(buildpy, tmp_path / "k", "")).clang_flags
    assert "-march=native" in flags
    assert "-mno-avx" not in flags


# A 256-byte struct copied by value, as ritz1 emits a move: an aggregate
# load and store, which clang lowers with %ymm when AVX is allowed.
COPY_LL = """
target triple = "x86_64-unknown-none"
%Big = type { [32 x i64] }
define void @copy(ptr %dst, ptr %src) {
  %v = load %Big, ptr %src
  store %Big %v, ptr %dst
  ret void
}
"""


def _copy_asm(tmp_path, flags):
    ll = tmp_path / "copy.ll"
    ll.write_text(COPY_LL)
    obj = tmp_path / "copy.o"
    subprocess.run(["clang", *flags, "-O2", "-c", str(ll), "-o", str(obj)], check=True)
    return subprocess.run(["objdump", "-d", str(obj)], capture_output=True, text=True,
                          check=True).stdout


@pytest.mark.integration
def test_a_large_copy_uses_no_ymm_with_the_harland_flags(buildpy, tmp_path):
    asm = _copy_asm(tmp_path, _harland_flags(buildpy, tmp_path))
    assert "%ymm" not in asm and "%zmm" not in asm
    assert "%xmm" in asm                    # SSE still copies it


@pytest.mark.integration
def test_mno_avx_alone_does_not_stop_an_avx10_host(tmp_path):
    # Why the baseline is fixed: #4912's `-march=native -mno-avx` on an
    # AVX10 host, stood in for by an explicit -mavx10.1 (what -march=native
    # passes there as +avx10.1-512; -march=graniterapids alone does not
    # reproduce it) so this means the same on every build host. If clang
    # ever makes -mno-avx win here, this goes red and the docstring above is
    # stale, not the fix.
    asm = _copy_asm(tmp_path, ["--target=x86_64-unknown-none", "-march=x86-64-v2",
                               "-mavx10.1", "-mno-avx"])
    assert "%ymm" in asm or "%zmm" in asm
