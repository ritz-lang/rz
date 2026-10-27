"""AGAST #1322 — prove the `ritz1_bin` fixture cannot be fooled by a stale binary.

`test_ritz1_parse_errors.py` used to build ritz1 only when the binary was
*absent*:

    if not RITZ1_BIN.exists():
        run make on ritz1


Absent is not the same as stale.  With a stale binary the suite still ran, and
it still reported a number — just not one about the tree you have checked out.
The direction people notice is a false *failure*: someone investigates, rebuilds,
moves on.  The direction that matters is the other one.  Make `parse_tokens` in
`main.ritz` ignore the parser's EOF error, run pytest without rebuilding,
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
only ever read, never mutated.

Since AGAST #1804 the fixture lives in conftest.py — one session-scoped build
shared by every module — so that is the file whose staleness rule is swapped.
The copy runs while other xdist workers are busy, so it leaves out the only
in-tree paths a concurrent test writes (conftest.py, item 5): build.py's
`.ritz-cache*` and `build.py run`'s top-level `build/`.  Everything else it
copies is only read during a session, so this module needs no xdist group.
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
# The parser rejects trailing garbage by setting `p.error` (module_require_eof),
# and main.ritz's `parse_tokens` turns that into a non-zero exit.  The mutant
# ignores the error and keeps the partial module, which is the #1301 regression:
# trailing garbage is swallowed and ritz1 exits 0.
#
# The site is in main.ritz because nothing imports main (AGAST #1895).  The
# rebuild is then main.ll + main.o + a relink (~2 s).  The previous site,
# parser_gen.ritz, recompiled 10 dependent modules (110-340 s).
# `test_mutation_site_is_a_leaf_module` keeps it that way.
MUTATION_FILE = Path("ritz1/src/main.ritz")
MUTATION_FROM = (
    "    let m: *Module = parse_module(@p)\n"
    "\n"
    "    if p.error != 0\n"
)
MUTATION_TO = (
    "    parse_module(@p)\n"
    "    let m: *Module = p.module  # AGAST #1322 mutant: keep the partial module\n"
    "\n"
    "    if p.error != p.error\n"
)

# --- The two fixture implementations, as literal source ----------------------
# `FIXTURE_NEW` must match conftest.py's `_ritz1_stale` exactly; if it stops
# matching, this test fails loudly rather than quietly testing nothing.
FIXTURE_FILE = "conftest.py"
FIXTURE_NEW = "    return True  # make decides freshness from mtimes (#1322)\n"
FIXTURE_OLD = "    return not RITZ1_BIN.exists()\n"

# Directories that are pure build noise or would make the copy enormous.
_NOISE = shutil.ignore_patterns(
    "__pycache__", ".git", ".pytest_cache", "*.pyc", ".mypy_cache", ".ruff_cache",
)


def _COPY_IGNORE(directory: str, names: list[str]) -> set[str]:
    """Noise, plus what concurrent tests write in the real tree (see docstring).

    `build` is dropped only at the top level: ritz1/build must be copied.
    """
    ignored = set(_NOISE(directory, names))
    ignored.update(n for n in names if n.startswith(".ritz-cache"))
    if Path(directory) == RITZ_ROOT and "build" in names:
        ignored.add("build")
    return ignored


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


def _dependents(mutation_file: Path) -> list[str]:
    """ritz1 modules whose make dependency file (`build/<m>.d`) lists `mutation_file`.

    Each of them gets recompiled, often with clang -O2 too, when the mutation lands.
    """
    rel = f"src/{mutation_file.name}"
    return sorted(
        d.stem
        for d in (RITZ_ROOT / "ritz1" / "build").glob("*.d")
        if rel in d.read_text()
    )


@pytest.mark.integration
def test_mutation_site_is_a_leaf_module(ritz1_bin):
    """AGAST #1895: the mutated module must have no dependents.

    The old site, parser_gen.ritz, was imported by 10 modules, including emitter
    at -O2.  The mutated "incremental" rebuild then took 110-340 s, and this
    module became the critical path of the whole xdist session.  If the site
    gets dependents, the slow test is slow again.
    """
    assert ritz1_bin.exists()
    deps = _dependents(MUTATION_FILE)
    assert deps == [], (
        f"{MUTATION_FILE} is imported by {deps}; mutating it rebuilds each of "
        f"them.  Pick a mutation site in a module nothing imports (main.ritz)."
    )


@pytest.mark.slow  # scheduled first under xdist (conftest.py, item 6)
@pytest.mark.integration
def test_stale_ritz1_binary_cannot_produce_a_false_pass(tmp_path, ritz1_bin):
    """A stale binary must not be able to turn a real regression into a green run.

    Arms the same broken tree with each fixture implementation in turn.  The old
    one passes (it never rebuilds, so it grades yesterday's compiler); the new
    one fails (make notices `main.ritz` moved and relinks).  If both arms
    agree, the fixture is not doing its job — in either direction.
    """
    # `ritz1_bin` is a fresh binary plus its object files, so the copy below
    # starts consistent.  The mutated rebuild then recompiles only main.ritz
    # (a leaf) and relinks, instead of a cold build (~51s).
    assert ritz1_bin == RITZ1_BIN and RITZ1_BIN.exists()

    # copytree uses copy2, which preserves mtimes — essential, since the whole
    # experiment is about what make concludes from them.
    root = tmp_path / "ritz"
    shutil.copytree(RITZ_ROOT, root, ignore=_COPY_IGNORE, symlinks=True)
    assert (root / "ritz1" / "build" / "ritz1").exists(), "copy lost the binary"

    # Break the compiler at the source level.  The binary in the copy still
    # rejects trailing garbage; only the sources disagree with it now.
    src = root / MUTATION_FILE
    text = src.read_text()
    assert text.count(MUTATION_FROM) == 1, (
        f"{MUTATION_FILE} no longer contains the expected parse-error check "
        f"{MUTATION_FROM!r}; pick a new mutation site rather than skipping."
    )
    src.write_text(text.replace(MUTATION_FROM, MUTATION_TO))

    target_file = root / "ritz0" / FIXTURE_FILE

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
    # make sees main.ritz is newer than the binary, relinks, and the fresh
    # compiler happily accepts trailing garbage — so the test fails, as it must.
    _swap_fixture(target_file, FIXTURE_OLD, FIXTURE_NEW, "old")
    fresh = _run_pytest(root)
    assert fresh.returncode != 0, (
        "THE FIXTURE IS FAILING OPEN: ritz1's parse-error exit was removed at the source "
        "level and the parse-error suite still passed, which means it graded a "
        "stale binary.  A green run of test_ritz1_parse_errors.py currently proves "
        "nothing about the working tree (AGAST #1322).\n"
        f"stdout:\n{fresh.stdout[-4000:]}\nstderr:\n{fresh.stderr[-4000:]}"
    )
    assert "test_trailing_garbage_is_not_silently_ignored" in (fresh.stdout + fresh.stderr), (
        "the fresh-fixture run failed, but not in the test we mutated the "
        f"compiler to break:\nstdout:\n{fresh.stdout[-4000:]}\nstderr:\n{fresh.stderr[-4000:]}"
    )
