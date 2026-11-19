"""Tests for spawn_guard, the `integration` marker audit (AGAST #1805).

36 files that spawned ritz0/ritz1/clang carried no `integration` mark, so
`-m "not integration"` (the smoke tier's selection) silently included tests
that compile and link.  spawn_guard fails any test that starts a process —
in setup, call or teardown, directly or through ritz0_inproc — unless it is
marked `integration`.  It watches what the test actually does rather than
grepping its source, so it cannot be fooled by a helper imported from
another module, and it cannot flag a pure test for mentioning `subprocess`.
AGAST #4264 adds one static check on top: an unmarked test whose own source
calls a spawn API fails in setup, so skipping for a missing tool can't hide it.

Every case is a scratch test file, and one nested pytest runs them all with
the plugin loaded by name, exactly as ritz0/conftest.py loads it.  Each case
gets its own file, so a module-scoped fixture in one can't leak into another,
and each test here reads its own case's verdict from the session's JUnit XML.
AGAST #3898: a nested session per case cost ~3 s of plugin autoload each
(22 CPU-s for the file); now it's one session with autoload off.
"""

import os
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parent

CASES = {
    # The spawn sits in a helper, outside the test's own source, so the
    # runtime watch (not AGAST #4264's static check) is what catches it.
    "unmarked_spawn": """
        import subprocess
        def spawn():
            subprocess.run(["true"])
        def test_spawns():
            spawn()
    """,
    "marked_spawn": """
        import pytest, subprocess
        pytestmark = pytest.mark.integration
        def test_spawns():
            subprocess.run(["true"])
    """,
    "pure_mentions_subprocess": """
        import subprocess
        def test_pure():
            assert subprocess.PIPE == -1
    """,
    "spawn_in_fixture_setup": """
        import pytest, subprocess
        @pytest.fixture(scope="module")
        def built():
            subprocess.run(["true"])
        def test_uses(built):
            pass
    """,
    "inproc_oracle": """
        from ritz0_inproc import ritz0_oracle
        def test_oracle():
            ritz0_oracle("pub fn main() -> i32\\n    0\\n")
    """,
    "os_system": """
        import os
        def shell():
            os.system("true")
        def test_shell():
            shell()
    """,
    # AGAST #4264: a test that skips when an optional tool is missing never
    # reaches its spawn on such a host, so the runtime watch saw nothing and
    # the gate passed tests that CI (which has the tool) then failed.
    "skip_hides_spawn": """
        import pytest, shutil, subprocess
        def test_tool_gated():
            tool = shutil.which("no-such-tool-4264")
            if tool is None:
                pytest.skip("no-such-tool-4264 not on PATH")
            subprocess.run([tool])
    """,
    "skipif_hides_spawn": """
        import pytest, subprocess
        @pytest.mark.skipif(True, reason="optional tool missing")
        def test_tool_gated():
            subprocess.run(["no-such-tool-4264"])
    """,
    "marked_skip_hides_spawn": """
        import pytest, shutil, subprocess
        @pytest.mark.integration
        def test_tool_gated():
            if shutil.which("no-such-tool-4264") is None:
                pytest.skip("no-such-tool-4264 not on PATH")
            subprocess.run(["no-such-tool-4264"])
    """,
}


@pytest.fixture(scope="module")
def verdicts(tmp_path_factory):
    """{case: (outcome, message)} from one nested session over every case.

    outcome is "passed", or JUnit's tag: "failure" (in the call) or "error"
    (in setup or teardown).
    """
    tmp = tmp_path_factory.mktemp("spawn_guard")
    for name, body in CASES.items():
        (tmp / f"test_{name}.py").write_text(textwrap.dedent(body))
    report = tmp / "report.xml"
    # Not this session's PYTEST_* (the gate's PYTEST_ADDOPTS names files to
    # run, PYTEST_XDIST_WORKER, ...): the nested session runs only the cases.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env["PYTHONPATH"] = str(RITZ0_DIR)
    # Installed plugins (django, asyncio, cov, ...) cost seconds to load and
    # play no part in spawn_guard; it is loaded by name below.
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "spawn_guard",
         "-p", "no:cacheprovider", f"--junitxml={report}", str(tmp)],
        cwd=tmp, env=env, capture_output=True, text=True, timeout=300,
    )
    assert report.exists(), r.stdout + r.stderr
    found = {}
    for case in ET.parse(report).iter("testcase"):
        name = case.get("classname").rsplit(".", 1)[-1].removeprefix("test_")
        bad = case.find("failure")
        if bad is None:
            bad = case.find("error")
        outcome = "passed" if bad is None else bad.tag
        if bad is not None:
            message = (bad.get("message") or "") + "\n" + (bad.text or "")
        else:
            message = ""
        # A setup error and the call's pass are both reported; the worst wins.
        if found.get(name, ("passed",))[0] == "passed":
            found[name] = (outcome, message)
    assert sorted(found) == sorted(CASES), r.stdout + r.stderr
    return found


def test_unmarked_spawn_fails(verdicts):
    outcome, message = verdicts["unmarked_spawn"]
    assert outcome == "failure", message
    # The guard's own sentence: its hint line names the mark too.
    assert "not marked `integration`" in message and "true" in message


def test_marked_spawn_passes(verdicts):
    assert verdicts["marked_spawn"][0] == "passed", verdicts["marked_spawn"]


def test_pure_test_mentioning_subprocess_passes(verdicts):
    assert verdicts["pure_mentions_subprocess"][0] == "passed", (
        verdicts["pure_mentions_subprocess"]
    )


def test_spawn_in_fixture_setup_fails(verdicts):
    outcome, message = verdicts["spawn_in_fixture_setup"]
    assert outcome in ("error", "failure"), message


def test_inproc_ritz0_counts_as_a_spawn(verdicts):
    outcome, message = verdicts["inproc_oracle"]
    assert outcome == "failure", message
    # Not just "ritz0": that is in this case's path.  ritz0_inproc notes "ritz0
    # (in-process) ..." through spawn_guard.note_spawn.
    assert "ritz0 (in-process)" in message or "ritz0_oracle (in-process)" in message


def test_os_system_counts_as_a_spawn(verdicts):
    outcome, message = verdicts["os_system"]
    assert outcome == "failure", message


@pytest.mark.parametrize("case", ["skip_hides_spawn", "skipif_hides_spawn"])
def test_a_skip_cannot_hide_an_unmarked_spawn(verdicts, case):
    # AGAST #4264: the spawn is in the test's own source, so the guard fails
    # it in setup, before a skip (in the body or a skipif) can hide it.
    outcome, message = verdicts[case]
    assert outcome in ("error", "failure"), message
    assert "not marked `integration`" in message and "subprocess.run" in message


def test_a_marked_tool_gated_test_still_skips(verdicts):
    assert verdicts["marked_skip_hides_spawn"][0] == "passed", (
        verdicts["marked_skip_hides_spawn"]
    )
