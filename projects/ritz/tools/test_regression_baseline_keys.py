"""regression_baseline_keys.tree_hash: what the Stage 1 baseline key reads (AGAST #4347).

`global_key` hashes `tree_hash(root / "ritzlib")` as "what every example links
against".  Examples link the ritzlib *modules*, not the `ritzlib/tests` package
(its own ritz.toml, run by the ritz1 test step) nor the README (docs).  Reading
either trips main's read-set-audit: the "Differential corpus regression" step's
read set excludes `projects/ritz/ritzlib/tests/*` and
`projects/ritz/ritzlib/*.md`, so the strace of the step must not open them
(AGAST #4315, #4347).
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _mod():
    spec = importlib.util.spec_from_file_location(
        "regression_baseline_keys", SCRIPTS / "regression_baseline_keys.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ritzlib(tmp_path: Path) -> Path:
    """A ritzlib-shaped tree: a module, a README, and a nested tests package."""
    r = tmp_path / "ritzlib"
    r.mkdir()
    (r / "argspec.ritz").write_text("// argspec\n")
    (r / "README.md").write_text("# readme\n")
    (r / "tests").mkdir()
    (r / "tests" / "ritz.toml").write_text("[package]\n")
    (r / "tests" / "test_argspec.ritz").write_text("// test\n")
    return r


def test_the_ritzlib_tree_hash_reads_only_modules(tmp_path):
    tree_hash = _mod().tree_hash
    r = _ritzlib(tmp_path)
    baseline = tree_hash(r, skip_subpackages=True, skip_suffixes=(".md",))

    # A module change is an input of the baseline key...
    (r / "argspec.ritz").write_text("// argspec changed\n")
    assert tree_hash(r, skip_subpackages=True, skip_suffixes=(".md",)) != baseline

    # ...but the nested tests package and the README are not.
    (r / "argspec.ritz").write_text("// argspec\n")
    assert tree_hash(r, skip_subpackages=True, skip_suffixes=(".md",)) == baseline
    (r / "tests" / "test_argspec.ritz").write_text("// test changed\n")
    assert tree_hash(r, skip_subpackages=True, skip_suffixes=(".md",)) == baseline
    (r / "README.md").write_text("# readme changed\n")
    assert tree_hash(r, skip_subpackages=True, skip_suffixes=(".md",)) == baseline


def test_the_default_tree_hash_reads_the_whole_tree(tmp_path):
    """An example's (or dependency's) key still hashes every file."""
    tree_hash = _mod().tree_hash
    r = _ritzlib(tmp_path)
    whole = tree_hash(r)
    (r / "tests" / "test_argspec.ritz").write_text("// test changed\n")
    assert tree_hash(r) != whole
    (r / "README.md").write_text("# readme changed\n")
    assert tree_hash(r) != whole


@pytest.mark.integration
def test_the_global_key_ignores_ritzlib_tests_and_readme(tmp_path):
    """`global_key` is the caller: editing a ritzlib test or the README must
    not invalidate the Stage 1 baseline (they are not what examples link)."""
    global_key = _mod().global_key
    root = tmp_path / "root"
    root.mkdir()
    _ritzlib(root)
    (root / "runtime").mkdir()
    (root / "runtime" / "ritz_start.x86_64.ll").write_text("; runtime\n")
    harness = root / "scripts" / "regression.sh"
    harness.parent.mkdir()
    harness.write_text("#!/usr/bin/env bash\n")

    baseline = global_key(root, "build-dir", harness, "extra")

    (root / "ritzlib" / "tests" / "test_argspec.ritz").write_text("// test changed\n")
    (root / "ritzlib" / "README.md").write_text("# readme changed\n")
    assert global_key(root, "build-dir", harness, "extra") == baseline

    (root / "ritzlib" / "argspec.ritz").write_text("// argspec changed\n")
    assert global_key(root, "build-dir", harness, "extra") != baseline
