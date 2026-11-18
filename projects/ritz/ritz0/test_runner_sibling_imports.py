"""`ritz0 --test` resolves a test file's sibling imports from the test file's
own directory, as `rz build` and ritz1 do.

AGAST #1558. ritz0 compiles a scratch copy of the test file in a tmpdir, so a
bare `import foo` of a module next to the test file only resolved because
`setup_test_environment` copied two hardcoded names into that tmpdir:
`test_import_*.ritz` and `helpers.ritz`. Any other sibling (`import fixtures`)
failed with "Cannot find module". The copies are gone; the test file's
directory is now the harness's first source root, for both import discovery
and the harness compile.
"""

import os
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
    """A package whose test imports `fixtures_math`, a sibling support module
    under a name no allowlist has ever known."""
    monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
    (tmp_path / "ritz.toml").write_text(
        '[package]\nname = "siblings"\nversion = "0.1.0"\n'
    )
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "fixtures_math.ritz").write_text("pub fn seven() -> i32\n    7\n")
    test_file = test_dir / "test_siblings.ritz"
    test_file.write_text(
        textwrap.dedent(
            """\
            import ritzlib.sys
            import fixtures_math

            [[test]]
            fn test_sibling_import() -> i32
                assert seven() == 7
                0
            """
        )
    )
    return test_file


@pytest.mark.unit
def test_setup_copies_no_sources_into_tmpdir(package, tmp_path):
    """No module is copied by name: discovery finds the sibling in place."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    _, deps, error, _ = test_runner.setup_test_environment(str(package), str(scratch))
    assert error is None
    assert str((package.parent / "fixtures_math.ritz").resolve()) in deps
    copied = [p.name for p in scratch.iterdir()
              if p.suffix == ".ritz" and p.name != "dummy_harness.ritz"]
    assert copied == []


@pytest.mark.integration
def test_sibling_import_resolves_under_ritz0_test(package):
    passed, failed, failures = test_runner.run_test_file(str(package))
    assert (passed, failed) == (1, 0), failures

