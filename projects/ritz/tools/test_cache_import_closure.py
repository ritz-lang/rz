"""The per-module build cache must see every import form (AGAST #1832).

`cache.py` used to find a module's imports with a regex that matched only a
bare `import a.b` line. `import b { S }`, `pub import b`, `pub import b { S }`
and `import b as bb` (30% of the imports in the tree) were invisible to
`needs_rebuild`. So after a struct change in `b`, the dependent's cached
.ll/.o was reused and the binary linked two different layouts of `S`.

The fix derives the import graph from ritz0's own import resolver, the same
code `list_deps.py` and the compiler use. These tests pin that:

* unit: for every import form, changing `b` invalidates the dependent.
* end to end: build, change a field's type in `b`, rebuild, run. The binary
  must see the new layout.
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
# build.py does `from cache import BuildCache`, so its directory must be
# importable for the end-to-end test.
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

_spec = importlib.util.spec_from_file_location("ritz_cache_1832", PKG_DIR / "cache.py")
_cache_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cache_mod)
BuildCache = _cache_mod.BuildCache

B_V1 = "pub struct S\n    x: i32\n"
B_V2 = "pub struct S\n    x: i64\n"
MAIN_BODY = "\nfn main() -> i32\n    return sizeof(S) as i32\n"

# Each case: {relative file: source}. `main.ritz` is the dependent; `b.ritz`
# holds S and gets edited.
IMPORT_FORMS = {
    "bare": {"main.ritz": "import b" + MAIN_BODY},
    "brace": {"main.ritz": "import b { S }" + MAIN_BODY},
    "pub_import": {"main.ritz": "pub import b" + MAIN_BODY},
    "pub_import_brace": {"main.ritz": "pub import b { S }" + MAIN_BODY},
    "alias": {"main.ritz": "import b as bb" + MAIN_BODY},
    "multiline_brace": {"main.ritz": "import b {\n    S,\n}" + MAIN_BODY},
    # Re-export through an intermediate module: main never names b at all.
    "reexport_via_mod": {
        "mod.ritz": "pub import b { S }\n",
        "main.ritz": "import mod { S }" + MAIN_BODY,
    },
    # A dotted path into a subdirectory, brace form.
    "dotted_brace": {
        "main.ritz": "import lib.b { S }" + MAIN_BODY,
        "@b": "lib/b.ritz",
    },
}


def _write_tree(root: Path, form: str) -> tuple[Path, Path]:
    files = dict(IMPORT_FORMS[form])
    b_rel = files.pop("@b", "b.ritz")
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    b = root / b_rel
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_text(B_V1)
    return root / "main.ritz", b


@pytest.mark.unit
@pytest.mark.parametrize("form", sorted(IMPORT_FORMS))
def test_dependency_change_invalidates_dependent(tmp_path, form):
    src = tmp_path / "src"
    src.mkdir()
    main, b = _write_tree(src, form)

    cache = BuildCache(project_root=tmp_path)
    cache.update_cache(main, "; main v1\n")
    stale, reason = cache.needs_rebuild(main)
    assert not stale, f"fresh cache should be valid, got: {reason}"

    b.write_text(B_V2)
    stale, reason = cache.needs_rebuild(main)
    assert stale, f"`{form}` import of b: struct change in b left main's cache valid"
    assert str(b.resolve()) in reason


@pytest.mark.unit
@pytest.mark.parametrize("form", sorted(IMPORT_FORMS))
def test_transitive_dependencies_include_b(tmp_path, form):
    src = tmp_path / "src"
    src.mkdir()
    main, b = _write_tree(src, form)
    deps = BuildCache(project_root=tmp_path).get_transitive_dependencies(main)
    assert str(b.resolve()) in deps


@pytest.mark.unit
def test_import_via_source_root_is_tracked(tmp_path):
    """Imports resolved through a package's `sources` roots count too.

    build.py resolves `import b` against the package's source roots
    (list_deps --sources). The cache must use the same resolution, or a
    module found that way is invisible to it.
    """
    pkg = tmp_path / "pkg"
    (pkg / "src" / "app").mkdir(parents=True)
    (pkg / "lib").mkdir()
    main = pkg / "src" / "app" / "main.ritz"
    main.write_text("import b { S }" + MAIN_BODY)
    b = pkg / "lib" / "b.ritz"
    b.write_text(B_V1)

    cache = BuildCache(project_root=tmp_path)
    cache.set_import_context(project_root=pkg, source_roots=["lib"])
    cache.update_cache(main, "; main v1\n")
    assert not cache.needs_rebuild(main)[0]

    b.write_text(B_V2)
    stale, reason = cache.needs_rebuild(main)
    assert stale and str(b.resolve()) in reason


class _CountingResolver:
    """Wraps the real resolver and records which files it had to parse."""

    def __init__(self, real):
        self.real = real
        self.parsed = []

    def direct_imports(self, path):
        self.parsed.append(Path(path).name)
        return self.real.direct_imports(path)


def _counting(cache):
    counter = _CountingResolver(cache._get_resolver())
    cache._resolver = counter
    return counter


@pytest.mark.unit
def test_warm_process_parses_only_changed_files(tmp_path):
    """Parsing with the real lexer/parser is slow (~7s for ritz1's closure),
    so the scan results persist in the cache directory, keyed by content
    hash. A new build process (new BuildCache) re-parses only edited files.
    """
    src = tmp_path / "src"
    src.mkdir()
    main, b = _write_tree(src, "reexport_via_mod")

    first = BuildCache(project_root=tmp_path)
    first.update_cache(main, "; main v1\n")

    second = BuildCache(project_root=tmp_path)
    counter = _counting(second)
    assert not second.needs_rebuild(main)[0]
    assert counter.parsed == [], "unchanged files were re-parsed"

    b.write_text(B_V2)
    third = BuildCache(project_root=tmp_path)
    counter = _counting(third)
    stale, reason = third.needs_rebuild(main)
    assert stale and str(b.resolve()) in reason
    assert counter.parsed == ["b.ritz"]


@pytest.mark.unit
def test_persisted_imports_are_per_resolution_context(tmp_path):
    """The same file can resolve `import b` differently under different
    source roots, so a scan stored under one context is not reused in another."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "lib").mkdir()
    main = pkg / "src" / "main.ritz"
    main.write_text("import b { S }" + MAIN_BODY)
    (pkg / "lib" / "b.ritz").write_text(B_V1)

    plain = BuildCache(project_root=tmp_path)
    assert str((pkg / "lib" / "b.ritz").resolve()) not in plain.get_transitive_dependencies(main)
    plain.save()

    rooted = BuildCache(project_root=tmp_path)
    rooted.set_import_context(project_root=pkg, source_roots=["lib"])
    assert str((pkg / "lib" / "b.ritz").resolve()) in rooted.get_transitive_dependencies(main)


@pytest.mark.unit
def test_persisted_imports_rescanned_when_target_vanishes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    main = src / "main.ritz"
    main.write_text("import lib.b { S }" + MAIN_BODY)
    (src / "lib").mkdir()
    (src / "lib" / "b.ritz").write_text(B_V1)
    first = BuildCache(project_root=tmp_path)
    first.update_cache(main, "; v1\n")

    # Move b to a flat name: same import, different file, main unchanged.
    (src / "lib" / "b.ritz").rename(src / "lib.b.ritz")
    second = BuildCache(project_root=tmp_path)
    deps = second.get_transitive_dependencies(main)
    assert str((src / "lib.b.ritz").resolve()) in deps
    assert second.needs_rebuild(main)[0]


@pytest.mark.unit
def test_cache_module_has_no_regex_import_scanner():
    """The ticket's acceptance grep: one resolver, not a second regex one."""
    text = (PKG_DIR / "cache.py").read_text()
    assert "IMPORT_PATTERN" not in text
    assert "def scan_imports" not in text
    assert "def resolve_import_path" not in text


# --- end to end ------------------------------------------------------------


@pytest.fixture
def buildpy(request):
    spec = importlib.util.spec_from_file_location("ritz_buildpy_1832", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _assert_rebuild_sees_new_layout(buildpy, tmp_path, pkg, main, b, source_roots, what):
    out = tmp_path / "out"
    out.mkdir()

    # A private cache directory so the test never touches the shared one.
    cache = BuildCache(project_root=PKG_DIR)
    cache._cache_dir = tmp_path / ".ritz-cache"
    buildpy._build_cache["ritz0"] = cache

    def build_and_run() -> int:
        bin_path = buildpy.compile_binary(
            "layout", main, out, use_cache=True, pkg_dir=pkg, source_roots=source_roots)
        assert bin_path is not None, "build failed"
        return subprocess.run([str(bin_path)], timeout=30).returncode

    assert build_and_run() == 4
    b.write_text(B_V2)
    assert build_and_run() == 8, (
        f"{what}: main's cached object was reused after S changed in b")


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")
@pytest.mark.parametrize("form", ["bare", "brace", "pub_import", "reexport_via_mod"])
def test_rebuild_after_struct_change_sees_new_layout(buildpy, tmp_path, form):
    """`bare` guards the second half of the bug: b is compiled before main in
    the same build, so a shared per-file hash made b look unchanged by the
    time main was checked, whatever the import form."""
    pkg = tmp_path / "pkg"
    src = pkg / "src"
    src.mkdir(parents=True)
    main, b = _write_tree(src, form)
    _assert_rebuild_sees_new_layout(buildpy, tmp_path, pkg, main, b, ["src"], f"`{form}`")


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")
def test_rebuild_tracks_module_found_via_package_source_root(buildpy, tmp_path):
    """b is reachable only through the package's `lib` source root, so the
    cache must get build.py's resolution context (set_import_context)."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "lib").mkdir()
    main = pkg / "src" / "main.ritz"
    main.write_text("import b { S }" + MAIN_BODY)
    b = pkg / "lib" / "b.ritz"
    b.write_text(B_V1)
    _assert_rebuild_sees_new_layout(
        buildpy, tmp_path, pkg, main, b, ["src", "lib"], "source-root import")
