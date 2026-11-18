"""Dead tooling stays deleted (AGAST #1836, LARB tooling F5/F7).

`rz` carried ~1,000 lines nothing called: `run_pipeline` (the only
`shell=True`), the `compile_with_*` / `link_llvm_ir` group, `rz ci
plan/run/generate` with three provider templates, and `rz compare`.
`packaging.py` (902 lines) backed `build.py install/uninstall/global-*/lock/
vendor`, which had no user, and its module name shadowed PyPI `packaging`.
git keeps all of it. These tests fail if any of it comes back unnoticed.
"""

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parents[1]
RZ_PATH = REPO_ROOT / "rz"
BUILD_PY = PKG_DIR / "build.py"

# The commands `rz` keeps: the gate uses build/test/cache, rzrz delegates
# run/clean, and list is the workspace inventory.
RZ_COMMANDS = {"build", "test", "run", "list", "clean", "cache"}

DELETED_RZ_SYMBOLS = (
    "run_pipeline", "compile_with_ritz1", "compile_with_ritz0", "link_llvm_ir",
    "detect_main_params", "runtime_obj_for", "cmd_compare", "cmd_ci",
    "cmd_ci_plan", "cmd_ci_run", "cmd_ci_generate", "compute_impacted_projects",
)


def _load_rz():
    loader = importlib.machinery.SourceFileLoader("rz_cli_1836", str(RZ_PATH))
    spec = importlib.util.spec_from_loader("rz_cli_1836", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_rz_offers_only_the_kept_commands():
    parser = _load_rz().build_parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    assert set(sub.choices) == RZ_COMMANDS


@pytest.mark.unit
@pytest.mark.parametrize("symbol", DELETED_RZ_SYMBOLS)
def test_rz_dead_symbol_is_gone(symbol):
    assert not hasattr(_load_rz(), symbol)


@pytest.mark.unit
def test_rz_never_shells_out_through_a_shell():
    assert "shell=True" not in RZ_PATH.read_text()


@pytest.mark.unit
@pytest.mark.parametrize("argv", [["compare"], ["ci", "plan"]])
def test_rz_rejects_deleted_subcommands(argv):
    r = subprocess.run([sys.executable, str(RZ_PATH), *argv],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 2
    assert "invalid choice" in r.stderr


@pytest.mark.unit
def test_packaging_module_is_gone():
    assert not (PKG_DIR / "packaging.py").exists()
    # build.py and the modules it was split into (AGAST #3632).
    for src in sorted(PKG_DIR.glob("build*.py")):
        assert "from packaging import" not in src.read_text(), src.name


@pytest.mark.unit
@pytest.mark.parametrize("cmd", ["install", "uninstall", "global-list",
                                 "global-cache", "lock", "vendor"])
def test_build_py_rejects_packaging_commands(cmd):
    r = subprocess.run([sys.executable, str(BUILD_PY), cmd],
                       capture_output=True, text=True, timeout=60, cwd=PKG_DIR)
    assert r.returncode == 2
    assert "invalid choice" in r.stderr
