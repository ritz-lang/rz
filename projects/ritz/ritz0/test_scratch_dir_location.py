"""Scratch directories must not be created inside the tree under test.

AGAST #1392. `test_runner.py` built its per-file scratch directory with
`tempfile.mkdtemp(dir='.')`, i.e. inside the package being tested, and filled it
with a symlink named `ritzlib` pointing at the real `ritzlib` so imports would
resolve. Cleanup lived in a `finally`, which covers exceptions but not SIGTERM
-- CPython services SIGTERM by terminating without unwinding -- so a killed run
left the directory, and its symlink, behind.

When the package under test *is* ritzlib, that surviving symlink points at its
own ancestor:

    ritzlib/tests/tmphpa0oggb/ritzlib -> .../projects/ritz/ritzlib

which is a cycle. Two such directories existed, so a recursive walk had two ways
down at every level and the cost was exponential in depth. pytest follows
directory symlinks during collection: the ritz0 suite spent 739 s and collected
zero tests before it was interrupted, against a 73 s baseline for the same
suite once the cycle was removed.

The invariant these tests pin is deliberately narrow and structural: scratch
lives under the system temp directory, so it *cannot* be an ancestor of anything
it links to, and a cycle is unconstructible rather than merely unlikely. That is
what `run_batch_tests` at test_runner.py:754 already did -- one code path in
this very file was always correct, which is the strongest available evidence
that relocating the other two is safe.

The SIGTERM test is the one that would have caught the outage. It is
deliberately end-to-end (a real subprocess, a real signal) rather than a
monkeypatched assertion about which arguments `mkdtemp` received, because the
defect was never in the arguments -- it was in what survived the kill.
"""

import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402


@pytest.mark.unit
def test_scratch_dir_is_under_the_system_temp_dir():
    """The helper places scratch outside the tree under test.

    Asserting `is_relative_to(gettempdir())` rather than merely "not inside the
    repo" states the positive invariant: we know where scratch goes, so the OS
    reclaims a leak and no walk of the source tree can ever reach it.
    """
    scratch = Path(test_runner.make_scratch_dir())
    try:
        assert scratch.is_relative_to(Path(tempfile.gettempdir()).resolve()), (
            f"scratch dir {scratch} is not under {tempfile.gettempdir()}"
        )
        assert not scratch.is_relative_to(RITZ_DIR), (
            f"scratch dir {scratch} is inside the tree under test"
        )
    finally:
        os.rmdir(scratch)


@pytest.mark.unit
def test_scratch_dir_is_not_relative_to_the_current_directory(tmp_path, monkeypatch):
    """cwd must not influence where scratch lands.

    The original bug was `dir='.'`, so a helper that still honoured the process
    cwd would pass the previous test whenever pytest happened to run from a
    directory under /tmp. Changing cwd to somewhere outside the temp dir and
    re-checking is what distinguishes "uses gettempdir" from "uses cwd".
    """
    monkeypatch.chdir(tmp_path if not tmp_path.is_relative_to(Path(tempfile.gettempdir()).resolve()) else RITZ_DIR)
    scratch = Path(test_runner.make_scratch_dir())
    try:
        assert scratch.parent != Path.cwd().resolve(), (
            "scratch dir was created in the current directory"
        )
    finally:
        os.rmdir(scratch)


@pytest.mark.unit
def test_scratch_dirs_are_registered_for_cleanup():
    """A created scratch dir is tracked, so a signal handler can remove it.

    Without the registry, a SIGTERM handler has nothing to clean up: the paths
    are local variables in whichever frame happened to be running.
    """
    scratch = Path(test_runner.make_scratch_dir())
    try:
        assert str(scratch) in test_runner._SCRATCH_DIRS
    finally:
        test_runner.cleanup_scratch_dir(str(scratch))
    assert str(scratch) not in test_runner._SCRATCH_DIRS, (
        "cleanup_scratch_dir must deregister the directory it removed"
    )
    assert not scratch.exists()


@pytest.mark.unit
def test_cleanup_removes_symlinks_without_following_them(tmp_path):
    """Cleanup must unlink a symlink, never delete through it.

    This is the property `cleanup_tmpdir_with_symlinks` was written for and the
    reason cleanup cannot simply be `shutil.rmtree`. It is re-pinned here
    because the relocation in #1392 moves the scratch dir but keeps the
    symlinks, so losing this would turn a tidy-up into data loss.
    """
    precious = tmp_path / "precious"
    precious.mkdir()
    (precious / "keepme.txt").write_text("do not delete\n")

    scratch = Path(test_runner.make_scratch_dir())
    os.symlink(precious.resolve(), scratch / "ritzlib")

    test_runner.cleanup_scratch_dir(str(scratch))

    assert not scratch.exists()
    assert (precious / "keepme.txt").read_text() == "do not delete\n", (
        "cleanup followed the symlink and deleted the link target"
    )


@pytest.mark.integration
def test_sigterm_cleans_up_a_live_scratch_dir(tmp_path):
    """The regression test for the outage itself: a killed process must tidy up.

    A `finally` covers exceptions but not process death, so this needs a real
    subprocess and a real signal.

    An earlier draft of this test drove `run_test_file` against a synthetic
    package whose test called `sleep_seconds(60)`, intending the signal to land
    mid-run. `sleep_seconds` does not exist, so the run compile-failed in
    milliseconds, the SIGTERM arrived after the process had already finished,
    and the test passed against a deliberately reintroduced `mkdtemp(dir='.')`.
    It asserted nothing. Mutation testing is the only reason that was caught.

    So the subject is now the thing actually under test -- the handler and the
    registry -- rather than the compiler, which was never the point and only
    supplied ways to finish early. The subprocess allocates scratch, signals
    that it is ready, and blocks forever; the parent kills it and looks at the
    directory. Nothing here can complete on its own, so a pass cannot be
    vacuous.
    """
    ready = tmp_path / "ready"
    driver = tmp_path / "driver.py"
    driver.write_text(
        textwrap.dedent(
            f"""\
            import os, sys, time
            sys.path.insert(0, {str(RITZ0_DIR)!r})
            import test_runner
            test_runner.install_signal_handlers()
            scratch = test_runner.make_scratch_dir()
            # The symlink is what made a leak dangerous rather than merely
            # untidy, so the artefact under test carries one.
            os.symlink({str(tmp_path)!r}, os.path.join(scratch, "ritzlib"))
            with open({str(ready)!r}, "w") as fh:
                fh.write(scratch)
            while True:
                time.sleep(3600)
            """
        )
    )

    proc = subprocess.Popen(
        [sys.executable, str(driver)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if ready.exists() and ready.read_text().strip():
                break
            if proc.poll() is not None:
                raise AssertionError(
                    "driver exited before allocating scratch: "
                    + proc.stderr.read().decode(errors="replace")
                )
            time.sleep(0.05)
        else:
            raise AssertionError("driver never signalled readiness")

        scratch = Path(ready.read_text().strip())
        assert scratch.is_dir(), f"driver did not create {scratch}"
        assert (scratch / "ritzlib").is_symlink()

        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)

    assert not scratch.exists(), (
        f"SIGTERM left the scratch directory {scratch} behind. A surviving "
        "directory with a `ritzlib` symlink is exactly the artefact that formed "
        "the collection-wedging cycle in #1392."
    )
    # The link target must survive: cleanup unlinks, it does not delete through.
    assert tmp_path.is_dir()


@pytest.mark.unit
def test_no_source_file_creates_scratch_in_the_current_directory():
    """No caller may reintroduce `mkdtemp(dir='.')`.

    A grep-shaped test, which is usually a smell -- but the invariant is
    genuinely lexical here. The three call sites in test_runner.py disagreed
    with each other for months (two used `dir='.'`, one used the system temp
    dir) and nothing flagged it, because each is individually reasonable and
    only the *inconsistency* is the bug.

    Production modules are identified by NOT importing pytest, rather than by
    filename. The first draft of this test skipped `path.name.startswith("test_")`
    and so passed against the unfixed tree -- `test_runner.py` is production
    code whose name merely looks like a test module's, and it is the single
    file the check exists to police.
    """
    offenders = []
    for path in sorted(RITZ0_DIR.glob("*.py")):
        text = path.read_text()
        if "import pytest" in text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue  # prose describing the defect is not the defect
            if "mkdtemp(" in line and "dir=" in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "scratch directories must not be pinned to a directory; use "
        "make_scratch_dir():\n  " + "\n  ".join(offenders)
    )
