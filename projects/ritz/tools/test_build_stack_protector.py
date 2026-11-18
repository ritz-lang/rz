"""AGAST #2590: `[bin.NAME.flags] stack-protector = true` reaches the compiler.

The compilers' `--stack-protector` (ritz0/test_stack_protector.py) is opt-in
per [[bin]]: a freestanding binary that turns it on must define
`__stack_chk_guard` and `__stack_chk_fail`, so it cannot be the default.
build.py reads the key, passes the flag to ritz0 or ritz1, and keys the
artifact store on it, since the IR differs. A binary without it keeps the
store key it had before the key existed.
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
    spec = importlib.util.spec_from_file_location("ritz_buildpy_2590", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kernel_pkg(tmp_path: Path, flags: str) -> Path:
    pkg = tmp_path / "kpkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text("fn kmain() -> i32\n    0\n")
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "kpkg"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "k"\nentry = "main::kmain"\n'
        'target = "x86_64-none-elf"\nfreestanding = true\n\n'
        f'[bin.k.flags]\n{flags}\n')
    return pkg


def _kernel_bin(buildpy, tmp_path, flags):
    pkg = _kernel_pkg(tmp_path, flags)
    config = tomllib.loads((pkg / "ritz.toml").read_text())
    (bin_config,) = buildpy.get_binaries(pkg, config)
    return bin_config


def test_flag_reaches_the_compiler_and_the_store_key(buildpy, tmp_path):
    on = buildpy.freestanding_target(_kernel_bin(buildpy, tmp_path / "a", "stack-protector = true"))
    off = buildpy.freestanding_target(_kernel_bin(buildpy, tmp_path / "b", "no-red-zone = true"))
    assert "--stack-protector" in on.compiler_args()
    assert "--stack-protector" not in off.compiler_args()
    assert on.key_flags.get("stack_protector") is True
    # Unchanged for every existing binary, so its store entries stay valid.
    assert "stack_protector" not in off.key_flags
