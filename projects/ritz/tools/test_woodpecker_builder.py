"""The builder matrix on huburght's Woodpecker (AGAST #4846, epic #4783).

`.woodpecker/builder.yml` runs main.yml's builder-matrix on
`https://ci.fucken.ninja` (kubernetes backend): one step per package, each
step a pod whose image IS the builder image of the commit,
`ghcr.io/ritz-lang/rz-builder:${CI_COMMIT_SHA}` (published by main.yml's
builder-image job). GitHub's hosted builder-matrix runs only when
`woodpecker_fleet.py` says the fleet can't (Aaron, 2026-11-26).

What these tests pin:

* the pipeline is generated: its package steps are exactly
  `builder_matrix.py matrix`, in order (`builder_matrix.py woodpecker
  --write` regenerates it);
* rules of the cluster (adele's, docs/gitea.md there): no privileged step,
  no volumes (so no hostPath, no docker.sock), no services (no dind), no
  secrets, no entrypoint override, no CPU limit, a memory cap; images
  pinned (the builder by the commit, the helper by digest);
* routing: `labels: pool: rz-builder` sends it to the rz agent (one workflow
  at a time, its own namespace and quota); steps have no depends_on, so they
  run one at a time, in order;
* the step script, the image wait and the fleet probe, against stubs.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import builder_matrix  # noqa: E402

REPO_ROOT = TOOLS_DIR.parents[2]
PIPELINE = REPO_ROOT / ".woodpecker" / "builder.yml"
SCRIPTS = REPO_ROOT / ".github" / "scripts"
STEP_SCRIPT = SCRIPTS / "woodpecker_builder_step.sh"
WAIT_SCRIPT = SCRIPTS / "wait_for_builder_image.sh"
FLEET_SCRIPT = SCRIPTS / "woodpecker_fleet.py"
BUILDER_IMAGE = "ghcr.io/ritz-lang/rz-builder:${CI_COMMIT_SHA}"
COMMIT = "0123456789abcdef0123456789abcdef01234567"



def _load_fleet():
    """.github/scripts isn't a package on sys.path: load the script by path,
    as builder_matrix.load_rz() loads `rz`."""
    spec = importlib.util.spec_from_file_location("woodpecker_fleet_4846", FLEET_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


woodpecker_fleet = _load_fleet()


def _pipeline() -> dict:
    return yaml.safe_load(PIPELINE.read_text())


def _steps() -> list[dict]:
    return _pipeline()["steps"]


def _package_steps() -> list[dict]:
    return [s for s in _steps() if s["name"] != "wait-for-image"]


# --- the pipeline is the matrix -------------------------------------------

@pytest.mark.integration
def test_pipeline_is_what_the_generator_writes():
    """A known-failures or package change moves the matrix; regenerate with
    `python3 projects/ritz/tools/builder_matrix.py woodpecker --write`."""
    want = builder_matrix.woodpecker_pipeline(builder_matrix.matrix_entries())
    assert PIPELINE.read_text() == want, (
        ".woodpecker/builder.yml is stale: run "
        "`python3 projects/ritz/tools/builder_matrix.py woodpecker --write`")


@pytest.mark.integration
def test_one_step_per_matrix_package_in_order_after_the_image_wait():
    entries = builder_matrix.matrix_entries()
    steps = _steps()
    assert steps[0]["name"] == "wait-for-image", steps[0]
    cmds = [s["commands"] for s in steps[1:]]
    want = [[(f"bash .github/scripts/woodpecker_builder_step.sh"
              f"{' --build-only' if e['build_only'] else ''} {e['path']}")]
            for e in entries]
    assert cmds == want


@pytest.mark.unit
def test_generator_names_steps_from_paths_and_flags_build_only():
    entries = [{"package": "../bench/r/s2", "path": "bench/r/s2", "build_only": True},
               {"package": "harland/libnet", "path": "projects/harland/libnet",
                "build_only": False}]
    spec = yaml.safe_load(builder_matrix.woodpecker_pipeline(entries))
    names = [s["name"] for s in spec["steps"]]
    assert names == ["wait-for-image", "bench-r-s2", "harland-libnet"]
    assert spec["steps"][1]["commands"] == [
        "bash .github/scripts/woodpecker_builder_step.sh --build-only bench/r/s2"]


@pytest.mark.unit
def test_generator_refuses_two_packages_with_one_step_name():
    entries = [{"package": "a/b", "path": "projects/a/b", "build_only": False},
               {"package": "a-b", "path": "projects/a-b", "build_only": False}]
    with pytest.raises(ValueError, match="step name"):
        builder_matrix.woodpecker_pipeline(entries)


# --- routing and triggers ---------------------------------------------------

@pytest.mark.unit
def test_runs_on_the_rz_builder_agent_for_main_pushes_and_manual_runs():
    spec = _pipeline()
    assert spec["labels"] == {"pool": "rz-builder"}
    assert spec["when"] == [{"event": "push", "branch": "main"}, {"event": "manual"}]


@pytest.mark.unit
def test_steps_run_one_at_a_time_in_order():
    """No depends_on anywhere: Woodpecker runs such steps serially, in order.
    One depends_on would make it a DAG and run every root step at once."""
    for s in _steps():
        assert "depends_on" not in s, s["name"]
    assert "depends_on" not in _pipeline()


@pytest.mark.unit
def test_every_package_runs_after_another_fails_but_the_wait_gates():
    """GitHub's matrix is fail-fast: false; so is this. Each package step runs
    whatever the steps before it did."""
    for s in _package_steps():
        assert s.get("when") == [{"status": ["success", "failure"]}], s["name"]
    assert "when" not in _steps()[0]


# --- the cluster's rules ----------------------------------------------------

@pytest.mark.unit
def test_no_privilege_volumes_services_or_secrets():
    # The YAML, not its header comment (which names what it leaves out).
    text = "\n".join(ln for ln in PIPELINE.read_text().splitlines()
                     if not ln.lstrip().startswith("#"))
    for word in ("privileged", "volumes", "hostPath", "docker.sock", "from_secret",
                 "secrets", "network_mode", "entrypoint", "services", "detach"):
        assert word not in text, word
    spec = _pipeline()
    assert not spec.get("services")
    for s in _steps():
        assert set(s) <= {"name", "image", "commands", "when", "backend_options"}, s


@pytest.mark.unit
def test_package_steps_run_in_the_builder_image_of_the_commit():
    for s in _package_steps():
        assert s["image"] == BUILDER_IMAGE, s


@pytest.mark.unit
def test_the_wait_step_image_is_pinned_by_tag_and_digest():
    image = _steps()[0]["image"]
    m = re.fullmatch(r"[\w./-]+:([\w.-]+)@sha256:[0-9a-f]{64}", image)
    assert m and m.group(1) != "latest", image
    assert _steps()[0]["commands"] == [
        ("sh .github/scripts/wait_for_builder_image.sh "
         "ghcr.io/ritz-lang/rz-builder ${CI_COMMIT_SHA}")]


@pytest.mark.unit
def test_memory_is_capped_and_cpu_never_limited():
    """adele's cluster: no CPU limits (Don't Starve The Hungry). No CPU
    request either, so under contention a step gets the smallest CPU weight,
    below everything else on huburght; memory is capped at 8Gi."""
    for s in _package_steps():
        res = s["backend_options"]["kubernetes"]["resources"]
        assert res == {"requests": {"memory": "1Gi"}, "limits": {"memory": "8Gi"}}, s
    for s in _steps():
        text = json.dumps(s.get("backend_options", {}))
        assert "cpu" not in text, s["name"]


@pytest.mark.unit
def test_package_steps_run_as_a_non_root_user_without_escalation():
    """Rootless (Aaron, 2026-11-26): no daemon, no root. The image's entrypoint
    only reads the checkout and writes under mktemp, which uid 1000 can
    (checked in the image of 31d73e00e: ritzlib's 896 tests and goliath's 72
    pass as 1000:1000). 1000 is also Woodpecker's default fsGroup."""
    for s in _package_steps():
        sc = s["backend_options"]["kubernetes"]["securityContext"]
        assert sc == {"runAsNonRoot": True, "runAsUser": 1000, "runAsGroup": 1000,
                      "allowPrivilegeEscalation": False}, s["name"]


@pytest.mark.unit
def test_steps_leave_seccomp_to_the_cluster():
    """ritzlib's tests call io_uring, which RuntimeDefault seccomp blocks;
    baseline Pod Security forbids an explicit Unconfined. Woodpecker leaves
    the profile unset unless a step names one, so none does. (Under
    Docker's default profile, the image of 31d73e00e fails 19 of ritzlib's
    896 tests.)"""
    for s in _steps():
        k8s = s.get("backend_options", {}).get("kubernetes", {})
        assert set(k8s) <= {"resources", "securityContext"}, s["name"]
        assert "seccomp" not in json.dumps(k8s), s["name"]


# --- the step script --------------------------------------------------------

# A stand-in for the image's entrypoint (/usr/local/bin/rz-builder): records
# its environment and arguments, writes $STUB_DIR/summary.json to $RZ_OUT.
ENTRY_STUB = r"""#!/usr/bin/env bash
d="$STUB_DIR"
printf 'RZ_ROOT=%s RZ_OUT=%s ARGS=%s\n' "$RZ_ROOT" "$RZ_OUT" "$*" >> "$d/calls"
mkdir -p "$RZ_OUT"
echo "build log line" > "$RZ_OUT/build.log"
[[ -f "$d/summary.json" ]] && cp "$d/summary.json" "$RZ_OUT/summary.json"
exit "$(cat "$d/exit" 2>/dev/null || echo 0)"
"""


def _step(tmp_path: Path, *args: str, summary: dict | None, exit_code: int = 0,
          pkg: str = "projects/sage"):
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "rz-builder").write_text(ENTRY_STUB)
    (stub / "rz-builder").chmod(0o755)
    (tmp_path / "exit").write_text(str(exit_code))
    (tmp_path / "calls").write_text("")
    if summary is not None:
        (tmp_path / "summary.json").write_text(json.dumps(summary))
    ws = tmp_path / "ws"
    (ws / pkg).mkdir(parents=True, exist_ok=True)
    (ws / pkg / "ritz.toml").write_text("[package]\nname = \"x\"\n")
    (ws / ".github" / "scripts").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}", STUB_DIR=str(tmp_path))
    r = subprocess.run(["bash", str(STEP_SCRIPT), *args], cwd=ws, env=env,
                       capture_output=True, text=True, timeout=30, check=False)
    return r, (tmp_path / "calls").read_text().splitlines(), ws


@pytest.mark.integration
def test_step_runs_the_entrypoint_on_the_checkout_and_counts_tests(tmp_path):
    r, calls, ws = _step(tmp_path, "projects/sage",
                         summary={"ok": True, "test": {"passed": 3}})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "3 test(s) passed" in r.stdout
    [call] = calls
    assert call.startswith(f"RZ_ROOT={ws} "), call
    out = call.split("RZ_OUT=")[1].split()[0]
    assert not out.startswith(str(ws)), "out must not land in the checkout"
    assert call.endswith("ARGS=projects/sage"), call


@pytest.mark.integration
def test_step_fails_on_zero_tests_and_shows_the_logs(tmp_path):
    r, _, _ = _step(tmp_path, "projects/sage", summary={"ok": True, "test": {"passed": 0}})
    assert r.returncode == 1
    assert "ran zero tests" in r.stderr


@pytest.mark.integration
def test_step_fails_when_the_entrypoint_does(tmp_path):
    r, _, _ = _step(tmp_path, "projects/sage", exit_code=1,
                    summary={"ok": False, "test": {"passed": 0}})
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_step_fails_when_the_entrypoint_does_even_with_an_ok_summary(tmp_path):
    """The entrypoint's exit status is the verdict; the summary only adds the
    zero-test check on top."""
    r, _, _ = _step(tmp_path, "projects/sage", exit_code=1,
                    summary={"ok": True, "test": {"passed": 3}})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "rz-builder exited 1" in r.stderr


@pytest.mark.integration
def test_step_fails_when_no_summary_is_written(tmp_path):
    r, _, _ = _step(tmp_path, "projects/sage", summary=None)
    assert r.returncode == 1
    assert "missing" in r.stderr


@pytest.mark.integration
def test_step_build_only_passes_on_zero_tests(tmp_path):
    r, calls, _ = _step(tmp_path, "--build-only", "projects/indium", pkg="projects/indium",
                        summary={"ok": True, "test": {"passed": 0}})
    assert r.returncode == 0, r.stdout + r.stderr
    assert calls[0].endswith("ARGS=--build-only projects/indium"), calls


@pytest.mark.integration
def test_step_usage_on_bad_arguments(tmp_path):
    r, calls, _ = _step(tmp_path, summary=None)
    assert r.returncode == 2 and "usage:" in r.stderr
    assert calls == []


# --- waiting for the image --------------------------------------------------

# curl stub: answers the ghcr token endpoint with a token, and the manifest
# HEAD with the status in $STUB_DIR/status (a line per call; the last repeats).
CURL_STUB = r"""#!/bin/sh
d="$STUB_DIR"
echo "$*" >> "$d/calls"
case "$*" in
*/token\?*) echo '{"token":"tok"}'; exit 0 ;;
esac
n=$(grep -c manifests "$d/calls")
code=$(sed -n "${n}p" "$d/status")
[ -n "$code" ] || code=$(tail -n 1 "$d/status")
printf '%s' "$code"
"""


def _wait(tmp_path: Path, statuses: list[str], *args: str, timeout: str = "5"):
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "curl").write_text(CURL_STUB)
    (stub / "curl").chmod(0o755)
    (tmp_path / "status").write_text("".join(f"{s}\n" for s in statuses))
    (tmp_path / "calls").write_text("")
    env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}", STUB_DIR=str(tmp_path),
               WAIT_TIMEOUT=timeout, WAIT_INTERVAL="0")
    r = subprocess.run(["sh", str(WAIT_SCRIPT), *args], env=env,
                       capture_output=True, text=True, timeout=30, check=False)
    return r, (tmp_path / "calls").read_text().splitlines()


@pytest.mark.integration
def test_wait_returns_once_the_commit_tag_exists(tmp_path):
    r, calls = _wait(tmp_path, ["404", "404", "200"], "ghcr.io/ritz-lang/rz-builder", COMMIT)
    assert r.returncode == 0, r.stdout + r.stderr
    heads = [c for c in calls if "manifests" in c]
    assert len(heads) == 3
    assert heads[-1].endswith(f"https://ghcr.io/v2/ritz-lang/rz-builder/manifests/{COMMIT}")
    assert any("scope=repository:ritz-lang/rz-builder:pull" in c for c in calls)


@pytest.mark.integration
def test_wait_fails_after_its_timeout(tmp_path):
    start = time.monotonic()
    r, _ = _wait(tmp_path, ["404"], "ghcr.io/ritz-lang/rz-builder", COMMIT, timeout="1")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "not published" in r.stderr
    assert time.monotonic() - start < 20


@pytest.mark.integration
@pytest.mark.parametrize("args", [
    ("ghcr.io/ritz-lang/rz-builder", "main"),
    ("ghcr.io/ritz-lang/rz-builder:main", COMMIT),
    ("ghcr.io/ritz-lang/rz-builder",),
])
def test_wait_refuses_anything_but_an_image_and_a_full_commit(tmp_path, args):
    r, calls = _wait(tmp_path, ["200"], *args)
    assert r.returncode == 2, r.stdout + r.stderr
    assert calls == []


# --- the fallback switch ----------------------------------------------------

NOW = 1_800_000_000


def _fetch(routes: dict):
    """A fetch(url) -> (status, body) that answers from routes, else raises."""
    def fetch(url):
        for suffix, answer in routes.items():
            if url.endswith(suffix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise OSError(f"no route to {url}")
    return fetch


UP = {
    "/api/healthz": (204, b""),
    "/api/repos/lookup/ritz-lang/rz": (200, json.dumps({"id": 7}).encode()),
    "/api/repos/7/pipelines": (200, json.dumps([
        {"status": "success", "created": NOW - 3600},
        {"status": "running", "created": NOW - 60},
        {"status": "pending", "created": NOW - 120}]).encode()),
}


@pytest.mark.unit
def test_fleet_up_means_no_hosted_run():
    hosted, why = woodpecker_fleet.decide(
        "https://ci.example", "ritz-lang/rz", _fetch(UP), now=NOW)
    assert hosted is False, why


@pytest.mark.unit
@pytest.mark.parametrize("change,reason", [
    ({"/api/healthz": OSError("connection refused")}, "server"),
    ({"/api/healthz": (502, b"bad gateway")}, "server"),
    ({"/api/repos/lookup/ritz-lang/rz": (404, b"")}, "repo"),
    ({"/api/repos/7/pipelines": (200, json.dumps([
        {"status": "pending", "created": NOW - 31 * 60}]).encode())}, "pending"),
    ({"/api/repos/7/pipelines": (200, b"not json")}, "pipelines"),
])
def test_fleet_down_or_stuck_falls_back_to_hosted(change, reason):
    """Server down, the repo not activated (or not public), or a pipeline
    stuck pending past STUCK_SECONDS (no agent picks it up): GitHub runs the
    matrix itself. Every doubt falls back to hosted."""
    hosted, why = woodpecker_fleet.decide(
        "https://ci.example", "ritz-lang/rz", _fetch({**UP, **change}), now=NOW)
    assert hosted is True
    assert reason in why, why


@pytest.mark.integration
def test_fleet_cli_prints_a_github_output_line_and_never_fails():
    """An unreachable server is a hosted run, not a red job."""
    r = subprocess.run([sys.executable, str(FLEET_SCRIPT), "http://127.0.0.1:9", "ritz-lang/rz"],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "hosted=true", r.stdout


# --- main.yml: hosted only when the fleet is down ---------------------------

MAIN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"
HOSTED = "needs.builder-fleet.outputs.hosted == 'true'"


def _main_jobs() -> dict:
    return yaml.safe_load(MAIN_WORKFLOW.read_text())["jobs"]


@pytest.mark.unit
def test_builder_fleet_probes_woodpecker_only_after_a_gitea_push():
    """Woodpecker runs what gitea-push pushed (test_gitea_push.py pins that
    side): with no push (a workflow_dispatch run, no secret, a failed push)
    the run is GitHub's alone, so the probe only asks after one."""
    job = _main_jobs()["builder-fleet"]
    assert job["outputs"] == {"hosted": "${{ steps.probe.outputs.hosted }}"}
    assert job["timeout-minutes"] <= 5
    [probe] = [s for s in job["steps"] if s.get("id") == "probe"]
    run = probe["run"]
    assert ('python3 .github/scripts/woodpecker_fleet.py https://ci.fucken.ninja '
            'ritz-lang/rz >> "$GITHUB_OUTPUT"') in run, run
    assert re.search(r'if \[\[ "\$PUSHED" != true \]\]; then\s+'
                     r'echo "hosted=true" >> "\$GITHUB_OUTPUT"', run), run


@pytest.mark.unit
def test_the_hosted_matrix_runs_only_when_the_fleet_is_down():
    jobs = _main_jobs()
    for name in ("builder-packages", "builder-matrix"):
        assert "builder-fleet" in jobs[name]["needs"], name
        assert jobs[name]["if"] == HOSTED, name
    assert jobs["builder-matrix"]["needs"] == ["builder-fleet", "builder-packages",
                                               "builder-image"]


@pytest.mark.unit
def test_builder_image_always_builds_and_hands_over_the_image_only_when_hosted():
    """The image is built on every run: Woodpecker pulls it from ghcr.io
    when the fleet is up, and the hosted matrix takes it as an artifact when
    it isn't. Saving and uploading ~400 MiB is skipped when nobody reads it."""
    job = _main_jobs()["builder-image"]
    assert "if" not in job
    assert job["needs"] == ["builder-fleet"]
    handover = [s for s in job["steps"]
                if "rz-builder:ci" in str(s.get("run", "")) or "upload-artifact" in str(s.get("uses", ""))]
    assert len(handover) == 2, handover
    for s in handover:
        assert s["if"] == HOSTED, s
