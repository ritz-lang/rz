#!/usr/bin/env python3
"""Self-tests for .claude/provision-room.sh's trust key (AGAST #2746, from #1378).

When cwd is a git WORKTREE, Claude Code (2.1.316 .. 2.1.322) checks workspace
trust under the MAIN checkout's key in ~/.claude.json, not the worktree's own
path. provision-room.sh used to trust only the worktree, and its --verify
checked that same key, so it passed while the CLI ignored every room's
permissions.allow entries. These tests hold the script to:

  1. --verify with only the worktree key trusted FAILS (it used to pass);
  2. apply trusts BOTH keys, and --verify then passes;
  3. --remove drops only the worktree key and keeps the shared main key;
     with the main key gone, --verify fails again.

Everything runs against a throwaway git repo + worktree, with HOME and
CLAUDE_CONFIG_DIR pointed at a temp dir: the real ~/.claude.json is never read
or written.

Run with:
    python3 -m pytest projects/ritz/tools/test_provision_room.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROVISION = REPO / ".claude" / "provision-room.sh"


@pytest.fixture()
def env(tmp_path: Path):
    """A scratch main checkout, a worktree of it, and a scratch config dir."""
    main = tmp_path / "main"
    wt = tmp_path / "main-task-1"
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    git = [
        "git",
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "-c",
        "init.defaultBranch=main",
    ]
    subprocess.run([*git, "init", "-q", str(main)], check=True)
    subprocess.run(
        [*git, "-C", str(main), "commit", "-q", "--allow-empty", "-m", "x"], check=True
    )
    subprocess.run(
        [*git, "-C", str(main), "worktree", "add", "-q", "-b", "t1", str(wt)],
        check=True,
    )

    e = dict(os.environ)
    # Both: the pre-fix script read Path.home(), the fixed one CLAUDE_CONFIG_DIR.
    # Pointing both at the scratch dir keeps either version off the real file.
    e["HOME"] = str(cfg)
    e["CLAUDE_CONFIG_DIR"] = str(cfg)
    cj = cfg / ".claude.json"
    cj.write_text(json.dumps({"oauthAccount": {"keep": "me"}, "projects": {}}))
    return {
        "main": str(main.resolve()),
        "wt": str(wt.resolve()),
        "cj": cj,
        "env": e,
    }


def _run(env, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(PROVISION), *args],
        env=env["env"],
        capture_output=True,
        text=True,
    )


def _projects(env) -> dict:
    return json.loads(env["cj"].read_text()).get("projects", {})


def _trust(env, *keys: str) -> None:
    d = json.loads(env["cj"].read_text())
    for k in keys:
        d.setdefault("projects", {}).setdefault(k, {})["hasTrustDialogAccepted"] = True
    env["cj"].write_text(json.dumps(d))


def _write_settings(env) -> None:
    s = Path(env["wt"]) / ".claude" / "settings.json"
    s.parent.mkdir(parents=True, exist_ok=True)
    allow = ["Write", "Edit", "NotebookEdit", "Read", "Glob", "Grep", "Bash"]
    s.write_text(json.dumps({"permissions": {"allow": allow}}))


def test_verify_fails_when_only_the_worktree_key_is_trusted(env):
    """Case 1: the false pass. This is the state every room was left in."""
    _trust(env, env["wt"])
    _write_settings(env)
    r = _run(env, "--verify", env["wt"])
    assert r.returncode == 1, r.stdout + r.stderr
    assert env["main"] in r.stderr


def test_apply_trusts_both_keys_and_verify_passes(env):
    """Case 2: apply sets the main-checkout key (what the CLI checks) and the
    worktree key (in case a later CLI keys on cwd again)."""
    r = _run(env, env["wt"])
    assert r.returncode == 0, r.stdout + r.stderr
    p = _projects(env)
    assert p[env["main"]]["hasTrustDialogAccepted"] is True
    assert p[env["wt"]]["hasTrustDialogAccepted"] is True
    # Read-modify-write: the rest of the file (auth, history) survives.
    assert json.loads(env["cj"].read_text())["oauthAccount"] == {"keep": "me"}
    assert _run(env, "--verify", env["wt"]).returncode == 0


def test_remove_keeps_the_shared_main_key(env):
    """Case 3: --remove at reap drops only the worktree's own key. The main
    key is shared by the parent room and every live worktree."""
    assert _run(env, env["wt"]).returncode == 0
    r = _run(env, "--remove", env["wt"])
    assert r.returncode == 0, r.stdout + r.stderr
    p = _projects(env)
    assert env["wt"] not in p
    assert p[env["main"]]["hasTrustDialogAccepted"] is True


def test_verify_fails_again_without_the_main_key(env):
    """Case 3, second half: the main key is the one --verify actually needs."""
    assert _run(env, env["wt"]).returncode == 0
    d = json.loads(env["cj"].read_text())
    del d["projects"][env["main"]]
    env["cj"].write_text(json.dumps(d))
    r = _run(env, "--verify", env["wt"])
    assert r.returncode == 1, r.stdout + r.stderr


def test_config_file_follows_claude_config_dir(env, tmp_path: Path):
    """The CLI reads $CLAUDE_CONFIG_DIR/.claude.json when that is set; trusting
    ~/.claude.json instead would be the same silent miss one level up."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude.json").write_text("{}")
    env["env"]["HOME"] = str(home)
    assert _run(env, env["wt"]).returncode == 0
    assert env["main"] in _projects(env)
    assert json.loads((home / ".claude.json").read_text()) == {}


def test_verify_requires_bare_bash_as_well_as_write(env):
    """--verify checks the bare Bash entry too: without it, rm / git push in a
    trusted room still reach adele's approval callback."""
    assert _run(env, env["wt"]).returncode == 0
    s = Path(env["wt"]) / ".claude" / "settings.json"
    d = json.loads(s.read_text())
    d["permissions"]["allow"].remove("Bash")
    s.write_text(json.dumps(d))
    assert _run(env, "--verify", env["wt"]).returncode == 1
