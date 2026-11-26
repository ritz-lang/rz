"""main.yml pushes main to git.fucken.ninja (AGAST #4846).

Aaron, 2026-11-26: GitHub stays canonical. On every push to main, main.yml's
gitea-push job pushes the commit to `ritz-lang/rz` on git.fucken.ninja with a
Gitea token stored as the GitHub secret GITEA_PUSH_TOKEN; that push's webhook
starts `.woodpecker/builder.yml`. Not a pull mirror, and not train.sh.

What these tests pin:

* the job: only on a push to main, a full-history checkout with no GitHub
  credential left in it, the token only as the step's env, runs queued in
  order (a later push never races an earlier one);
* routing: builder-fleet says hosted unless the push happened, so a failed or
  skipped push still runs the matrix on GitHub;
* the script (`push_to_gitea.sh`) against a real bare repo and a fake git:
  the token never reaches argv, no token means a skip and not a red run, a
  rejected push fails.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parents[2]
MAIN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"
PUSH_SCRIPT = REPO_ROOT / ".github" / "scripts" / "push_to_gitea.sh"
GITEA_URL = "https://git.fucken.ninja/ritz-lang/rz.git"
TOKEN = "s3cr3t-gitea-token-4846"
ON_MAIN_PUSH = "github.event_name == 'push' && github.ref == 'refs/heads/main'"


def _jobs() -> dict:
    return yaml.safe_load(MAIN_WORKFLOW.read_text())["jobs"]


# --- the job ----------------------------------------------------------------

@pytest.mark.unit
def test_gitea_push_runs_only_for_a_push_to_main_in_order():
    job = _jobs()["gitea-push"]
    assert job["if"] == ON_MAIN_PUSH
    assert job["timeout-minutes"] <= 10
    # Queued, never cancelled mid-push: runs push in the order GitHub queued
    # them, so an older commit never lands on Gitea after a newer one.
    assert job["concurrency"] == {"group": "gitea-push", "cancel-in-progress": False}
    assert job["permissions"] == {"contents": "read"}
    assert job["outputs"] == {"pushed": "${{ steps.push.outputs.pushed }}"}


@pytest.mark.unit
def test_gitea_push_checks_out_full_history_without_githubs_credential():
    """A shallow clone can't push to an empty repo, and the checkout's
    GITHUB_TOKEN extraheader has no business on another forge."""
    checkout, *rest = _jobs()["gitea-push"]["steps"]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    [push] = rest
    assert push["id"] == "push"
    assert push["env"] == {"GITEA_PUSH_TOKEN": "${{ secrets.GITEA_PUSH_TOKEN }}"}
    assert push["run"].strip() == (
        f'bash .github/scripts/push_to_gitea.sh {GITEA_URL} "${{{{ github.sha }}}}" '
        '>> "$GITHUB_OUTPUT"')


@pytest.mark.unit
def test_the_token_is_read_by_one_step_only():
    text = MAIN_WORKFLOW.read_text()
    assert text.count("secrets.GITEA_PUSH_TOKEN") == 1


@pytest.mark.unit
def test_builder_fleet_says_hosted_unless_the_push_happened():
    """A skipped (no secret, a workflow_dispatch run), failed or cancelled
    push starts no Woodpecker run, so GitHub runs the matrix itself."""
    job = _jobs()["builder-fleet"]
    assert job["needs"] == ["gitea-push"]
    assert job["if"] == "${{ !cancelled() }}"
    [probe] = [s for s in job["steps"] if s.get("id") == "probe"]
    assert probe["env"] == {"PUSHED": "${{ needs.gitea-push.outputs.pushed }}"}
    run = probe["run"]
    assert 'if [[ "$PUSHED" != true ]]; then' in run, run
    assert run.index('"$PUSHED" != true') < run.index("woodpecker_fleet.py"), run


# --- the script ---------------------------------------------------------------

def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


@pytest.fixture
def repos(tmp_path: Path):
    """A work clone with two commits, and an empty bare 'Gitea' repo."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    for n in (1, 2):
        (work / "f").write_text(f"{n}\n")
        _git(work, "add", "f")
        _git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", f"c{n}")
    gitea = tmp_path / "gitea.git"
    _git(tmp_path, "init", "-q", "--bare", str(gitea))
    return work, gitea


def _push(cwd: Path, *args: str, token: str | None = TOKEN, path: str | None = None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("GITEA_PUSH_TOKEN", None)
    if token is not None:
        env["GITEA_PUSH_TOKEN"] = token
    if path is not None:
        env["PATH"] = path
    return subprocess.run(["bash", str(PUSH_SCRIPT), *args], check=False, cwd=cwd, env=env,
                          text=True, capture_output=True)


@pytest.mark.integration
def test_push_sends_the_commit_to_main_and_says_pushed(repos):
    work, gitea = repos
    sha = _git(work, "rev-parse", "HEAD")
    r = _push(work, gitea.as_uri(), sha)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "pushed=true\n"
    assert _git(gitea, "rev-parse", "refs/heads/main") == sha


@pytest.mark.integration
def test_push_of_an_older_commit_is_rejected_not_forced(repos):
    """GitHub's main only moves forward (ff-only); Gitea must never move back."""
    work, gitea = repos
    head = _git(work, "rev-parse", "HEAD")
    assert _push(work, gitea.as_uri(), head).returncode == 0
    r = _push(work, gitea.as_uri(), _git(work, "rev-parse", "HEAD~1"))
    assert r.returncode == 1, r.stderr
    assert "pushed=true" not in r.stdout
    assert _git(gitea, "rev-parse", "refs/heads/main") == head


@pytest.mark.integration
def test_no_token_is_a_warning_and_no_push(repos):
    """Until the secret is set the job is green and the matrix runs hosted."""
    work, gitea = repos
    for token in (None, ""):
        r = _push(work, gitea.as_uri(), _git(work, "rev-parse", "HEAD"), token=token)
        assert r.returncode == 0, r.stderr
        assert r.stdout == "pushed=false\n"
        assert "::warning::" in r.stderr and "GITEA_PUSH_TOKEN" in r.stderr
    assert _git(gitea, "for-each-ref") == ""


FAKE_GIT = r"""#!/usr/bin/env bash
printf '%s\n' "$@" > "$ARGV_LOG"
env > "$ENV_LOG"
# Run the credential helper the script configured, as git would.
for ((i = 1; i <= $#; i++)); do
    if [[ "${!i}" == credential.helper=!* ]]; then
        helper=${!i#credential.helper=!}
    fi
done
printf 'protocol=https\nhost=git.fucken.ninja\n\n' | sh -c "$helper \"\$@\"" sh get > "$CRED_LOG"
"""


@pytest.mark.integration
def test_the_token_reaches_git_only_through_the_credential_helper(tmp_path):
    """Never in argv (ps, git's own error messages) or in the URL."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "git").write_text(FAKE_GIT)
    (bindir / "git").chmod(0o755)
    logs = {k: tmp_path / k for k in ("ARGV_LOG", "ENV_LOG", "CRED_LOG")}
    os.environ.update({k: str(v) for k, v in logs.items()})
    try:
        r = _push(tmp_path, GITEA_URL, "a" * 40, path=f"{bindir}:{os.environ['PATH']}")
    finally:
        for k in logs:
            os.environ.pop(k)
    assert r.returncode == 0, r.stderr
    argv = logs["ARGV_LOG"].read_text()
    assert TOKEN not in argv
    assert GITEA_URL in argv.splitlines()
    assert f"{'a' * 40}:refs/heads/main" in argv.splitlines()
    assert "--force" not in argv and "+" + "a" * 40 not in argv
    assert "GIT_TERMINAL_PROMPT=0" in logs["ENV_LOG"].read_text().splitlines()
    cred = logs["CRED_LOG"].read_text().splitlines()
    # Gitea takes a token as the username with this password (basic auth).
    assert f"username={TOKEN}" in cred and "password=x-oauth-basic" in cred
    assert TOKEN not in r.stdout + r.stderr


@pytest.mark.integration
@pytest.mark.parametrize("args", [(), (GITEA_URL,), (GITEA_URL, "abc"),
                                  (GITEA_URL, "a" * 40, "extra"),
                                  ("http://git.fucken.ninja/x.git", "a" * 40)])
def test_push_refuses_bad_arguments(tmp_path, args):
    r = _push(tmp_path, *args)
    assert r.returncode == 2, (args, r.stderr)
    assert "usage" in r.stderr
