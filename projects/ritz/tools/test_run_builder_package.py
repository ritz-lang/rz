"""run_builder_package.sh, the builder-matrix job's per-package call
(AGAST #4825, #4826).

Docker isn't available to run for real here, so these stub `docker` on
PATH: `run` writes a fixed summary.json into the mounted /out (as the
image's entrypoint would) and records the call; nothing else runs the real
image. That mirrors test_publish_builder.py's stub, which answers
`image ls` / `image inspect` the same way for publish_builder.sh.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "run_builder_package.sh"
IMAGE = "ghcr.io/ritz-lang/rz-builder:main"

# $STUB_DIR/exit holds the container's own exit status (default 0).
# $STUB_DIR/summary.json, if present, is copied into the mounted /out; its
# absence simulates a run that crashed before writing one.
DOCKER_STUB = r"""#!/usr/bin/env bash
set -u
d="$STUB_DIR"
echo "$*" >> "$d/calls"
if [[ "$1" != "run" ]]; then
    echo "docker stub: unexpected $*" >&2
    exit 3
fi
out=""
prev=""
for a in "$@"; do
    if [[ "$prev" == "-v" && "$a" == *:/out ]]; then
        out="${a%%:/out}"
    fi
    prev="$a"
done
if [[ -n "$out" && -f "$d/summary.json" ]]; then
    cp "$d/summary.json" "$out/summary.json"
fi
exit "$(cat "$d/exit" 2>/dev/null || echo 0)"
"""


def _summary(ok: bool, passed: int) -> dict:
    return {"ok": ok, "test": {"passed": passed, "failed": 0}}


def _run(tmp_path: Path, pkg: Path, *, exit_code: int = 0, summary: dict | None = None):
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "docker").write_text(DOCKER_STUB)
    (stub / "docker").chmod(0o755)
    (tmp_path / "exit").write_text(str(exit_code))
    (tmp_path / "calls").write_text("")
    if summary is not None:
        (tmp_path / "summary.json").write_text(json.dumps(summary))
    out = tmp_path / "out"
    cwd = tmp_path / "cwd"
    cwd.mkdir(exist_ok=True)
    pkg_dir = cwd / pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "ritz.toml").write_text("[package]\nname = \"x\"\n")
    env = dict(os.environ)
    env["PATH"] = f"{stub}:{env['PATH']}"
    env["STUB_DIR"] = str(tmp_path)
    r = subprocess.run(
        ["bash", str(SCRIPT), IMAGE, str(pkg), str(out)],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    calls = (tmp_path / "calls").read_text().splitlines()
    return r, calls, out


@pytest.mark.integration
def test_passes_when_the_run_is_ok_and_tests_passed(tmp_path):
    r, calls, out = _run(tmp_path, Path("projects/buddhafinger"),
                         summary=_summary(True, 5))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "5 test(s) passed" in r.stdout, r.stdout
    assert len(calls) == 1 and calls[0].split()[0] == "run", calls


@pytest.mark.integration
def test_fails_when_the_container_reports_zero_tests_even_if_ok(tmp_path):
    """summary.py's "No tests found, skipping" is ok=true, passed=0: correct
    for a library with none, indistinguishable from a suite that silently
    ran nothing without the count. This script treats a zero count as a
    failure regardless of `ok`."""
    r, calls, out = _run(tmp_path, Path("projects/buddhafinger"),
                         summary=_summary(True, 0))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ran zero tests" in r.stderr, r.stderr


@pytest.mark.integration
def test_fails_when_the_summary_says_not_ok(tmp_path):
    r, calls, out = _run(tmp_path, Path("projects/buddhafinger"),
                         summary=_summary(False, 0))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "run not ok" in r.stderr, r.stderr


@pytest.mark.integration
def test_fails_when_the_container_exits_nonzero(tmp_path):
    r, calls, out = _run(tmp_path, Path("projects/buddhafinger"),
                         exit_code=1, summary=_summary(False, 0))
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_fails_when_no_summary_is_written(tmp_path):
    r, calls, out = _run(tmp_path, Path("projects/buddhafinger"), summary=None)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "is missing after the run" in r.stderr, r.stderr


@pytest.mark.integration
def test_mounts_the_package_read_only_and_out_writable(tmp_path):
    r, calls, out = _run(tmp_path, Path("projects/buddhafinger"),
                         summary=_summary(True, 1))
    assert r.returncode == 0, r.stdout + r.stderr
    call = calls[0]
    assert f"/src/projects/buddhafinger:ro" in call, call
    assert "--network=none" in call, call
    assert "--security-opt seccomp=unconfined" in call, call
    assert call.strip().endswith(f"{IMAGE} /src/projects/buddhafinger"), call


@pytest.mark.integration
def test_rejects_a_package_with_no_manifest(tmp_path):
    out = tmp_path / "out"
    r = subprocess.run(
        ["bash", str(SCRIPT), IMAGE, "projects/does-not-exist", str(out)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "no ritz.toml" in r.stderr, r.stderr


@pytest.mark.integration
def test_usage_on_bad_arguments(tmp_path):
    r = subprocess.run(["bash", str(SCRIPT), IMAGE, "projects/buddhafinger"],
                       cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "usage:" in r.stderr, r.stderr
