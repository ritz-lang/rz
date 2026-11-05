"""Tests for tools/check_liveness.py (AGAST #1822).

Runs in `make tools-unit` (`pytest tools/`), and `test_real_tree_is_live` is
what puts the guard itself in that target: an orphan in ritz0/ fails there.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import check_liveness
from check_liveness import ENTRY_POINTS, find_orphans, find_strays, project_files

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.unit


def tree(tmp_path, sources):
    """Write `sources` plus stub entry points; return (root, relative files)."""
    entries = {f"ritz0/{e}": "" for e in ENTRY_POINTS}
    for rel, text in {**entries, **sources}.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path, sorted({**entries, **sources})


def orphans(tmp_path, sources):
    return find_orphans(*tree(tmp_path, sources))


def test_module_nothing_imports_is_an_orphan(tmp_path):
    assert orphans(tmp_path, {"ritz0/dead.py": ""}) == ["ritz0/dead.py"]


def test_module_imported_from_an_entry_point_is_live(tmp_path):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": "import live\n",
        "ritz0/live.py": "",
    }) == []


def test_liveness_is_transitive(tmp_path):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": "import a\n",
        "ritz0/a.py": "from b import thing\n",
        "ritz0/b.py": "",
    }) == []


def test_orphans_importing_each_other_are_still_orphans(tmp_path):
    """Why this is reachability and not "has an importer": parser_gen.py and
    parser_adapter.py were reachable only from each other."""
    assert orphans(tmp_path, {
        "ritz0/gen.py": "import adapter\n",
        "ritz0/adapter.py": "import gen\n",
    }) == ["ritz0/adapter.py", "ritz0/gen.py"]


def test_a_test_importer_does_not_keep_a_module_alive(tmp_path):
    """emitter/struct_layout.py's only importer was its test."""
    assert orphans(tmp_path, {
        "ritz0/dead.py": "",
        "ritz0/test_dead.py": "import dead\n",
        "ritz0/emitter/test_dead2.py": "import dead\n",
    }) == ["ritz0/dead.py"]


def test_commented_out_import_does_not_count(tmp_path):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": "# import dead\n",
        "ritz0/dead.py": "",
    }) == ["ritz0/dead.py"]


def test_import_inside_a_function_counts(tmp_path):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": "def f():\n    import lazy\n",
        "ritz0/lazy.py": "",
    }) == []


@pytest.mark.parametrize("line", [
    "import emitter.fn_cache\n",
    "from emitter.fn_cache import x\n",
    "from emitter import fn_cache\n",
])
def test_submodule_import_forms(tmp_path, line):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": line,
        "ritz0/emitter/__init__.py": "",
        "ritz0/emitter/fn_cache.py": "",
    }) == []


def test_importing_one_submodule_leaves_its_sibling_dead(tmp_path):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": "from emitter.fn_cache import x\n",
        "ritz0/emitter/__init__.py": "",
        "ritz0/emitter/fn_cache.py": "",
        "ritz0/emitter/calls.py": "",
    }) == ["ritz0/emitter/calls.py"]


def test_relative_import_inside_a_package(tmp_path):
    assert orphans(tmp_path, {
        "ritz0/ritz0.py": "import emitter.a\n",
        "ritz0/emitter/__init__.py": "",
        "ritz0/emitter/a.py": "from .b import x\nfrom . import c\n",
        "ritz0/emitter/b.py": "",
        "ritz0/emitter/c.py": "",
    }) == []


@pytest.mark.parametrize("importer", ["build.py", "tools/x.py", "scripts/y.py"])
def test_production_importer_outside_ritz0_counts(tmp_path, importer):
    assert orphans(tmp_path, {
        importer: "import used_by_driver\n",
        "ritz0/used_by_driver.py": "",
    }) == []


def test_test_importer_outside_ritz0_does_not_count(tmp_path):
    assert orphans(tmp_path, {
        "tools/test_x.py": "import dead\n",
        "ritz0/dead.py": "",
    }) == ["ritz0/dead.py"]


def test_test_runner_is_production_despite_its_name(tmp_path):
    """build.py loads it, so what it imports is live."""
    assert orphans(tmp_path, {
        "ritz0/test_runner.py": "import helper\n",
        "ritz0/helper.py": "",
    }) == []


def test_entry_point_that_no_longer_exists_is_reported(tmp_path):
    root, files = tree(tmp_path, {})
    (root / "ritz0/list_deps.py").unlink()
    files.remove("ritz0/list_deps.py")
    assert find_orphans(root, files) == ["ritz0/list_deps.py (listed entry point is missing)"]


@pytest.mark.parametrize("rel", [
    "ritz0/parser_gen.py.orig",
    "grammars/ritz.grammar.old",
    "examples/x/src/main.ritz.old",
])
def test_backup_files_are_strays(tmp_path, rel):
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text("old")
    assert find_strays(tmp_path, [rel]) == [rel]


def test_elf_in_ritz0_is_a_stray(tmp_path):
    (tmp_path / "ritz0").mkdir()
    (tmp_path / "ritz0/cat_ll").write_bytes(b"\x7fELF\x02\x01\x01")
    (tmp_path / "ritz0/notes.md").write_text("text")
    assert find_strays(tmp_path, ["ritz0/cat_ll", "ritz0/notes.md"]) == ["ritz0/cat_ll"]


def test_real_tree_is_live():
    """The guard. Fails `make tools-unit` when ritz0/ grows an orphan."""
    assert find_orphans(ROOT, project_files(ROOT)) == []
    assert find_strays(ROOT, project_files(ROOT, untracked=False)) == []


def test_entry_points_each_have_a_reason():
    assert all(reason.strip() for reason in ENTRY_POINTS.values())


@pytest.mark.integration
def test_cli_goes_red_on_a_planted_untracked_orphan(tmp_path):
    """End to end: an orphan nobody has `git add`ed yet still fails."""
    root, _ = tree(tmp_path, {})
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    tool = [sys.executable, check_liveness.__file__, "--root", str(root)]

    clean = subprocess.run(tool, capture_output=True, text=True)
    assert clean.returncode == 0, clean.stdout + clean.stderr

    (root / "ritz0/planted.py").write_text("")
    planted = subprocess.run(tool, capture_output=True, text=True)
    assert planted.returncode == 1
    assert "ritz0/planted.py" in planted.stdout
