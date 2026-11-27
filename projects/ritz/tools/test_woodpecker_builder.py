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
        {"status": "pending", "created": NOW - 11 * 60}]).encode())}, "pending"),
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
HOSTED = "needs.builder-watch.outputs.hosted == 'true'"


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
def test_builder_watch_waits_for_this_commits_pipeline_only_when_routed_to_woodpecker():
    """builder-fleet said Woodpecker: builder-watch gives this commit's
    pipeline FALLBACK_SECONDS to start. builder-fleet said hosted (or
    failed): it passes that on at once and says why."""
    job = _main_jobs()["builder-watch"]
    assert job["needs"] == ["builder-fleet"]
    assert job["if"] == "${{ !cancelled() }}"
    assert job["outputs"] == {"hosted": "${{ steps.watch.outputs.hosted }}",
                              "why": "${{ steps.watch.outputs.why }}"}
    assert (woodpecker_fleet.FALLBACK_SECONDS // 60 + 2
            <= job["timeout-minutes"] <= woodpecker_fleet.FALLBACK_SECONDS // 60 + 10)
    assert "permissions" in job and job["permissions"] == {"contents": "read"}
    [step] = [s for s in job["steps"] if s.get("id") == "watch"]
    assert step["env"]["FLEET_HOSTED"] == "${{ needs.builder-fleet.outputs.hosted }}"
    run = step["run"]
    assert re.search(r'if \[\[ "\$FLEET_HOSTED" != false \]\]; then', run), run
    assert ('python3 .github/scripts/woodpecker_fleet.py --watch "${{ github.sha }}" '
            'https://ci.fucken.ninja ritz-lang/rz >> "$GITHUB_OUTPUT"') in run, run
    assert "secrets." not in str(job)


@pytest.mark.unit
def test_the_hosted_matrix_runs_only_when_woodpecker_did_not_take_it():
    jobs = _main_jobs()
    for name in ("builder-packages", "builder-matrix"):
        assert "builder-watch" in jobs[name]["needs"], name
        assert jobs[name]["if"] == HOSTED, name
    assert jobs["builder-matrix"]["needs"] == ["builder-watch", "builder-packages",
                                               "builder-image"]


@pytest.mark.unit
def test_the_hosted_fallback_log_says_why():
    [step] = [s for s in _main_jobs()["builder-packages"]["steps"]
              if "WHY" in s.get("env", {})]
    assert step["env"]["WHY"] == "${{ needs.builder-watch.outputs.why }}"
    assert 'echo "::notice' in step["run"] and "$WHY" in step["run"], step["run"]


@pytest.mark.unit
def test_builder_image_always_builds_and_hands_over_the_image_only_when_hosted():
    """The image is built on every run: Woodpecker pulls it from ghcr.io
    when it took the commit, and the hosted matrix takes it as an artifact
    when it didn't. It waits for builder-watch so the hand-over follows the
    final decision; Woodpecker's first step waits for the image, and the
    watch needs only the pipeline started, not the image."""
    job = _main_jobs()["builder-image"]
    assert "if" not in job or job["if"] == "${{ !cancelled() }}"
    assert job["needs"] == ["builder-watch"]
    handover = [s for s in job["steps"]
                if "rz-builder:ci" in str(s.get("run", "")) or "upload-artifact" in str(s.get("uses", ""))]
    assert len(handover) == 2, handover
    for s in handover:
        assert s["if"] == HOSTED, s


# --- the watch: Woodpecker gets FALLBACK_SECONDS to start the commit -------
#
# Faked API answers and a fake clock: a dry run of the decision, so nobody
# waits ten minutes on a real dead pipeline (rz, 2026-11-27).

SHA = "97eacd11d8ee" + "0" * 28


class _Clock:
    """time() and sleep() for watch(): sleep advances time, never blocks."""

    def __init__(self, t: float = NOW):
        self.t = t
        self.slept = 0.0

    def time(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s
        self.slept += s


_LOOKUP = (200, json.dumps({"id": 3}).encode())


def _watch_fetch(clock: _Clock, pipelines, *, lookup=_LOOKUP):
    """pipelines(t) -> list of pipeline dicts (or an Exception) at time t."""
    def fetch(url):
        if url.endswith("/api/repos/lookup/ritz-lang/rz"):
            return lookup
        if url.endswith("/api/repos/3/pipelines"):
            answer = pipelines(clock.t)
            if isinstance(answer, Exception):
                raise answer
            return 200, json.dumps(answer).encode()
        raise OSError(f"no route to {url}")
    return fetch


def _run_watch(pipelines, clock=None, **kw):
    clock = clock or _Clock()
    hosted, why = woodpecker_fleet.watch(
        "https://ci.example", "ritz-lang/rz", SHA,
        _watch_fetch(clock, pipelines, **kw), clock=clock.time, sleep=clock.sleep)
    return hosted, why, clock


def _pl(status, created=NOW, started=0, commit=SHA, **extra):
    return {"number": 1, "commit": commit, "status": status,
            "created": created, "started": started, **extra}


@pytest.mark.unit
def test_watch_one_constant_of_about_ten_minutes():
    assert woodpecker_fleet.FALLBACK_SECONDS == 10 * 60
    assert woodpecker_fleet.STUCK_SECONDS == woodpecker_fleet.FALLBACK_SECONDS


@pytest.mark.unit
def test_watch_started_pipeline_means_woodpecker_runs_it():
    hosted, why, clock = _run_watch(lambda t: [_pl("running", started=NOW + 5)])
    assert hosted is False, why
    assert clock.slept == 0


@pytest.mark.unit
def test_watch_waits_while_pending_and_takes_a_late_start():
    """Pending, then started at minute 4 (an agent finishing other work)."""
    def pls(t):
        if t < NOW + 240:
            return [_pl("pending")]
        return [_pl("running", started=NOW + 240)]
    hosted, why, clock = _run_watch(pls)
    assert hosted is False, why
    assert 240 <= clock.slept < woodpecker_fleet.FALLBACK_SECONDS


@pytest.mark.unit
def test_watch_pending_forever_falls_back_at_the_deadline_and_says_why():
    hosted, why, clock = _run_watch(lambda t: [_pl("pending"),
                                               _pl("pending", commit="f" * 40)])
    assert hosted is True
    assert "pending" in why and "10 min" in why and "no agent" in why, why
    assert SHA[:12] in why, why
    # The deadline, not a poll more than one interval past it.
    assert (woodpecker_fleet.FALLBACK_SECONDS <= clock.slept
            < woodpecker_fleet.FALLBACK_SECONDS + woodpecker_fleet.POLL_SECONDS + 1)


@pytest.mark.unit
def test_watch_deadline_counts_from_the_pipeline_created_not_the_watch_start():
    """Created 9.5 min before the watch began: half a minute left."""
    created = NOW - 570
    hosted, why, clock = _run_watch(lambda t: [_pl("pending", created=created)])
    assert hosted is True, why
    assert clock.slept < 30 + woodpecker_fleet.POLL_SECONDS + 1


@pytest.mark.unit
def test_watch_no_pipeline_for_the_commit_falls_back():
    """The webhook never fired (or fired for another commit)."""
    hosted, why, clock = _run_watch(lambda t: [_pl("success", commit="e" * 40,
                                                   started=NOW - 900)])
    assert hosted is True
    assert "no pipeline" in why, why
    assert clock.slept >= woodpecker_fleet.FALLBACK_SECONDS


@pytest.mark.unit
@pytest.mark.parametrize("status", ["killed", "error", "declined", "skipped", "failure"])
def test_watch_finished_without_starting_falls_back_at_once(status):
    """Cancelled while pending, a config error: it will never run."""
    hosted, why, clock = _run_watch(lambda t: [_pl(status)])
    assert hosted is True
    assert status in why, why
    assert clock.slept == 0


@pytest.mark.unit
def test_watch_rides_out_api_errors_until_the_deadline():
    def pls(t):
        if t < NOW + 60:
            return OSError("connection reset")
        return [_pl("running", started=NOW + 30)]
    hosted, why, _ = _run_watch(pls)
    assert hosted is False, why


@pytest.mark.unit
def test_watch_api_down_throughout_falls_back_with_the_last_error():
    hosted, why, clock = _run_watch(lambda t: OSError("connection refused"))
    assert hosted is True
    assert "connection refused" in why, why
    assert clock.slept >= woodpecker_fleet.FALLBACK_SECONDS


class _FakeWoodpecker:
    """A real HTTP server answering the two calls watch() makes."""

    def __init__(self, pipelines):
        import http.server
        import threading
        body = json.dumps(pipelines).encode()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/repos/lookup/ritz-lang/rz":
                    out = json.dumps({"id": 3}).encode()
                elif self.path.startswith("/api/repos/3/pipelines"):
                    out = body
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.mark.integration
@pytest.mark.parametrize("status,hosted", [("running", "false"), ("killed", "true")])
def test_watch_cli_writes_hosted_and_why_for_github_output(status, hosted):
    srv = _FakeWoodpecker([_pl(status, created=time.time(),
                               started=time.time() if status == "running" else 0)])
    try:
        r = subprocess.run([sys.executable, str(FLEET_SCRIPT), "--watch", SHA,
                            srv.url, "ritz-lang/rz"],
                           capture_output=True, text=True, timeout=60, check=False)
    finally:
        srv.close()
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert lines[0] == f"hosted={hosted}", r.stdout
    assert lines[1].startswith("why=") and len(lines) == 2, r.stdout
    if hosted == "true":
        assert status in lines[1]
        assert "::notice" in r.stderr or "::warning" in r.stderr, r.stderr


@pytest.mark.integration
def test_watch_cli_usage():
    r = subprocess.run([sys.executable, str(FLEET_SCRIPT), "--watch", "abc",
                        "http://x", "ritz-lang/rz"],
                       capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 2


# --- the guard: a pipeline that started too late leaves it to GitHub --------


def _guard_env(created: int | None, started: int | None) -> dict:
    env = {}
    if created is not None:
        env["CI_PIPELINE_CREATED"] = str(created)
    if started is not None:
        env["CI_PIPELINE_STARTED"] = str(started)
    return env


def _step_env(tmp_path, extra, *args):
    old = dict(os.environ)
    os.environ.update(extra)
    try:
        return _step(tmp_path, *args, summary={"ok": True, "test": {"passed": 1}})
    finally:
        os.environ.clear()
        os.environ.update(old)


@pytest.mark.unit
def test_guard_limit_is_the_watch_constant_plus_slack():
    """The watch falls back at FALLBACK_SECONDS after creation; the step
    skips only past that plus slack, so an edge case runs twice, never
    zero times."""
    m = re.search(r"^FALLBACK_SECONDS=(\d+)$", STEP_SCRIPT.read_text(), re.MULTILINE)
    assert m and int(m[1]) == woodpecker_fleet.FALLBACK_SECONDS
    s = re.search(r"^SLACK_SECONDS=(\d+)$", STEP_SCRIPT.read_text(), re.MULTILINE)
    assert s and int(s[1]) >= 4 * woodpecker_fleet.POLL_SECONDS


@pytest.mark.integration
def test_guard_skips_a_stale_pipeline_without_running_the_entrypoint(tmp_path):
    r, calls, _ = _step_env(tmp_path, _guard_env(NOW, NOW + 3600), "projects/sage")
    assert r.returncode == 0, r.stderr
    assert calls == []
    assert "GitHub" in r.stdout and "60 min" in r.stdout, r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("env", [
    _guard_env(NOW, NOW + 60),            # prompt start
    _guard_env(NOW, NOW + 600 + 200),     # past the watch, inside the slack
    _guard_env(None, None),               # a manual run on an older server
    _guard_env(NOW, 0),
    _guard_env("x", "y"),
])
def test_guard_runs_a_fresh_or_unknown_pipeline(tmp_path, env):
    r, calls, _ = _step_env(tmp_path, env, "projects/sage")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(calls) == 1
