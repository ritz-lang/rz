"""AGAST #4607: a freestanding module's triple reaches ritz1 as it does ritz0.

ritz0 and ritz1 stop a trap or a failing assert through ritz_platform_fatal
when --target is freestanding (ritz0/tests/test_integer_overflow_traps.py's
freestanding rows), so build.py must pass the triple to whichever compiler
builds a kernel module.  Before this only ritz0 got it: ritz1's kernel IR
exited through a syscall.  A hosted module passes none.
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

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


@pytest.fixture(scope="module")
def buildpy():
    spec = importlib.util.spec_from_file_location("ritz_buildpy_4607", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kernel_target(buildpy, tmp_path: Path):
    pkg = tmp_path / "kpkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text("fn kmain() -> i32\n    0\n")
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "kpkg"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "k"\nentry = "main::kmain"\n'
        'target = "x86_64-none-elf"\nfreestanding = true\n')
    config = tomllib.loads((pkg / "ritz.toml").read_text())
    (bin_config,) = buildpy.get_binaries(pkg, config)
    return buildpy.freestanding_target(bin_config), pkg / "src" / "main.ritz"


def _with_binaries(buildpy, monkeypatch, tmp_path):
    """Stand-in ritz1 binaries, so the command is built without a bootstrap."""
    bins = {}
    for name, (_, hint) in buildpy.RITZ1_FAMILY_BINS.items():
        fake = tmp_path / name
        fake.write_text("")
        bins[name] = (fake, hint)
    monkeypatch.setattr(buildpy, "RITZ1_FAMILY_BINS", bins)


def _target_arg(cmd):
    assert cmd.count("--target") <= 1, cmd
    return cmd[cmd.index("--target") + 1] if "--target" in cmd else None


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_kernel_module_passes_its_triple(buildpy, monkeypatch, tmp_path, compiler):
    _with_binaries(buildpy, monkeypatch, tmp_path)
    target, src = _kernel_target(buildpy, tmp_path)
    cmd = buildpy.module_compile_cmd(compiler, src, tmp_path / "m.ll", target)
    assert _target_arg(cmd) == "x86_64-none-elf", cmd


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_hosted_module_passes_none(buildpy, monkeypatch, tmp_path, compiler):
    _with_binaries(buildpy, monkeypatch, tmp_path)
    src = tmp_path / "main.ritz"
    src.write_text("fn main() -> i32\n    0\n")
    cmd = buildpy.module_compile_cmd(compiler, src, tmp_path / "m.ll", buildpy.HOSTED)
    assert _target_arg(cmd) is None, cmd
