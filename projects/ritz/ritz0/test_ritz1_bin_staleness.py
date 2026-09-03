"""AGAST #1322 — prove the `ritz1_bin` fixture cannot be fooled by a stale binary.

`test_ritz1_parse_errors.py` used to build ritz1 only when the binary was
*absent*:

    if not RITZ1_BIN.exists():
        subprocess.run(["make", "-C", "ritz1", "ritz1"], ...)

Absent is not the same as stale.  With a stale binary the suite still ran, and
it still reported a number — just not one about the tree you have checked out.
The direction people notice is a false *failure*: someone investigates, rebuilds,
moves on.  The direction that matters is the other one.  Break `parse_module_end`
in `parser_gen.ritz` so ritz1 stops requiring EOF, run pytest without rebuilding,
and `test_trailing_garbage_is_not_silently_ignored` passes — against the *old*
binary, which still has the check.  The regression #1301 exists to prevent ships
green.  Nobody looks at a green run.

An always-rebuild fixture and a never-rebuild fixture both look green on a clean
tree, so the fixture change alone is unverified.  This module supplies the
missing half by running both fixture implementations against one identically
broken tree and asserting they disagree:

    old fixture (build-if-missing) -> pytest exits 0   <- the false PASS
    new fixture (delegate to make) -> pytest exits != 0 <- the regression caught

Everything happens inside a `tmp_path` copy of `projects/ritz`; the real tree is
only ever read (and brought up to date), never mutated.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

# The test whose verdict must depend on the freshness of the binary.
TARGET_TEST = "test_ritz1_parse_errors.py::test_trailing_garbage_is_not_silently_ignored"

# --- The mutation ------------------------------------------------------------
# `parse_module_end` is what enforces "the module ends at EOF".  Neutering it is
# precisely the #1301 regression: trailing garbage is swallowed and ritz1 exits 0.
MUTATION_FILE = Path("ritz1/src/parser_gen.ritz")
MUTATION_FROM = "        return module_require_eof(p)"
MUTATION_TO = "        return 0  # AGAST #1322 mutant: EOF requirement removed"

# --- The two fixture implementations, as literal source ----------------------
# `FIXTURE_NEW` must match `test_ritz1_parse_errors.py` exactly; if it stops
# matching, this test fails loudly rather than quietly testing nothing.
FIXTURE_NEW = "    _build_ritz1()\n    return RITZ1_BIN\n"
FIXTURE_OLD = "    if not RITZ1_BIN.exists():\n        _build_ritz1()\n    return RITZ1_BIN\n"

# Directories that are pure build noise or would make the copy enormous.
_COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__", ".git", ".pytest_cache", "*.pyc", ".mypy_cache", ".ruff_cache"
)


def _run_pytest(root: Path) -> subprocess.CompletedProcess:
    """Run the single parse-error test inside a copied tree, from its own ritz0."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", TARGET_TEST, "-q", "-p", "no:cacheprovider"],
        cwd=root / "ritz0",
        env=dict(os.environ, RITZ_PATH=str(root)),
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _swap_fixture(test_file: Path, old: str, new: str, label: str) -> None:
    """Replace the fixture body, asserting the replacement actually happened."""
    text = test_file.read_text()
    count = text.count(old)
    assert count == 1, (
        f"expected exactly one occurrence of the {label} fixture body in "
        f"{test_file.name}, found {count}.  The fixture has been refactored and "
        f"this staleness test is no longer exercising what it claims to — update "
        f"FIXTURE_OLD/FIXTURE_NEW rather than deleting the assertion."
    )
    test_file.write_text(text.replace(old, new))


@pytest.mark.integration
def test_stale_ritz1_binary_cannot_produce_a_false_pass(tmp_path):
    """A stale binary must not be able to turn a real regression into a green run.

    Arms the same broken tree with each fixture implementation in turn.  The old
    one passes (it never rebuilds, so it grades yesterday's compiler); the new
    one fails (make notices `parser_gen.ritz` moved and relinks).  If both arms
    agree, the fixture is not doing its job — in either direction.
    """
    # A fresh binary plus its object files, so the copy below starts consistent
    # and the mutated rebuild is incremental (~6s) rather than cold (~51s).
    build = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert build.returncode == 0 and RITZ1_BIN.exists(), (
        f"could not build ritz1 to seed the staleness test:\n"
        f"{build.stdout[-4000:]}\n{build.stderr[-4000:]}"
    )

    # copytree uses copy2, which preserves mtimes — essential, since the whole
    # experiment is about what make concludes from them.
    root = tmp_path / "ritz"
    shutil.copytree(RITZ_ROOT, root, ignore=_COPY_IGNORE, symlinks=True)
    assert (root / "ritz1" / "build" / "ritz1").exists(), "copy lost the binary"

    # Break the compiler at the source level.  The binary in the copy still has
    # the EOF check; only the sources disagree with it now.
    src = root / MUTATION_FILE
    text = src.read_text()
    assert text.count(MUTATION_FROM) == 1, (
        f"{MUTATION_FILE} no longer contains the expected EOF-enforcement line "
        f"{MUTATION_FROM!r}; pick a new mutation site rather than skipping."
    )
    src.write_text(text.replace(MUTATION_FROM, MUTATION_TO))

    target_file = root / "ritz0" / "test_ritz1_parse_errors.py"

    # --- Arm A: the old build-if-missing fixture -----------------------------
    # The binary exists, so it rebuilds nothing and grades the stale compiler,
    # which still rejects trailing garbage.  Green. This is the bug.
    _swap_fixture(target_file, FIXTURE_NEW, FIXTURE_OLD, "new")
    stale = _run_pytest(root)
    assert stale.returncode == 0, (
        "expected the build-if-missing fixture to report a (false) pass against "
        "the stale binary — if it now fails, this test is no longer demonstrating "
        "the false-PASS direction and needs rewriting.\n"
        f"stdout:\n{stale.stdout[-4000:]}\nstderr:\n{stale.stderr[-4000:]}"
    )

    # --- Arm B: the real fixture ---------------------------------------------
    # make sees parser_gen.ritz is newer than the binary, relinks, and the fresh
    # compiler happily accepts trailing garbage — so the test fails, as it must.
    _swap_fixture(target_file, FIXTURE_OLD, FIXTURE_NEW, "old")
    fresh = _run_pytest(root)
    assert fresh.returncode != 0, (
        "THE FIXTURE IS FAILING OPEN: ritz1's EOF check was removed at the source "
        "level and the parse-error suite still passed, which means it graded a "
        "stale binary.  A green run of test_ritz1_parse_errors.py currently proves "
        "nothing about the working tree (AGAST #1322).\n"
        f"stdout:\n{fresh.stdout[-4000:]}\nstderr:\n{fresh.stderr[-4000:]}"
    )
    assert "test_trailing_garbage_is_not_silently_ignored" in (fresh.stdout + fresh.stderr), (
        "the fresh-fixture run failed, but not in the test we mutated the "
        f"compiler to break:\nstdout:\n{fresh.stdout[-4000:]}\nstderr:\n{fresh.stderr[-4000:]}"
    )
