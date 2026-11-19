"""AGAST #4308: `[bin.NAME.flags] no-red-zone = true` reaches the compiler.

`-mno-red-zone` on clang's command line does nothing for .ll input, so the
compilers' `--no-red-zone` (ritz0/test_no_red_zone.py) must put `noredzone`
in the IR. build.py passes it for a [[bin]] that sets the flag and keys the
artifact store on it, since the IR differs (store entries written before
the fix carry red-zone code under the old key). A binary without it keeps
the store key it had before.
"""

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def buildpy():
    spec = importlib.util.spec_from_file_location("ritz_buildpy_4308", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kernel_bin(buildpy, tmp_path: Path, flags: str, target: str = "x86_64-none-elf"):
    pkg = tmp_path / "kpkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text("fn kmain() -> i32\n    0\n")
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "kpkg"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "k"\nentry = "main::kmain"\n'
        f'target = "{target}"\nfreestanding = true\n\n'
        f'[bin.k.flags]\n{flags}\n')
    config = tomllib.loads((pkg / "ritz.toml").read_text())
    (bin_config,) = buildpy.get_binaries(pkg, config)
    return bin_config


def test_flag_reaches_the_compiler_and_the_store_key(buildpy, tmp_path):
    on = buildpy.freestanding_target(_kernel_bin(buildpy, tmp_path / "a", "no-red-zone = true"))
    off = buildpy.freestanding_target(_kernel_bin(buildpy, tmp_path / "b", 'code-model = "large"'))
    assert "--no-red-zone" in on.compiler_args()
    assert "--no-red-zone" not in off.compiler_args()
    assert on.key_flags.get("no_red_zone") is True
    # Unchanged for every binary that doesn't opt in (indium's), so its
    # store entries stay valid.
    assert "no_red_zone" not in off.key_flags


def test_hosted_target_passes_nothing(buildpy):
    assert "--no-red-zone" not in buildpy.HOSTED.compiler_args()
    assert buildpy.HOSTED.key_flags is None


def test_harland_kernel_opts_in():
    cfg = tomllib.loads((PKG_DIR.parent / "harland" / "ritz.toml").read_text())
    (kernel,) = [b for b in cfg["bin"] if b["name"] == "harland"]
    assert kernel["harland"]["flags"].get("no-red-zone") is True


def test_harland_boot_test_runs_the_checker():
    boot = (PKG_DIR.parent / "harland" / "tools" / "test_tier1_boot.sh").read_text()
    assert "check_no_red_zone.py" in boot
