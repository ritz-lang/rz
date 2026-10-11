"""`ritz0 --test` must resolve imports through the package's `sources` roots.

AGAST #1686. `setup_test_environment` read `sources` from ritz.toml and used
them to *discover* a test file's dependencies, but the two ritz0 invocations
that then *compile* them -- one per dependency (`compile_dependencies`) and one
for the harness (`_compile_harness`) -- were never given `--sources`. Discovery
succeeded, compilation then failed with "Cannot find module: types.color", and
every test in the file was reported as failed. That alone kept prism's
test_color.ritz (15 tests) red on every main push, with every test passing once
the import resolved. `rz build` passes the same roots via `--sources`, so a
package could build cleanly and still have an untestable test suite.
"""

import sys
import textwrap
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402


@pytest.fixture
def package(tmp_path, monkeypatch):
    """A package with sources = ["src"] whose test imports `geom.pt`.

    `geom.pt` in turn imports `geom.base` through the source root, so both the
    harness compile and the per-dependency compile must see `src/`.
    """
    monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
    (tmp_path / "ritz.toml").write_text(
        textwrap.dedent(
            """\
            [package]
            name = "srcroots"
            version = "0.1.0"
            sources = ["src"]
            """
        )
    )
    geom = tmp_path / "src" / "geom"
    geom.mkdir(parents=True)
    (geom / "base.ritz").write_text("pub fn base_val() -> i32\n    3\n")
    (geom / "pt.ritz").write_text(
        "import geom.base\n\npub fn pt_val() -> i32\n    base_val() + 4\n"
    )
    (tmp_path / "test").mkdir()
    test_file = tmp_path / "test" / "test_srcroots.ritz"
    test_file.write_text(
        textwrap.dedent(
            """\
            import ritzlib.sys
            import geom.pt

            [[test]]
            fn test_import_through_source_root() -> i32
                assert pt_val() == 7
                0
            """
        )
    )
    return test_file


@pytest.mark.unit
def test_project_source_roots_reads_ritz_toml(package):
    root = package.parent.parent
    roots = test_runner.project_source_roots(root)
    assert roots == [str(root / "src")]


@pytest.mark.unit
def test_project_source_roots_without_toml(tmp_path):
    assert test_runner.project_source_roots(None) == []
    assert test_runner.project_source_roots(tmp_path) == []


@pytest.mark.integration
def test_test_file_imports_resolve_through_source_roots(package):
    passed, failed, failures = test_runner.run_test_file(str(package))
    assert (passed, failed) == (1, 0), failures
