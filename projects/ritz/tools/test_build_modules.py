"""AGAST #3632: build.py is an entry point over manifest / build_pipeline /
build_testrun / build_cli, and still stands for all of them.

Tests and tools use build.py as one module: they read `build.X`, and they
monkeypatch `build.X` expecting the code that calls X (now in another
module) to see the patch. They also load it by path for a fresh copy of its
state. These pin each of those.
"""

import importlib.util
import itertools
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

_LOADS = itertools.count()


def _load_build():
    """build.py as the tests load it: by path, not registered in sys.modules."""
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_3632_{next(_LOADS)}", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def buildpy():
    return _load_build()


@pytest.mark.unit
def test_reads_come_from_the_defining_module(buildpy):
    assert buildpy.compile_modules is buildpy.build_pipeline.compile_modules
    assert buildpy.plan_binaries is buildpy.manifest.plan_binaries
    assert buildpy.run_tests is buildpy.build_testrun.run_tests
    assert buildpy.cmd_build is buildpy.build_cli.cmd_build
    assert buildpy.DependencySpec is buildpy.resolve.DependencySpec


@pytest.mark.unit
def test_a_counter_the_pipeline_bumps_reads_current(buildpy):
    buildpy.build_pipeline.CLANG_OBJ_FAILURES += 3
    assert buildpy.CLANG_OBJ_FAILURES == 3


@pytest.mark.unit
def test_a_patch_reaches_callers_in_other_modules(buildpy, monkeypatch):
    """build_cli calls build_package by the name it imported; patching
    `build.build_package` must rebind that name too, and undo must restore."""
    real = buildpy.build_package
    fake = object()
    monkeypatch.setattr(buildpy, "build_package", fake)
    assert buildpy.build_pipeline.build_package is fake
    assert buildpy.build_testrun.build_package is fake
    assert buildpy.build_cli.build_package is fake
    monkeypatch.undo()
    assert buildpy.build_cli.build_package is real
    assert buildpy.build_pipeline.build_package is real


@pytest.mark.unit
def test_each_load_has_its_own_state():
    """As one file, every load had its own globals; fixtures rely on that
    (a fresh failure counter, a fresh build cache)."""
    a, b = _load_build(), _load_build()
    assert a.build_pipeline is not b.build_pipeline
    a.build_pipeline.CLANG_OBJ_FAILURES += 1
    assert b.CLANG_OBJ_FAILURES == 0
    assert a.get_build_cache("ritz0") is not b.get_build_cache("ritz0")


@pytest.mark.unit
def test_a_later_load_leaves_the_registered_modules_alone():
    _load_build()
    registered = sys.modules["build_pipeline"]
    later = _load_build()
    assert sys.modules["build_pipeline"] is registered
    assert later.build_pipeline is not registered


@pytest.mark.unit
def test_main_is_the_build_command_line(buildpy):
    # manifest.py has a `main` too: the spec generator.
    assert buildpy.main is buildpy.build_cli.main


@pytest.mark.unit
def test_no_other_name_is_defined_twice(buildpy):
    """A name two modules define differently would read from whichever the
    facade searches first: `main` did. Only that one is resolved by hand."""
    seen, clashes = {}, set()
    for mod in buildpy._MODULES:
        for name, value in vars(mod).items():
            if name.startswith("__"):
                continue
            if name in seen and seen[name] is not value:
                clashes.add(name)
            seen.setdefault(name, value)
    assert clashes == {"main"}


@pytest.mark.unit
def test_the_test_runner_gets_this_build_module(buildpy):
    assert buildpy.build_testrun.BUILD_MODULE is buildpy


@pytest.mark.integration
def test_build_py_is_still_the_entry_point(tmp_path):
    r = subprocess.run([sys.executable, str(PKG_DIR / "build.py"), "list"],
                       cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "No packages found" in r.stdout
