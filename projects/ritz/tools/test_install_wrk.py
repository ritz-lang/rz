#!/usr/bin/env python3
"""Self-tests for .github/scripts/install_wrk.sh -- AGAST #2743.

build-all's "Install test tools" step apt-installs wrk for smoke_stack's
stack.wrk_index (#2464). GitHub's runners lost DNS for the Ubuntu mirrors on
three build-all runs in a row, and a single `apt-get install || (update &&
install)` gave up after one blip, so build-all went red with nothing wrong in
the code. The script retries update+install with backoff. It must still fail,
loudly, when wrk never installs: the smoke stack must not lose its wrk check
silently.

We can't run Actions here, so these tests put stub `sudo` and `apt-get` on
PATH: one that fails N times then "installs" wrk, and one that always fails.

Run with:
    python3 -m pytest projects/ritz/tools/test_install_wrk.py -q
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "install_wrk.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"

# apt-get stub. Counts every `install` in $STUB_DIR/installs and every
# `update` in $STUB_DIR/updates. The first $FAIL_INSTALLS installs fail with
# the DNS error the runners printed; after that, install writes a `wrk`
# onto PATH and succeeds. FAIL_INSTALLS=always never succeeds.
APT_STUB = r"""#!/usr/bin/env bash
set -u
d="$STUB_DIR"
case " $* " in
  *" update "*)
    echo x >> "$d/updates"
    echo "$*" >> "$d/update-args"
    exit 0 ;;
  *" install "*)
    echo x >> "$d/installs"
    echo "$*" >> "$d/install-args"
    n=$(wc -l < "$d/installs")
    if [ "$FAIL_INSTALLS" = always ] || [ "$n" -le "$FAIL_INSTALLS" ]; then
      echo "Temporary failure resolving 'azure.archive.ubuntu.com'" >&2
      echo "E: Unable to fetch some archives" >&2
      exit 100
    fi
    printf '#!/bin/sh\necho "wrk 4.1.0 [stub]"\n' > "$d/bin/wrk"
    chmod +x "$d/bin/wrk"
    exit 0 ;;
esac
echo "apt-get stub: unexpected args: $*" >&2
exit 2
"""

SUDO_STUB = '#!/bin/sh\nexec "$@"\n'

# The only real tools on the sealed PATH. A developer's (or a runner's)
# own wrk must not leak in and let the script pass without installing.
REAL_TOOLS = ("bash", "sh", "wc", "sleep", "head", "chmod")


def _count(stub: Path, name: str) -> int:
    f = stub / name
    return len(f.read_text().splitlines()) if f.exists() else 0


@pytest.fixture
def stub(tmp_path):
    (tmp_path / "bin").mkdir()
    for name, body in (("apt-get", APT_STUB), ("sudo", SUDO_STUB)):
        p = tmp_path / "bin" / name
        p.write_text(body)
        p.chmod(0o755)
    (tmp_path / "sys").mkdir()
    for tool in REAL_TOOLS:
        real = shutil.which(tool)
        assert real, f"{tool} is needed to run the stubs"
        (tmp_path / "sys" / tool).symlink_to(real)
    return tmp_path


def _run(stub: Path, fail_installs: str, attempts: int = 4):
    # Sealed PATH: the stubs, then symlinks to REAL_TOOLS. Nothing else.
    env = {
        "PATH": f"{stub / 'bin'}:{stub / 'sys'}",
        "STUB_DIR": str(stub),
        "FAIL_INSTALLS": fail_installs,
        "WRK_INSTALL_ATTEMPTS": str(attempts),
        "WRK_INSTALL_BACKOFF": "0",  # no real sleeping in tests
        "HOME": str(stub),
    }
    return subprocess.run(
        [str(stub / "sys" / "bash"), str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.unit
def test_first_try_succeeds_without_retrying(stub):
    r = _run(stub, "0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _count(stub, "installs") == 1
    assert (stub / "bin" / "wrk").exists()


@pytest.mark.unit
def test_transient_failures_are_retried_until_wrk_installs(stub):
    # The runners' failure: DNS out for a while, then back.
    r = _run(stub, "2", attempts=4)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _count(stub, "installs") == 3
    # A retry refreshes the package lists: stale lists were half of the
    # original `|| (update && install)` fallback.
    assert _count(stub, "updates") >= 2
    assert "wrk 4.1.0" in r.stdout


@pytest.mark.unit
def test_permanent_failure_exits_nonzero_and_says_why(stub):
    r = _run(stub, "always", attempts=3)
    assert r.returncode != 0
    assert _count(stub, "installs") == 3, "must use every attempt, then stop"
    out = r.stdout + r.stderr
    # A GitHub annotation, naming the tool, the attempts and the consequence.
    assert "::error" in out
    assert "wrk" in out and "3 attempts" in out
    assert "smoke" in out.lower()
    # apt's own error reaches the log, so the cause (DNS) is visible.
    assert "Temporary failure resolving" in out


@pytest.mark.unit
def test_install_that_leaves_no_wrk_on_path_fails(stub, tmp_path):
    # apt-get exits 0 but no wrk appears: never report success on that.
    (stub / "bin" / "apt-get").write_text("#!/bin/sh\nexit 0\n")
    r = _run(stub, "0", attempts=2)
    assert r.returncode != 0
    assert "::error" in r.stdout + r.stderr


@pytest.mark.unit
def test_apt_is_non_interactive_and_retries_its_own_fetches(stub):
    r = _run(stub, "0")
    assert r.returncode == 0, r.stdout + r.stderr
    args = (stub / "install-args").read_text()
    assert "-y" in args.split()
    assert "Acquire::Retries" in args


@pytest.mark.unit
def test_workflow_step_runs_the_script_with_a_timeout():
    wf = yaml.safe_load(WORKFLOW.read_text())
    steps = [
        s
        for s in wf["jobs"]["build-all"]["steps"]
        if "install test tools" in s.get("name", "").lower()
    ]
    assert len(steps) == 1
    step = steps[0]
    assert step["run"].strip() == "bash .github/scripts/install_wrk.sh"
    # Retries are bounded by the script; the timeout bounds a hung apt.
    assert 0 < step["timeout-minutes"] <= 15
    # No `|| true` / continue-on-error: a failed install fails build-all.
    assert not step.get("continue-on-error")
    assert "||" not in step["run"]


@pytest.mark.unit
def test_script_is_executable_bash():
    assert SCRIPT.read_text().startswith("#!/usr/bin/env bash\n")
    assert os.access(SCRIPT, os.X_OK)
