#!/usr/bin/env python3
"""The builder image's workflow and its publish script (AGAST #4824).

.github/workflows/builder.yml is separate from main.yml's compiler CI: the
builder is its own project, so compiler CI neither runs nor waits on a
75-minute image build.  It builds the image from the pushed commit with
projects/builder/test.sh (which runs the in-container checks and fails over
the README's size budget), dry-runs the publish, and then publishes on

* a push of any tag:  :<tag> (sanitised), :ritz1-<sha12>, :<commit>
* a push to main touching the builder:  :main, :<commit>

A workflow_dispatch run builds, tests and dry-runs, and pushes nothing.
.github/scripts/publish_builder.sh works out the tags from the ref and does
the tagging and pushing.

We can't run Actions or push here, so the script tests put a stub `docker`
on PATH that answers `image ls` / `image inspect` from fixed images and
records every call.

Run with:
    python3 -m pytest projects/ritz/tools/test_publish_builder.py -q
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "publish_builder.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "builder.yml"
MAIN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"
BUILDER = REPO_ROOT / "projects" / "builder"

COMMIT = "0123456789abcdef0123456789abcdef01234567"
SHA = "89ab" * 16
IMAGE = "ghcr.io/ritz-lang/rz-builder"
MAIN = "refs/heads/main"
PUBLISH_IF = ("github.event_name == 'push' && (github.ref == 'refs/heads/main'"
              " || startsWith(github.ref, 'refs/tags/'))")

# docker stub.  $STUB_DIR/images has one line per local image,
# "<repo:tag> <commit label> <ritz1 sha256 label>".  Every call is appended
# to $STUB_DIR/calls.  `image ls --filter label=dev.ritz.rz.commit=<c>
# --filter reference=<r> --format ...` prints the matching repo:tags;
# `image inspect <ref> --format ...` prints the requested label.
DOCKER_STUB = r"""#!/usr/bin/env bash
set -u
d="$STUB_DIR"
echo "$*" >> "$d/calls"
case "$1 $2" in
"image ls")
    commit="" ref=""
    shift 2
    while [[ $# -gt 0 ]]; do
        case "$1" in
        --filter) case "$2" in
            label=dev.ritz.rz.commit=*) commit="${2#label=dev.ritz.rz.commit=}" ;;
            reference=*) ref="${2#reference=}" ;;
            esac; shift 2 ;;
        *) shift ;;
        esac
    done
    while read -r tag c s; do
        [[ "$c" == "$commit" && "${tag%%:*}" == "${ref%%:*}" ]] && echo "$tag"
    done < "$d/images"
    exit 0 ;;
"image inspect")
    want="$3"
    while read -r tag c s; do
        if [[ "$tag" == "$want" ]]; then
            case "$*" in
            *ritz1-selfhosted.sha256*) echo "$s" ;;
            *rz.commit*) echo "$c" ;;
            *) echo "{}" ;;
            esac
            exit 0
        fi
    done < "$d/images"
    echo "Error: No such image: $want" >&2; exit 1 ;;
esac
case "$1" in
tag|push) exit 0 ;;
esac
echo "docker stub: unexpected $*" >&2
exit 3
"""


def _run(tmp_path: Path, images: list[str], *args: str, env: dict | None = None):
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "docker").write_text(DOCKER_STUB)
    (stub / "docker").chmod(0o755)
    (tmp_path / "images").write_text("".join(f"{i}\n" for i in images))
    (tmp_path / "calls").write_text("")
    e = {k: v for k, v in os.environ.items()
         if not k.startswith("GITHUB_")}
    e.update(PATH=f"{stub}:{os.environ['PATH']}", STUB_DIR=str(tmp_path))
    e.update(env or {})
    r = subprocess.run(["bash", str(SCRIPT), *args], env=e,
                       capture_output=True, text=True, timeout=30)
    calls = (tmp_path / "calls").read_text().splitlines()
    return r, calls


def _writes(calls: list[str]) -> list[str]:
    return [c for c in calls if c.split()[0] in ("tag", "push", "login")]


def _actions(ref: str, event: str = "push") -> dict:
    return {"GITHUB_ACTIONS": "true", "GITHUB_REF": ref, "GITHUB_EVENT_NAME": event}


LOCAL = f"rz-builder:{COMMIT[:12]}-{SHA[:12]} {COMMIT} {SHA}"
SRC = LOCAL.split()[0]
MAIN_TAGS = [f"{IMAGE}:main", f"{IMAGE}:{COMMIT}"]
V1_TAGS = [f"{IMAGE}:v1.2.0", f"{IMAGE}:ritz1-{SHA[:12]}", f"{IMAGE}:{COMMIT}"]


# --- which tags each ref publishes ---------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("ref,want", [
    (MAIN, MAIN_TAGS),
    ("refs/tags/v1.2.0", V1_TAGS),
], ids=["main", "tag"])
def test_dry_run_names_the_ref_s_tags_and_pushes_nothing(tmp_path, ref, want):
    r, calls = _run(tmp_path, [LOCAL], "--dry-run", COMMIT, IMAGE, ref)
    assert r.returncode == 0, r.stdout + r.stderr
    assert re.findall(r"^would push (\S+)", r.stdout, re.M) == want, r.stdout
    assert _writes(calls) == [], calls


@pytest.mark.integration
@pytest.mark.parametrize("ref,want", [
    (MAIN, MAIN_TAGS),
    ("refs/tags/v1.2.0", V1_TAGS),
], ids=["main", "tag"])
def test_publish_tags_and_pushes_the_ref_s_tags(tmp_path, ref, want):
    r, calls = _run(tmp_path, [LOCAL], COMMIT, IMAGE, ref, env=_actions(ref))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _writes(calls) == ([f"tag {SRC} {t}" for t in want]
                              + [f"push {t}" for t in want]), calls


@pytest.mark.integration
def test_a_branch_dry_run_names_only_the_commit_tag(tmp_path):
    """workflow_dispatch on a branch: the image and its labels are checked,
    and the only tag shown is the commit one, since a branch publishes
    nothing."""
    r, calls = _run(tmp_path, [LOCAL], "--dry-run", COMMIT, IMAGE,
                    "refs/heads/ritz-task-4824")
    assert r.returncode == 0, r.stdout + r.stderr
    assert re.findall(r"^would push (\S+)", r.stdout, re.M) == [f"{IMAGE}:{COMMIT}"]
    assert "publishes nothing" in r.stdout, r.stdout
    assert _writes(calls) == [], calls


@pytest.mark.integration
def test_commit_only_pushes_just_the_commit_tag_for_main(tmp_path):
    """AGAST #4846: main.yml's builder-image job publishes the image of every
    main commit for huburght's Woodpecker, whose steps run
    <image>:<commit>. :main stays builder.yml's."""
    r, calls = _run(tmp_path, [LOCAL], "--commit-only", COMMIT, IMAGE, MAIN,
                    env=_actions(MAIN))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _writes(calls) == [f"tag {SRC} {IMAGE}:{COMMIT}", f"push {IMAGE}:{COMMIT}"], calls


@pytest.mark.integration
@pytest.mark.parametrize("ref", ["refs/tags/v1.2.0", "refs/heads/ritz-task-4846"],
                         ids=["tag", "branch"])
def test_commit_only_publishes_for_main_alone(tmp_path, ref):
    r, calls = _run(tmp_path, [LOCAL], "--commit-only", COMMIT, IMAGE, ref, env=_actions(ref))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "--commit-only publishes a push to main only" in r.stderr, r.stderr
    assert _writes(calls) == [], calls


@pytest.mark.integration
def test_commit_only_dry_run_names_only_the_commit_tag(tmp_path):
    r, calls = _run(tmp_path, [LOCAL], "--dry-run", "--commit-only", COMMIT, IMAGE, MAIN)
    assert r.returncode == 0, r.stdout + r.stderr
    assert re.findall(r"^would push (\S+)", r.stdout, re.M) == [f"{IMAGE}:{COMMIT}"]
    assert _writes(calls) == [], calls


# --- --src-key (AGAST #4903) -----------------------------------------------

@pytest.mark.integration
def test_src_key_adds_a_src_tag_for_commit_only(tmp_path):
    """main.yml's builder-image job passes --src-key so the NEXT commit with
    the same content key can retag this push's image instead of rebuilding."""
    r, calls = _run(tmp_path, [LOCAL], "--commit-only", "--src-key", "deadbeef1234",
                    COMMIT, IMAGE, MAIN, env=_actions(MAIN))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _writes(calls) == [
        f"tag {SRC} {IMAGE}:{COMMIT}", f"tag {SRC} {IMAGE}:src-deadbeef1234",
        f"push {IMAGE}:{COMMIT}", f"push {IMAGE}:src-deadbeef1234",
    ], calls


@pytest.mark.integration
def test_src_key_also_tags_on_a_main_publish(tmp_path):
    r, calls = _run(tmp_path, [LOCAL], "--src-key", "deadbeef1234", COMMIT, IMAGE, MAIN,
                    env=_actions(MAIN))
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"push {IMAGE}:src-deadbeef1234" in calls, calls


@pytest.mark.integration
@pytest.mark.parametrize("key", ["", "DEADBEEF", "not-hex", "x" * 65])
def test_src_key_rejects_a_bad_key(tmp_path, key):
    r, calls = _run(tmp_path, [LOCAL], "--dry-run", "--src-key", key, COMMIT, IMAGE, MAIN)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--src-key" in r.stderr, r.stderr
    assert calls == [], calls  # nothing ran before the argument check


# --- git tag name -> Docker tag --------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("git_tag,docker_tag", [
    ("v1.2.0", "v1.2.0"),                    # already valid: unchanged
    ("builder/v1", "builder-v1"),            # '/' is not allowed in a tag
    ("v1+build.5", "v1-build.5"),            # nor '+'
    ("release/ü", "release---"),             # nor non-ASCII: one '-' a byte
    (".hidden", "_hidden"),                  # a tag can't start with '.'
    ("-x", "_x"),                            # or '-'
    ("a" * 200, "a" * 128),                  # 128 characters at most
], ids=["valid", "slash", "plus", "utf8", "leading-dot", "leading-dash", "long"])
def test_a_git_tag_is_sanitised_to_a_valid_docker_tag(tmp_path, git_tag, docker_tag):
    r, _ = _run(tmp_path, [LOCAL], "--dry-run", COMMIT, IMAGE, f"refs/tags/{git_tag}")
    assert r.returncode == 0, r.stdout + r.stderr
    pushed = re.findall(r"^would push (\S+)", r.stdout, re.M)
    assert pushed[0] == f"{IMAGE}:{docker_tag}", pushed
    assert re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", docker_tag)


@pytest.mark.integration
@pytest.mark.parametrize("git_tag", [
    "main",                    # would move :main off main's commit
    f"ritz1-{SHA[:12]}",       # would claim to be a compiler build
    "ritz1-anything",          # the whole ritz1- prefix is the workflow's
    COMMIT,                    # would claim to be a commit's image
], ids=["main", "ritz1", "ritz1-prefix", "commit"])
def test_a_git_tag_that_would_overwrite_a_managed_tag_is_refused(tmp_path, git_tag):
    """:main, :ritz1-<sha12> and :<commit> belong to the workflow; a git tag
    sanitised onto one of them is refused rather than overwriting it."""
    r, calls = _run(tmp_path, [LOCAL], "--dry-run", COMMIT, IMAGE, f"refs/tags/{git_tag}")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "reserved" in r.stderr, r.stderr
    assert _writes(calls) == [], calls


# --- refusals --------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("images,why", [
    ([], "no rz-builder image"),
    ([LOCAL, f"rz-builder:other {COMMIT} {SHA}"], "2 rz-builder images"),
    ([f"rz-builder:x {COMMIT} not-a-sha"], "ritz1_selfhosted sha256"),
], ids=["none", "two", "bad-label"])
def test_publish_refuses_without_exactly_one_labelled_image(tmp_path, images, why):
    r, calls = _run(tmp_path, images, COMMIT, IMAGE, MAIN)
    assert r.returncode == 1, r.stdout + r.stderr
    assert why in r.stderr, r.stderr
    assert _writes(calls) == [], calls


@pytest.mark.integration
@pytest.mark.parametrize("args,why", [
    (["0123", IMAGE, MAIN], "full 40-hex commit"),
    ([COMMIT, f"{IMAGE}:latest", MAIN], "without a tag"),
    ([COMMIT, IMAGE], "usage"),
    ([COMMIT, IMAGE, "main"], "not a branch or tag ref"),
    ([COMMIT, IMAGE, "refs/pull/1/merge"], "not a branch or tag ref"),
    ([COMMIT, IMAGE, "refs/tags/"], "empty tag"),
], ids=["short-commit", "tagged-image", "no-ref", "bare-name", "pull-ref", "empty-tag"])
def test_publish_refuses_bad_arguments(tmp_path, args, why):
    r, calls = _run(tmp_path, [LOCAL], *args)
    assert r.returncode == 2, r.stdout + r.stderr
    assert why in r.stderr, r.stderr
    assert _writes(calls) == [], calls


@pytest.mark.integration
def test_a_branch_never_publishes(tmp_path):
    r, calls = _run(tmp_path, [LOCAL], COMMIT, IMAGE, "refs/heads/ritz-task-4824")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "only a push to main or a tag publishes" in r.stderr, r.stderr
    assert _writes(calls) == [], calls


@pytest.mark.integration
@pytest.mark.parametrize("ref,env", [
    (MAIN, _actions(MAIN, event="workflow_dispatch")),
    ("refs/tags/v1.2.0", _actions("refs/tags/v1.2.0", event="workflow_dispatch")),
    (MAIN, _actions("refs/tags/v1.2.0")),   # the ref argument isn't the run's
], ids=["dispatch-main", "dispatch-tag", "ref-mismatch"])
def test_in_actions_only_a_push_of_that_ref_publishes(tmp_path, ref, env):
    """Belt and braces under the job's `if:`: in Actions, the script pushes
    only for a push event whose GITHUB_REF is the ref it was given."""
    r, calls = _run(tmp_path, [LOCAL], COMMIT, IMAGE, ref, env=env)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "only a push" in r.stderr, r.stderr
    assert _writes(calls) == [], calls
    r, _ = _run(tmp_path, [LOCAL], "--dry-run", COMMIT, IMAGE, ref, env=env)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.integration
def test_publish_writes_the_tags_to_the_step_summary(tmp_path):
    summary = tmp_path / "summary.md"
    r, _ = _run(tmp_path, [LOCAL], "--dry-run", COMMIT, IMAGE, "refs/tags/v1.2.0",
                env={"GITHUB_STEP_SUMMARY": str(summary)})
    assert r.returncode == 0, r.stdout + r.stderr
    text = summary.read_text()
    for t in V1_TAGS:
        assert t in text, text


# --- .github/workflows/builder.yml -----------------------------------------

def _spec():
    return yaml.safe_load(WORKFLOW.read_text())


def _on():
    spec = _spec()
    return spec.get("on", spec.get(True))   # YAML 1.1 reads `on:` as True


def _job():
    return _spec()["jobs"]["builder"]


def _steps():
    return _job()["steps"]


def _step(pattern: str):
    hits = [s for s in _steps() if re.search(pattern, s.get("run") or "")]
    assert len(hits) == 1, (pattern, [s.get("name") for s in hits])
    return hits[0]


def _main_jobs():
    return yaml.safe_load(MAIN_WORKFLOW.read_text())["jobs"]


@pytest.mark.unit
def test_main_yml_builds_the_image_once_and_publishes_only_its_commit_tag():
    """Since AGAST #4847 main.yml's builder-image job builds the image of the
    commit under test (test.sh, ~4 min); since #4846 it also pushes that
    image as :<commit> for a push to main, for huburght's Woodpecker, whose
    steps run it. Nothing else in main.yml builds it, holds a registry
    right or pushes; :main and the tag tags stay builder.yml's."""
    jobs = _main_jobs()
    assert "builder" not in jobs
    builds = [name for name, job in jobs.items()
              if any("projects/builder/test.sh" in str(st.get("run", ""))
                     for st in job.get("steps") or [])]
    assert builds == ["builder-image"], builds
    for name, job in jobs.items():
        if name != "builder-image":
            assert "packages" not in (job.get("permissions") or {}), name
            assert "docker login" not in str(job) and "publish_builder" not in str(job), name
    image = jobs["builder-image"]
    assert image["permissions"] == {"contents": "read", "packages": "write"}
    publish = [s for s in image["steps"] if "publish_builder.sh" in str(s.get("run", ""))]
    assert len(publish) == 1, publish
    assert re.search(r'publish_builder\.sh --commit-only --src-key '
                     r'"\$\{\{ steps\.key\.outputs\.key \}\}" "\$\{\{ github\.sha \}\}" '
                     r'ghcr\.io/ritz-lang/rz-builder refs/heads/main', publish[0]["run"]), publish


@pytest.mark.unit
def test_main_yml_registry_steps_run_on_a_push_to_main_only():
    steps = _main_jobs()["builder-image"]["steps"]
    touching = [s for s in steps
                if re.search(r"docker (login|logout|push)|publish_builder", s.get("run") or "")]
    assert len(touching) == 3, [s.get("name") for s in touching]
    for s in touching:
        assert "github.event_name == 'push' && github.ref == 'refs/heads/main'" in s["if"], s
        assert "runner.temp" in str((s.get("env") or {}).get("DOCKER_CONFIG")), s
    login, _, logout = touching
    assert "--password-stdin" in login["run"] and "secrets." not in login["run"], login
    assert "secrets.GITHUB_TOKEN" in str(login["env"]), login
    assert "always()" in logout["if"] and 'rm -rf "$DOCKER_CONFIG"' in logout["run"], logout
    # The publish finds its image by label among rz-builder:* images; it runs
    # before the hosted path re-tags the image as rz-builder:ci.
    names = [s.get("name") for s in steps]
    retag = next(i for i, s in enumerate(steps) if "rz-builder:ci" in str(s.get("run", "")))
    assert names.index(touching[1].get("name")) < retag, names


@pytest.mark.unit
def test_builder_workflow_runs_on_tags_builder_changes_on_main_and_dispatch():
    on = _on()
    assert sorted(on) == ["push", "workflow_dispatch"], on
    push = on["push"]
    assert push["tags"] == ["**"], push            # every tag, '/' included
    assert push["branches"] == ["main"], push
    # GitHub ignores `paths` for a tag push, so the filter limits main only.
    assert sorted(push["paths"]) == sorted([
        "projects/builder/**", ".github/workflows/builder.yml",
        ".github/scripts/publish_builder.sh"]), push


@pytest.mark.unit
def test_builder_job_builds_and_tests_the_pushed_commit():
    step = _step(r"projects/builder/test\.sh")
    assert "--keep" in step["run"] and "github.sha" in step["run"], step
    assert "if" not in step, step  # every run, dispatch too


@pytest.mark.unit
def test_builder_job_dry_runs_the_publish_on_every_run():
    step = _step(r"publish_builder\.sh --dry-run")
    assert "if" not in step, step
    assert '"$GITHUB_REF"' in step["run"], step


@pytest.mark.unit
def test_no_run_script_expands_the_ref_into_its_text():
    """A tag name is attacker-shaped text ($(...) and backticks are legal in
    a ref), so it reaches a script as "$GITHUB_REF", never as ${{ }}."""
    for s in _steps():
        assert not re.search(r"\$\{\{\s*github\.(ref|head_ref)", s.get("run") or ""), s


@pytest.mark.unit
def test_only_a_push_of_main_or_a_tag_logs_in_and_pushes():
    """Every step that touches the registry runs on a publishing push alone."""
    touching = [s for s in _steps()
                if re.search(r"docker (login|logout|push)|publish_builder\.sh (?!--dry-run)",
                             s.get("run") or "")]
    assert len(touching) == 3, [s.get("name") for s in touching]
    for s in touching:
        assert PUBLISH_IF in str(s.get("if", "")), s
    assert '"$GITHUB_REF"' in _step(r"publish_builder\.sh (?!--dry-run)")["run"]


@pytest.mark.unit
def test_login_reads_the_token_from_stdin_into_a_job_private_docker_config():
    login = _step(r"docker login")
    assert "--password-stdin" in login["run"], login
    assert "secrets.GITHUB_TOKEN" in str(login.get("env", {})), login
    assert "secrets." not in login["run"], "token expanded into the script text"
    logout = _step(r"docker logout")
    assert "always()" in str(logout["if"]), logout
    assert 'rm -rf "$DOCKER_CONFIG"' in logout["run"], logout
    # runner.temp is not in scope for a job-level env, so each step that holds
    # the credential names the private config itself.
    for s in (login, _step(r"publish_builder\.sh (?!--dry-run)"), logout):
        assert "runner.temp" in str((s.get("env") or {}).get("DOCKER_CONFIG")), s


@pytest.mark.unit
def test_only_the_builder_job_may_write_packages():
    spec = _spec()
    assert spec["permissions"] == {"contents": "read"}, spec.get("permissions")
    assert list(spec["jobs"]) == ["builder"]
    assert _job()["permissions"] == {"contents": "read", "packages": "write"}
    # main.yml's one exception, builder-image (AGAST #4846), is pinned by
    # test_main_yml_builds_the_image_once_and_publishes_only_its_commit_tag.
    assert len(re.findall(r"packages:\s*write", MAIN_WORKFLOW.read_text())) == 1


@pytest.mark.unit
def test_publishes_queue_per_event_and_ref():
    """A tag publish and a main publish don't wait on each other; two main
    publishes queue, never cancel the running one, so :main can't move back
    to an older commit.  The event is in the group so a dispatch dry run on
    main can't replace a queued main publish (a group keeps one pending)."""
    c = _job()["concurrency"]
    assert c["cancel-in-progress"] is False, c
    assert "github.ref" in c["group"] and "github.event_name" in c["group"], c
    assert "concurrency" not in _spec(), "a workflow-level group would serialise refs"


@pytest.mark.unit
def test_size_budget_in_test_sh_is_the_readme_budget():
    """test.sh enforces the budget; it must be the one README.md records."""
    readme = (BUILDER / "README.md").read_text()
    m = re.search(r"\*\*Budget: (\d+) MiB unpacked\*\*", readme)
    assert m, "README.md lost its **Budget: N MiB unpacked** line"
    t = re.search(r"^BUDGET_MIB=(\d+)", (BUILDER / "test.sh").read_text(), re.M)
    assert t and t.group(1) == m.group(1), (t and t.group(1), m.group(1))
