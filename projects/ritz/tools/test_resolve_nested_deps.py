"""AGAST #1835: `rz` and build.py resolve a package's dependencies alike.

`rz`'s collect_dependency_paths (the RITZ_PATH a build.py child gets) only
followed a dependency's own dependencies when it sat directly under
projects/. A nested package (projects/x/y, a workspace member since
AGAST #1383) contributed its directory but none of its dependencies, and
string-shorthand dependencies (`z = "../../z"`, which build.py accepts)
were dropped. build.py's get_transitive_dependencies followed both.

Both now come from one resolver, resolve.py.

The tree:  a/b -> c -> x/y -> z  (x/y -> z is shorthand), plus a/b -> x/y
directly, so the walk meets x/y twice and must not list it twice.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RZ_PATH = PKG_DIR.parents[1] / "rz"


@pytest.fixture(scope="module")
def rz():
    loader = importlib.machinery.SourceFileLoader("rz_cli_1835", str(RZ_PATH))
    spec = importlib.util.spec_from_loader("rz_cli_1835", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_resolve", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _package(projects, rel, deps):
    pkg = projects / rel
    (pkg / "src").mkdir(parents=True)
    body = "".join(f"{name} = {spec}\n" for name, spec in deps.items())
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "{pkg.name}"\nversion = "0.1.0"\n\n[dependencies]\n{body}')
    return pkg


@pytest.fixture
def workspace(tmp_path, rz, monkeypatch):
    projects = tmp_path / "projects"
    _package(projects, "a/b", {"c": '{ path = "../../c" }', "y": '{ path = "../../x/y" }'})
    _package(projects, "c", {"y": '{ path = "../x/y" }'})
    _package(projects, "x/y", {"z": '"../../z"'})
    _package(projects, "z", {})
    monkeypatch.setattr(rz, "PROJECTS_DIR", projects)
    return projects


@pytest.mark.unit
def test_rz_follows_a_nested_dependencys_dependencies(rz, workspace):
    paths = [p.resolve() for p in rz.collect_dependency_paths("a/b")]
    assert (workspace / "z").resolve() in paths, \
        "x/y's dependency z is missing from RITZ_PATH: nested packages not followed"
    assert len(paths) == len(set(paths)), "a package reached twice was listed twice"


@pytest.mark.unit
def test_rz_and_buildpy_resolve_the_same_packages(rz, buildpy, workspace):
    import tomllib
    root = workspace / "a" / "b"
    config = tomllib.loads((root / "ritz.toml").read_text())
    from_build = {spec.path.resolve()
                  for spec in buildpy.get_transitive_dependencies(root, config).values()}
    from_rz = {p.resolve() for p in rz.collect_dependency_paths("a/b")}
    assert from_rz == {root.resolve()} | from_build
    assert from_build == {(workspace / p).resolve() for p in ("c", "x/y", "z")}


@pytest.mark.unit
def test_rz_keeps_the_depth_first_order(rz, workspace):
    # RITZ_PATH is searched in order, so the order is part of the contract:
    # the package, then each dependency followed by its own, as before.
    got = [p.resolve().relative_to(workspace.resolve()).as_posix()
           for p in rz.collect_dependency_paths("a/b")]
    assert got == ["a/b", "c", "x/y", "z"]
