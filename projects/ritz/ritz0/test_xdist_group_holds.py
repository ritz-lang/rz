#!/usr/bin/env python3
"""`xdist_group` must really keep a group on one worker, on the installed pytest.

Found by AGAST #2251. conftest.py item 5 relies on the "tree" group to serialize
every test that shares in-tree state, such as projects/ritz/build/main. xdist
3.8.0 makes a group by writing `item._nodeid`, and pytest 9.2.0 stopped reading
that attribute (`Node.nodeid` is now `str(self._id)`), so each test became its
own scope. Nothing reported that: a split group passes unless two tests happen
to collide, and on CI they sometimes did, with one test running the other's
binary and exiting 7 instead of 11.

So these tests run a real session and look at where its tests landed, rather
than inspecting nodeids: they hold for any way xdist makes a group, and they
fail on every run, not only on an unlucky one.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

MEMBERS = 4

PROBE = """\
import os
from pathlib import Path

import pytest

{mark}


@pytest.mark.parametrize("member", range({members}))
def test_member(member):
    landed = Path(os.environ["GROUP_PROBE_DIR"]) / f"member-{{member}}"
    landed.write_text(os.environ["PYTEST_XDIST_WORKER"])
"""


def _workers_used(tmp_path: Path, mark: str) -> set[str]:
    """Run `MEMBERS` tests under -n 2 --dist loadgroup; return the workers used."""
    session = tmp_path / "session"
    landed = tmp_path / "landed"
    session.mkdir()
    landed.mkdir()
    (session / "test_probe.py").write_text(PROBE.format(mark=mark, members=MEMBERS))
    # Not this session's PYTEST_* (PYTEST_ADDOPTS, PYTEST_XDIST_WORKER, ...): the
    # nested session must schedule for itself.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env["GROUP_PROBE_DIR"] = str(landed)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-n", "2", "--dist", "loadgroup",
         "-p", "no:cacheprovider", "--rootdir", str(session), "test_probe.py"],
        cwd=session, env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    files = list(landed.iterdir())
    assert len(files) == MEMBERS, result.stdout + result.stderr
    return {path.read_text() for path in files}


@pytest.mark.integration
def test_a_group_runs_on_one_worker(tmp_path):
    workers = _workers_used(tmp_path, 'pytestmark = pytest.mark.xdist_group("probe")')
    assert len(workers) == 1, (
        f"an xdist_group ran on {sorted(workers)}, so the \"tree\" group no longer "
        "serializes tests that share in-tree state (AGAST #2251). The installed "
        "pytest and pytest-xdist don't work together: see the pytest cap in "
        "projects/ritz/requirements.txt."
    )


@pytest.mark.integration
def test_ungrouped_tests_use_both_workers(tmp_path):
    # Keeps the test above honest: one worker only means something if the same
    # session would otherwise have used two.
    assert len(_workers_used(tmp_path, "")) == 2
