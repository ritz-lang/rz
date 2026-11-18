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
from check_liveness import (
    ENTRY_POINTS,
    RITZLIB_ALLOWLIST,
    find_orphans,
    find_ritzlib_orphans,
    find_strays,
    project_files,
    repo_root,
    ritzlib_dir,
)

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.unit


def tree(tmp_path, sources):
    """Write `sources` plus stub entry points and allowlisted ritzlib modules;
    return (root, relative files)."""
    entries = {f"ritz0/{e}": "" for e in ENTRY_POINTS}
    entries.update({f"ritzlib/{m}": "" for m in RITZLIB_ALLOWLIST})
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


@pytest.mark.parametrize("rel", ["ritz0/cat_ll", "ritz1/ritz1_new", "tools/a.out"])
def test_elf_anywhere_is_a_stray(tmp_path, rel):
    """AGAST #3447: ritz1/ritz1_new sat tracked for months; ritz0/ was the only
    directory checked."""
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x7fELF\x02\x01\x01")
    (tmp_path / "notes.md").write_text("text")
    assert find_strays(tmp_path, [rel, "notes.md"]) == [rel]


def test_real_tree_is_live():
    """The guard. Fails `make tools-unit` when ritz0/ or ritzlib/ grows an
    orphan."""
    assert find_orphans(ROOT, project_files(ROOT)) == []
    assert find_strays(ROOT, project_files(ROOT, untracked=False)) == []
    repo = repo_root(ROOT)
    assert find_ritzlib_orphans(repo, project_files(repo), ritzlib_dir(ROOT, repo)) == []


# --- ritzlib (AGAST #3913) ---------------------------------------------------
#
# The same rule one level up: a ritzlib module must be reachable from a
# non-test .ritz file anywhere in the repo.  #1859 found crt0, entry, meta,
# async.ritz and lang/* alive only in docs or tests.

LIB = "projects/ritz/ritzlib"


def lib_orphans(tmp_path, sources, allow=None):
    for rel, text in sources.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return find_ritzlib_orphans(tmp_path, sorted(sources), LIB, {} if allow is None else allow)


def test_ritzlib_module_nothing_imports_is_an_orphan(tmp_path):
    assert lib_orphans(tmp_path, {f"{LIB}/crt0.ritz": ""}) == [f"{LIB}/crt0.ritz"]


@pytest.mark.parametrize("importer", [
    "projects/valet/src/main.ritz",
    "projects/ritz/ritz1/src/main.ritz",
    "projects/ritz/examples/tier1_basics/03_echo/src/main.ritz",
])
def test_ritzlib_module_with_a_production_importer_is_live(tmp_path, importer):
    assert lib_orphans(tmp_path, {
        importer: "import ritzlib.sys\n",
        f"{LIB}/sys.ritz": "",
    }) == []


@pytest.mark.parametrize("line", [
    "import ritzlib.span\n",
    "pub import ritzlib.span\n",
    "import ritzlib.span { Span, span_from_ptr }\n",
    "import ritzlib.span as sp\n",
    "    import ritzlib.span\n",
])
def test_ritzlib_import_forms(tmp_path, line):
    assert lib_orphans(tmp_path, {
        "projects/http/lib/a.ritz": line,
        f"{LIB}/span.ritz": "",
    }) == []


def test_ritzlib_nested_module_path(tmp_path):
    """`ritzlib.async.tasks` is async/tasks.ritz; its sibling stays dead."""
    assert lib_orphans(tmp_path, {
        "projects/valet/src/main.ritz": "import ritzlib.async.tasks\n",
        f"{LIB}/async/tasks.ritz": "",
        f"{LIB}/async/blocking_fs.ritz": "",
    }) == [f"{LIB}/async/blocking_fs.ritz"]


def test_ritzlib_liveness_is_transitive(tmp_path):
    assert lib_orphans(tmp_path, {
        "projects/valet/src/main.ritz": "import ritzlib.io\n",
        f"{LIB}/io.ritz": "import ritzlib.sys\n",
        f"{LIB}/sys.ritz": "",
    }) == []


def test_ritzlib_orphans_importing_each_other_are_still_orphans(tmp_path):
    assert lib_orphans(tmp_path, {
        f"{LIB}/entry.ritz": "import ritzlib.span\n",
        f"{LIB}/span.ritz": "import ritzlib.entry\n",
    }) == [f"{LIB}/entry.ritz", f"{LIB}/span.ritz"]


@pytest.mark.parametrize("importer", [
    f"{LIB}/tests/test_heap.ritz",
    "projects/ritz/ritz0/test/heap_fixture.ritz",
    "projects/valet/test/test_x.ritz",
    "projects/ritz/examples/tier5_async/82_box/test/test_main.ritz",
    "projects/goliath/tests/integration.ritz",
])
def test_ritzlib_test_importer_does_not_keep_a_module_alive(tmp_path, importer):
    """lang/lexer's one importer was a test (#1859)."""
    assert lib_orphans(tmp_path, {
        importer: "import ritzlib.heap\n",
        f"{LIB}/heap.ritz": "",
    }) == [f"{LIB}/heap.ritz"]


@pytest.mark.parametrize("importer", [
    "projects/larb/review/snapshot/main.ritz",
    "projects/ritz/docs/archive/old/main.ritz",
    "archive/spectree/lib/types.ritz",
])
def test_ritzlib_archived_importer_does_not_count(tmp_path, importer):
    assert lib_orphans(tmp_path, {
        importer: "import ritzlib.heap\n",
        f"{LIB}/heap.ritz": "",
    }) == [f"{LIB}/heap.ritz"]


def test_ritzlib_commented_out_import_does_not_count(tmp_path):
    assert lib_orphans(tmp_path, {
        "projects/harland/user/lib.ritz": "#   import ritzlib.heap { a }\n",
        f"{LIB}/heap.ritz": "",
    }) == [f"{LIB}/heap.ritz"]


def test_ritzlib_import_named_only_in_a_doc_does_not_count(tmp_path):
    """STDLIB_REFERENCE.md showed `import ritzlib.heap` while nothing used it."""
    assert lib_orphans(tmp_path, {
        "projects/ritz/docs/STDLIB_REFERENCE.md": "```ritz\nimport ritzlib.heap\n```\n",
        f"{LIB}/heap.ritz": "",
    }) == [f"{LIB}/heap.ritz"]


def test_ritzlib_allowlisted_orphan_passes_and_keeps_its_imports_alive(tmp_path):
    assert lib_orphans(tmp_path, {
        f"{LIB}/testlib.ritz": "import ritzlib.str\n",
        f"{LIB}/str.ritz": "",
    }, allow={"testlib.ritz": "test helpers"}) == []


def test_ritzlib_allowlisted_module_that_is_missing_is_reported(tmp_path):
    assert lib_orphans(tmp_path, {}, allow={"gone.ritz": "why"}) == [
        f"{LIB}/gone.ritz (allowlisted module is missing)"]


def test_ritzlib_allowlisted_module_that_became_live_is_reported(tmp_path):
    """A stale entry would silently cover the module if it died again."""
    assert lib_orphans(tmp_path, {
        "projects/valet/src/main.ritz": "import ritzlib.ptr\n",
        f"{LIB}/ptr.ritz": "",
    }, allow={"ptr.ritz": "why"}) == [
        f"{LIB}/ptr.ritz (allowlisted but has a production importer; drop the entry)"]


def test_ritzlib_tests_package_is_not_a_module(tmp_path):
    """ritzlib/tests/ is its own package of test files, not library modules."""
    assert lib_orphans(tmp_path, {f"{LIB}/tests/helper.ritz": ""}) == []


def test_ritzlib_allowlist_entries_each_have_a_reason():
    assert RITZLIB_ALLOWLIST
    assert all(reason.strip() for reason in RITZLIB_ALLOWLIST.values())


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


@pytest.mark.integration
def test_cli_goes_red_on_a_planted_tracked_elf(tmp_path):
    """End to end (AGAST #3447): a tracked ELF outside ritz0/ fails; the same
    file untracked does not, since a local build output is not the tree's."""
    root, _ = tree(tmp_path, {})
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    tool = [sys.executable, check_liveness.__file__, "--root", str(root)]

    (root / "ritz1").mkdir()
    (root / "ritz1/ritz1_new").write_bytes(b"\x7fELF\x02\x01\x01")
    untracked = subprocess.run(tool, capture_output=True, text=True)
    assert untracked.returncode == 0, untracked.stdout + untracked.stderr

    subprocess.run(["git", "add", "ritz1/ritz1_new"], cwd=root, check=True)
    tracked = subprocess.run(tool, capture_output=True, text=True)
    assert tracked.returncode == 1
    assert "ritz1/ritz1_new" in tracked.stdout


@pytest.mark.integration
def test_cli_goes_red_on_a_planted_ritzlib_orphan(tmp_path):
    """End to end (AGAST #3913): a ritzlib module only a test imports fails;
    a production importer anywhere in the repo clears it."""
    root, _ = tree(tmp_path, {})
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    tool = [sys.executable, check_liveness.__file__, "--root", str(root)]

    (root / "ritzlib/crt0.ritz").write_text("")
    (root / "ritzlib/tests").mkdir()
    (root / "ritzlib/tests/test_crt0.ritz").write_text("import ritzlib.crt0\n")
    planted = subprocess.run(tool, capture_output=True, text=True, check=False)
    assert planted.returncode == 1
    assert "ritzlib/crt0.ritz: no production importer" in planted.stdout

    (root / "examples/x/src").mkdir(parents=True)
    (root / "examples/x/src/main.ritz").write_text("import ritzlib.crt0\n")
    cleared = subprocess.run(tool, capture_output=True, text=True, check=False)
    assert cleared.returncode == 0, cleared.stdout + cleared.stderr
