#!/usr/bin/env python3
"""Self-tests for .claude/room-account.sh: which Claude account a room runs on
(AGAST #4699).

host.env's RZ_ROOM_ACCOUNTS lists a host's accounts; room <id> gets account
<id> % N.  The helper must (1) pick by parity, (2) beat adele.env's
CLAUDE_CODE_OAUTH_TOKEN, which overrides any config dir's stored login,
(3) refuse an account `claude auth status` reports logged out, and (4) make
provision-room.sh --room write trust into the chosen account's .claude.json.

`claude` and `systemctl` are fakes; HOME, host.env, the unit dir and the
config dirs are all under tmp_path.  The systemd precedence the drop-in
relies on (EnvironmentFile= in a drop-in beats adele.env and room.env;
UnsetEnvironment= removes a variable) was measured with a scratch unit and
is recorded in the script's header.

Run with:
    python3 -m pytest projects/ritz/tools/test_room_account.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # every test starts a process (AGAST #4092)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ACCOUNT = REPO / ".claude" / "room-account.sh"
PROVISION = REPO / ".claude" / "provision-room.sh"

# A fake `claude auth status --json`: logged in with any env token (as the
# real CLI reports, measured), else when the config dir it would read holds a
# LOGGED_IN marker.  It logs the auth env it saw, one line per call.
FAKE_CLAUDE = """#!/bin/sh
echo "token=${CLAUDE_CODE_OAUTH_TOKEN-<unset>} dir=${CLAUDE_CONFIG_DIR-<unset>}" >> "$FAKE_LOG"
if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    echo '{"loggedIn": true, "authMethod": "oauth_token"}'; exit 0
fi
d="${CLAUDE_CONFIG_DIR-$HOME/.claude}"
if [ -e "$d/LOGGED_IN" ]; then
    echo "{\\"loggedIn\\": true, \\"authMethod\\": \\"claude.ai\\", \\"email\\": \\"$(cat "$d/LOGGED_IN")\\"}"
else
    echo '{"loggedIn": false, "authMethod": "none"}'
fi
"""


def _exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture()
def h(tmp_path: Path) -> dict:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "LOGGED_IN").write_text("default@x")
    (home / ".claude.json").write_text(json.dumps({"projects": {}}))
    acct = tmp_path / "acct-a"
    acct.mkdir()
    (acct / "LOGGED_IN").write_text("a@x")
    (acct / ".claude.json").write_text(json.dumps({"keep": 1, "projects": {}}))
    out = tmp_path / "acct-out"
    out.mkdir()  # a config dir whose stored login is gone
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    _exe(bin_ / "claude", FAKE_CLAUDE)
    _exe(bin_ / "systemctl", f'#!/bin/sh\necho "$*" >> {tmp_path}/systemctl.log\n')
    env = {
        "HOME": str(home),
        "PATH": f"{bin_}:{os.environ['PATH']}",
        "RZ_HOST_ENV": str(tmp_path / "host.env"),
        "RZ_SYSTEMD_USER_DIR": str(tmp_path / "units"),
        "RZ_ROOM_ACCOUNT_DIR": str(tmp_path / "room-accounts"),
        "RZ_CLAUDE_BIN": str(bin_ / "claude"),
        "FAKE_LOG": str(tmp_path / "claude.log"),
        # What adele.env hands every room unit on most hosts.
        "CLAUDE_CODE_OAUTH_TOKEN": "adele-env-token",
    }
    return {"tmp": tmp_path, "home": home, "acct": acct, "out": out, "env": env}


def _host_env(h: dict, line: str) -> None:
    Path(h["env"]["RZ_HOST_ENV"]).write_text(line + "\n")


def _run(h: dict, *args: str, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(ACCOUNT), *args],
        env={**h["env"], **env},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _dropin(h: dict, room: str) -> Path:
    return (
        h["tmp"] / "units" / f"adele-agent@{room}.service.d" / "55-rz-room-account.conf"
    )


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("room", "want"),
    [("ritz-task-4698", "acct"), ("ritz-task-4699", "default"), ("4701", "default")],
)
def test_ticket_parity_picks_the_account(h, room, want):
    """Two accounts: even ids get the first, odd ids the second."""
    _host_env(h, f'RZ_ROOM_ACCOUNTS="{h["acct"]} default"')
    r = _run(h, "--config-dir", room)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == (str(h["acct"]) if want == "acct" else "default")


def test_one_account_serves_every_room(h):
    _host_env(h, f"RZ_ROOM_ACCOUNTS={h['acct']}")
    for room in ("ritz-task-10", "ritz-task-11"):
        assert _run(h, "--config-dir", room).stdout.strip() == str(h["acct"])


def test_no_key_leaves_the_units_environment_alone(h):
    """No RZ_ROOM_ACCOUNTS (or no host.env): today's behaviour, no drop-in."""
    assert _run(h, "--config-dir", "ritz-task-7").stdout.strip() == "inherit"
    r = _run(h, "ritz-task-7")
    assert r.returncode == 0 and r.stdout == ""
    r = _run(h, "--install", "ritz-task-7")
    assert r.returncode == 0, r.stderr
    assert not _dropin(h, "ritz-task-7").exists()
    assert not (h["tmp"] / "claude.log").exists()  # nothing to check


def test_bad_accounts_value_is_refused(h):
    _host_env(h, "RZ_ROOM_ACCOUNTS=relative/dir default")
    r = _run(h, "--config-dir", "ritz-task-8")
    assert r.returncode == 2
    assert "RZ_ROOM_ACCOUNTS must be" in r.stderr


# --------------------------------------------------------------------------
# Beating adele.env's token
# --------------------------------------------------------------------------


def test_config_dir_account_drops_the_env_token(h):
    """The login check runs without adele.env's token, and the drop-in unsets
    it, so the room authenticates with the dir's stored login."""
    _host_env(h, f"RZ_ROOM_ACCOUNTS={h['acct']}")
    r = _run(h, "--install", "ritz-task-12")
    assert r.returncode == 0, r.stderr
    assert "logged in as a@x (claude.ai)" in r.stdout
    assert (h["tmp"] / "claude.log").read_text().split("\n")[0] == (
        f"token=<unset> dir={h['acct']}"
    )
    body = _dropin(h, "ritz-task-12").read_text()
    env_file = h["tmp"] / "room-accounts" / "ritz-task-12.env"
    assert f"EnvironmentFile={env_file}\n" in body
    assert body.rstrip().endswith("UnsetEnvironment=CLAUDE_CODE_OAUTH_TOKEN")
    assert env_file.read_text() == f"CLAUDE_CONFIG_DIR={h['acct']}\n"
    assert "--user daemon-reload" in (h["tmp"] / "systemctl.log").read_text()
    assert _run(h, "--verify", "ritz-task-12").returncode == 0


def test_default_account_unsets_both_variables(h):
    """An empty CLAUDE_CONFIG_DIR= is NOT ~/.claude (the CLI reports
    configDirectory '' and logged out), so `default` must unset it."""
    _host_env(h, "RZ_ROOM_ACCOUNTS=default")
    r = _run(h, "--install", "ritz-task-13", CLAUDE_CONFIG_DIR=str(h["out"]))
    assert r.returncode == 0, r.stderr
    assert "token=<unset> dir=<unset>" in (h["tmp"] / "claude.log").read_text()
    body = _dropin(h, "ritz-task-13").read_text()
    assert "EnvironmentFile" not in body
    assert "UnsetEnvironment=CLAUDE_CODE_OAUTH_TOKEN CLAUDE_CONFIG_DIR" in body


def test_env_file_account_supplies_its_own_token(h):
    """A setup-token account: the drop-in reads the host-local file itself
    (the token is never copied), and unsets the config dir it lacks."""
    tok = h["tmp"] / "b.env"
    tok.write_text("CLAUDE_CODE_OAUTH_TOKEN=sk-b\n")
    tok.chmod(0o600)
    _host_env(h, f'RZ_ROOM_ACCOUNTS="default {tok}"')
    r = _run(h, "ritz-task-15")
    assert r.stdout.split() == ["CLAUDE_CODE_OAUTH_TOKEN=sk-b", "-CLAUDE_CONFIG_DIR"]
    r = _run(h, "--install", "ritz-task-15")
    assert r.returncode == 0, r.stderr
    assert "sk-b" not in r.stdout  # never echo a token
    assert "token=sk-b dir=<unset>" in (h["tmp"] / "claude.log").read_text()
    body = _dropin(h, "ritz-task-15").read_text()
    assert f"EnvironmentFile={tok}\n" in body
    assert "UnsetEnvironment=CLAUDE_CONFIG_DIR" in body
    assert "sk-b" not in body


def test_env_file_readable_by_others_is_refused(h):
    tok = h["tmp"] / "b.env"
    tok.write_text("CLAUDE_CODE_OAUTH_TOKEN=sk-b\n")
    tok.chmod(0o644)
    _host_env(h, f"RZ_ROOM_ACCOUNTS={tok}")
    r = _run(h, "ritz-task-16")
    assert r.returncode == 2
    assert "chmod 600" in r.stderr and "sk-b" not in r.stderr


# --------------------------------------------------------------------------
# Logged out
# --------------------------------------------------------------------------


def test_logged_out_account_is_refused_before_anything_is_written(h):
    """A dir with no stored login (a .credentials.json can exist with empty
    tokens, so the CLI is asked) refuses with one line, and writes nothing."""
    (h["out"] / ".credentials.json").write_text('{"claudeAiOauth": {}}')
    _host_env(h, f"RZ_ROOM_ACCOUNTS={h['out']} default")
    r = _run(h, "--install", "ritz-task-20")
    assert r.returncode == 1
    assert r.stderr.count("\n") == 1 and "not logged in" in r.stderr
    assert not _dropin(h, "ritz-task-20").exists()
    # The odd room's account is fine.
    assert _run(h, "--describe", "ritz-task-21").returncode == 0


# --------------------------------------------------------------------------
# provision-room.sh --room
# --------------------------------------------------------------------------


@pytest.fixture()
def wt(h) -> Path:
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    main = h["tmp"] / "main"
    w = h["tmp"] / "main-task-30"
    subprocess.run([*git, "init", "-q", str(main)], check=True)
    subprocess.run(
        [*git, "-C", str(main), "commit", "-q", "--allow-empty", "-m", "x"], check=True
    )
    subprocess.run([*git, "-C", str(main), "worktree", "add", "-q", str(w)], check=True)
    return w.resolve()


def _provision(h: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PROVISION), *args],
        env={**h["env"], "RZ_PROVISION_HOST_CHECKS": "0"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _trusted(cj: Path) -> set[str]:
    return {
        k
        for k, v in json.loads(cj.read_text())["projects"].items()
        if v.get("hasTrustDialogAccepted")
    }


def test_provision_trusts_in_the_chosen_accounts_config(h, wt):
    """Trust lands in <dir>/.claude.json, the file the room's CLI reads, not
    in the caller's ~/.claude.json; --verify reads the same file, and
    --remove drops the worktree key there and the drop-in."""
    _host_env(h, f"RZ_ROOM_ACCOUNTS={h['acct']} default")
    room = "ritz-task-30"
    r = _provision(h, "--room", room, str(wt))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "room permissions OK" in r.stdout
    acct_cj = h["acct"] / ".claude.json"
    assert str(wt) in _trusted(acct_cj)
    assert json.loads(acct_cj.read_text())["keep"] == 1
    assert _trusted(h["home"] / ".claude.json") == set()
    # A host.env edited after the spawn can't redirect the teardown.
    _host_env(h, "RZ_ROOM_ACCOUNTS=default")
    r = _provision(h, "--remove", "--room", room, str(wt))
    assert r.returncode == 0, r.stderr
    assert str(wt) not in _trusted(acct_cj)
    assert not _dropin(h, room).exists()


def test_provision_refuses_a_logged_out_account(h, wt):
    _host_env(h, f"RZ_ROOM_ACCOUNTS={h['out']}")
    r = _provision(h, "--room", "ritz-task-30", str(wt))
    assert r.returncode == 1
    assert "not logged in" in r.stderr
    assert not (wt / ".claude" / "settings.json").exists()


def test_provision_verify_fails_without_the_dropin(h, wt):
    _host_env(h, "RZ_ROOM_ACCOUNTS=default")
    assert _provision(h, "--room", "ritz-task-30", str(wt)).returncode == 0
    _dropin(h, "ritz-task-30").unlink()
    r = _provision(h, "--verify", "--room", "ritz-task-30", str(wt))
    assert r.returncode == 1
    assert "drop-in is missing or stale" in r.stderr


# --------------------------------------------------------------------------
# No account names in the repo
# --------------------------------------------------------------------------


@pytest.mark.unit
def test_repo_names_no_account_dirs():
    """Aaron, 2026-11-25: account dirs are per-host config (host.env), never
    named in the repo.  The pattern is assembled so this file doesn't match."""
    names = "claude-" + "better" + "comp\\|claude-" + "nev" + "elis"
    r = subprocess.run(
        ["git", "-C", str(REPO), "grep", "-il", names],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.stdout == "", r.stdout
