"""AGAST #4912: a Harland [[bin]] compiles without AVX.

Freestanding objects compile with -march=native, so clang may use the build
host's AVX, e.g. to copy a large struct. Harland's kernel enables SSE only
(it never sets CR4.OSXSAVE or XCR0), so any AVX instruction is #UD in a
Harland process: buddhafinger died at startup on a 256-byte `vmovups %ymm`.
A `target_os = "harland"` binary adds -mno-avx after -march=native; other
freestanding binaries keep their flags and store keys.
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


@pytest.mark.unit
def test_harland_binaries_drop_avx_after_native(buildpy, tmp_path):
    flags = list(buildpy.freestanding_target(_bin(buildpy, tmp_path / "h", "harland")).clang_flags)
    assert "-mno-avx" in flags
    assert flags.index("-mno-avx") > flags.index("-march=native")


@pytest.mark.unit
def test_other_freestanding_binaries_keep_their_flags(buildpy, tmp_path):
    flags = buildpy.freestanding_target(_bin(buildpy, tmp_path / "k", "")).clang_flags
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


@pytest.mark.integration
def test_a_large_copy_uses_no_ymm_with_the_harland_flags(buildpy, tmp_path):
    ll = tmp_path / "copy.ll"
    ll.write_text(COPY_LL)
    flags = list(buildpy.freestanding_target(_bin(buildpy, tmp_path / "h", "harland")).clang_flags)
    # Stand-in for an AVX build host, so the test means the same everywhere.
    flags = [f if f != "-march=native" else "-march=x86-64-v3" for f in flags]
    obj = tmp_path / "copy.o"
    subprocess.run(["clang", *flags, "-O2", "-c", str(ll), "-o", str(obj)], check=True)
    asm = subprocess.run(["objdump", "-d", str(obj)], capture_output=True, text=True, check=True).stdout
    assert "%ymm" not in asm and "%zmm" not in asm
    assert "%xmm" in asm                    # SSE still copies it
