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

pytestmark = pytest.mark.integration  # every test starts a process (AGAST #4092)

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
    # The host checks (AGAST #3722) have their own tests in
    # test_borque_hooks.py; a CI runner has no qemu or OVMF.
    e["RZ_PROVISION_HOST_CHECKS"] = "0"
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


@pytest.fixture(params=["ritz.git", "ritz"], ids=["bare", "bare-no-git-suffix"])
def bare_env(env, tmp_path: Path, request):
    """A worktree of a BARE mirror, as Borque's hostd makes them (AGAST #4256):
    ~/borque/mirrors/ritz.git -> ~/borque/worktrees/<room>. The CLI keys trust
    on the common git dir, which for a bare repo is the mirror dir itself."""
    mirror = tmp_path / "mirrors" / request.param
    wt = tmp_path / "worktrees" / "room-1"
    subprocess.run(
        ["git", "clone", "-q", "--bare", env["main"], str(mirror)], check=True
    )
    subprocess.run(
        ["git", "-C", str(mirror), "worktree", "add", "-q", "-b", "r1", str(wt)],
        check=True,
    )
    return {**env, "mirror": str(mirror.resolve()), "wt": str(wt.resolve())}


def test_bare_worktree_apply_trusts_the_mirror_dir(bare_env):
    """Not the worktree path alone: the CLI ignores the allow list unless
    projects[<mirror dir>] is trusted."""
    r = _run(bare_env, bare_env["wt"])
    assert r.returncode == 0, r.stdout + r.stderr
    p = _projects(bare_env)
    assert p[bare_env["mirror"]]["hasTrustDialogAccepted"] is True
    assert p[bare_env["wt"]]["hasTrustDialogAccepted"] is True
    v = _run(bare_env, "--verify", bare_env["wt"])
    assert v.returncode == 0, v.stdout + v.stderr
    assert bare_env["mirror"] in v.stdout


def test_bare_worktree_verify_fails_with_only_the_worktree_key(bare_env):
    """The #2746/#1378 false pass, Borque edition: --verify must check the
    mirror key the CLI uses, so trusting only the worktree fails. Apply first
    so the settings file is complete and the missing key is the only gap."""
    assert _run(bare_env, bare_env["wt"]).returncode == 0
    d = json.loads(bare_env["cj"].read_text())
    d["projects"].pop(bare_env["mirror"], None)
    bare_env["cj"].write_text(json.dumps(d))
    assert bare_env["wt"] in _projects(bare_env)
    r = _run(bare_env, "--verify", bare_env["wt"])
    assert r.returncode == 1, r.stdout + r.stderr
    assert bare_env["mirror"] in r.stderr


def test_verify_requires_bare_bash_as_well_as_write(env):
    """--verify checks the bare Bash entry too: without it, rm / git push in a
    trusted room still reach adele's approval callback."""
    assert _run(env, env["wt"]).returncode == 0
    s = Path(env["wt"]) / ".claude" / "settings.json"
    d = json.loads(s.read_text())
    d["permissions"]["allow"].remove("Bash")
    s.write_text(json.dumps(d))
    assert _run(env, "--verify", env["wt"]).returncode == 1


# ---------------------------------------------------------------------------
# AGAST #3568: systemd-run and /tmp scratch
# ---------------------------------------------------------------------------
#
# A bare `Bash` allow lets a room run `systemd-run --user make ...`, which
# moves the build out of its own unit's 5G cap.  The room settings deny every
# direct systemd-run spelling; tests that need a real unit go through
# .claude/room-unit.sh, which pins the unit inside ritz-rooms.slice under its
# own cap and in the room's /tmp namespace.

ROOM_UNIT = REPO / ".claude" / "room-unit.sh"
ROOM_UNIT_DENY = {
    "Bash(systemd-run:*)",
    "Bash(/usr/bin/systemd-run:*)",
    "Bash(/bin/systemd-run:*)",
}
ROOM_CGROUP = "0::/user.slice/user-1000.slice/user@1000.service/ritz.slice/ritz-rooms.slice/adele-agent@ritz-task-9.service\n"


def _settings(env) -> dict:
    return json.loads((Path(env["wt"]) / ".claude" / "settings.json").read_text())


def test_apply_denies_direct_systemd_run(env):
    """Deny beats the bare Bash allow: no direct systemd-run, any spelling."""
    assert _run(env, env["wt"]).returncode == 0
    perms = _settings(env)["permissions"]
    assert ROOM_UNIT_DENY <= set(perms["deny"])
    # The deny is narrow: Bash itself (and so /tmp scratch) stays allowed.
    assert "Bash" in perms["allow"]
    assert not any(d.startswith("Bash(bash") or d == "Bash" for d in perms["deny"])


def test_verify_requires_the_systemd_run_deny(env):
    assert _run(env, env["wt"]).returncode == 0
    s = Path(env["wt"]) / ".claude" / "settings.json"
    d = json.loads(s.read_text())
    d["permissions"]["deny"].remove("Bash(systemd-run:*)")
    s.write_text(json.dumps(d))
    r = _run(env, "--verify", env["wt"])
    assert r.returncode == 1
    assert "systemd-run" in r.stderr


def _unit(tmp_path: Path, *args: str, cgroup: str = ROOM_CGROUP):
    cg = tmp_path / "cgroup"
    cg.write_text(cgroup)
    e = dict(os.environ, ROOM_UNIT_DRY_RUN="1", ROOM_UNIT_CGROUP_FILE=str(cg))
    return subprocess.run(
        ["bash", str(ROOM_UNIT), *args], env=e, capture_output=True, text=True
    )


def _argv(r: subprocess.CompletedProcess) -> list[str]:
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout.splitlines()


def test_room_unit_pins_the_unit_inside_the_room(tmp_path: Path):
    """3567's probe, through the wrapper: same options, plus the pins."""
    argv = _argv(
        _unit(
            tmp_path,
            "--quiet",
            "--unit=t3567-probe",
            "--pipe",
            "-p",
            "StandardError=file:/home/x/t3567.err",
            "--setenv=X=a $$ ${HOME} $HOME %h",
            "--",
            "/bin/bash",
            "-c",
            "echo hi",
        )
    )
    sep = argv.index("--")
    head, cmd = argv[:sep], argv[sep + 1 :]
    assert head[0] == "systemd-run"
    for pin in (
        "--user",
        "--wait",
        "--collect",
        "--slice=ritz-rooms.slice",
        "--property=MemoryMax=1G",
        "--property=CPUWeight=20",
        "--property=RuntimeMaxSec=900",
        # The room's PrivateTmp: without these the unit sees the host's /tmp
        # and 3567's /tmp/t3567probe never appeared to the room.
        "--property=PrivateTmp=yes",
        "--property=JoinsNamespaceOf=adele-agent@ritz-task-9.service",
    ):
        assert pin in head, (pin, head)
    assert "--unit=t3567-probe" in head
    assert "--pipe" in head
    assert "--property=StandardError=file:/home/x/t3567.err" in head
    assert "--setenv=X=a $$ ${HOME} $HOME %h" in head
    assert cmd == ["/bin/bash", "-c", "echo hi"]


@pytest.mark.parametrize(
    "args",
    [
        ["--slice=user.slice", "--", "make"],
        ["--slice", "app.slice", "--", "make"],
        ["-p", "Slice=app.slice", "--", "make"],
        ["--property=Slice=app.slice", "--", "make"],
        ["-p", "MemoryMax=infinity", "--", "make"],
        ["-p", "CPUWeight=100", "--", "make"],
        ["-p", "JoinsNamespaceOf=foo.service", "--", "make"],
        ["--scope", "--", "make"],
        ["--system", "--", "make"],
        ["--machine=x", "--", "make"],
        ["--on-active=5", "--", "make"],
        ["--unit=../x", "--", "make"],
        ["--unit=ritz-gate.slice", "--", "make"],
        # The manager opens file: outputs in the HOST's /tmp, not the room's:
        # 3567's probe file never appeared.  Refused, pointing at --pipe.
        ["-p", "StandardOutput=file:/tmp/t3567probe", "--", "true"],
        ["-p", "StandardError=append:/var/tmp/x", "--", "true"],
        ["--property=StandardOutput=truncate:/tmp/x", "--", "true"],
        ["make"],  # no `--`: options and command must be unambiguous
        ["--"],  # no command
    ],
)
def test_room_unit_refuses_anything_that_could_leave_the_room(tmp_path, args):
    r = _unit(tmp_path, *args)
    assert r.returncode == 2, (args, r.stdout, r.stderr)
    assert r.stdout == ""


def test_room_unit_refuses_outside_a_room_unit(tmp_path: Path):
    """No room unit in our cgroup: nothing to pin to, so nothing runs."""
    r = _unit(tmp_path, "--", "/bin/true", cgroup="0::/user.slice/session-3.scope\n")
    assert r.returncode == 2
    assert r.stdout == ""


def test_room_unit_restart_self(tmp_path: Path):
    """The briefing's self-restart, now that direct systemd-run is denied.
    It can only restart the unit the caller is running in."""
    assert _argv(_unit(tmp_path, "restart-self")) == [
        "systemd-run",
        "--user",
        "--on-active=15",
        "systemctl",
        "--user",
        "restart",
        "adele-agent@ritz-task-9.service",
    ]
    assert _unit(tmp_path, "restart-self", "adele-agent@rz.service").returncode == 2


# ---------------------------------------------------------------------------
# AGAST #4215: a compound /tmp command that asks despite the bare Bash allow
# ---------------------------------------------------------------------------
#
# ritz-task-4078 stalled on one Bash call that wrote nothing under .claude/:
#   R=/tmp/t4078/r4; rm -rf $R; HOGS=(); for c in 4 5 6; do for k in ...; do
#   taskset -c $c bash -c 'while :; do :; done' & HOGS+=($!); done; done; ...
#   kill ${HOGS[@]}
# Bisected with `claude -p` (CLI 2.1.322, the room's settings): the CLI asks
# only when ONE call combines `rm -rf`, a loop backgrounding `bash -c '...'`
# into a $! array, and `kill` of that array; drop any part and it runs.  No
# allow entry changes that (bare Bash is already allowed), and adele tiers the
# ask "destructive" and holds it for a human.  The same text run as
# `bash /tmp/<script>.sh`, or with the `rm -rf` in its own call, runs without
# asking.  So the fix is the briefing; this pins it.

SKILL = REPO / ".claude" / "skills" / "rz-iterate" / "SKILL.md"
# AGAST #4698: the standing room rules left the briefing for ROOM.md, which
# every room has in its worktree; the briefing itself is a short template.
ROOM = SKILL.parent / "ROOM.md"


def _briefing_paragraph(head: str, path: Path = SKILL) -> str:
    text = path.read_text()
    at = text.index(head)
    end = text.find("\n\n", at)
    return text[at : end if end >= 0 else len(text)]


@pytest.mark.unit
def test_briefing_tells_rooms_to_script_rm_plus_background_kill():
    para = _briefing_paragraph("**Writing under `.claude/` asks a human**", ROOM)
    assert "#4215" in para
    # The trigger, named so a room recognises it ...
    assert "rm -rf" in para and "kill" in para and "&" in para
    # ... and the two phrasings measured not to ask.
    assert "bash /tmp/" in para
    assert "own call" in para


@pytest.mark.unit
def test_briefing_says_spawn_does_not_create_tmpdir_dropin():
    """AGAST #4476: the `60-rz-room-tmpdir.conf` drop-in is a host step,
    not something `adele room spawn` creates; the host installs it before
    the unit starts."""
    text = SKILL.read_text()
    at = text.index("**Exec-capable TMPDIR (bangerang")
    end = text.index("`TEARDOWN ritz-task-<id>`", at)
    flat = " ".join(text[at:end].split()).lower()
    # The drop-in is still named where the host installs it ...
    assert "60-rz-room-tmpdir.conf" in flat
    # ... but the stale "At SPAWN the host makes ... before the unit starts"
    # is replaced by an explicit spawn-does-not-create / host-step statement.
    assert "does not create" in flat
    assert "host step" in flat
    assert "before starting the unit" in flat


@pytest.mark.unit
def test_briefing_says_fleet_runs_default_harness_host_decides_config():
    """Aaron, 2026-11-23 (AGAST #4569, replacing #4476's DeepSeek pin):
    rooms run the default harness and model, with no harness drop-in.
    Since 2026-11-24 23:09Z each host's adele.env decides CLAUDE_CONFIG_DIR
    (AGAST #4698), so there is no fleet-wide bettercomp rule. The three
    places a stale DeepSeek pin hides are named so a room stuck on
    `unrecognized_model` can be cleared."""
    para = _briefing_paragraph("**Fleet model")
    flat = " ".join(para.split()).lower()
    # Default harness/model: no flags, no drop-in, no model= on a SPAWN.
    assert "default harness and model" in flat
    assert "do **not** pass `--harness` / `--model`" in flat
    assert "do **not** install any harness drop-in" in flat
    assert "90-adele-deepseek.conf" in flat
    assert "95-adele-harness.conf" in flat
    assert "model=" in flat
    # The host decides the config dir: huburght unset, omegalisk bettercomp.
    assert "each host's `~/.config/adele/adele.env` decides `claude_config_dir`" in flat
    assert "huburght it is unset" in flat
    assert "omegalisk rooms get `claude_config_dir=/home/aaron/.claude-bettercomp`" in flat
    # The retired fleet-wide rule must not creep back.
    assert "**must** have" not in flat
    # The three hiding places of a stale DeepSeek pin.
    assert "room.env" in flat and "drop-in" in flat and "rooms.json" in flat
    assert "clear all three" in flat


@pytest.mark.unit
def test_briefing_says_budget_only_gate_verdict_is_terminal():
    """AGAST #4423: a budget-only verdict is final, not a reason to re-queue."""
    text = SKILL.read_text()
    # The room's rules (ROOM.md, AGAST #4698).
    # Normalise the prose: it is hard-wrapped, so phrases straddle lines.
    flat = " ".join(ROOM.read_text().split())
    # The terminal case, stated next to the exit-124 rule it is confused with.
    assert "budget-only" in flat
    assert "terminal" in flat
    assert "0 failed" in flat
    assert "do not re-gate" in flat
    # The gate section must name it too, and say rz accepts such a REAP.
    gate_at = text.index("### Gate coverage: what runs before a merge")
    gate = " ".join(text[gate_at:].split())
    assert "budget-only" in gate
    assert "`rz` accepts" in gate


@pytest.mark.unit
def test_briefing_bans_machine_wide_kills_and_direct_ci_local():
    """AGAST #4468: the full suite runs only through run-gate.sh, and a room
    may stop only the PIDs it spawned -- never pkill -f or a negative PGID."""
    text = SKILL.read_text()
    # 1. The room's rules (ROOM.md, AGAST #4698), step 6, where the gate is
    # explained.  Normalise the hard-wrapped prose so phrases can straddle lines.
    flat = " ".join(ROOM.read_text().split())
    # Gate-slot-only builds: no hand-started ci_local.py/make ci-local.
    assert "only through `run-gate.sh`" in flat
    assert "ci_local.py" in flat
    assert "make ci-local" in flat
    # No machine-wide kill may reach another room's pytest.
    assert "pkill -f" in flat
    assert "kill -- -PGID" in flat
    # 2. The gate section (## Hosts) carries the rule and its evidence.
    hosts_at = text.index("## Hosts")
    hosts_end = text.index("\n## ", hosts_at + 1)
    hosts = " ".join(text[hosts_at:hosts_end].split())
    assert "pkill -f" in hosts
    assert "ci_local.py" in hosts
    assert "run-gate.sh" in hosts
    assert "4295" in hosts and "31m18s" in hosts
    assert "AGAST #4468" in hosts
    # 3. run-gate.sh's header says it, where a room opening the script reads.
    gate_sh = (SKILL.parent / "run-gate.sh").read_text()
    assert "AGAST #4468" in gate_sh
    assert "pkill -f" in gate_sh


@pytest.mark.unit
def test_briefing_teardown_proves_land_by_the_commits_own_changes():
    """AGAST #4549: a rebase changes the SHA and can flip `git cherry` to `+`,
    so the land is proven by the commit's own changed lines and file set."""
    text = SKILL.read_text()
    # The **Remote room:** paragraph has no blank line before item 6, so the
    # _briefing_paragraph() helper would run into the next step and let these
    # assertions pass on the wrong text. Cut on the next item explicitly.
    at = text.index("**Remote room:**")
    end = text.index("6. **Gate fails", at)
    flat = " ".join(text[at:end].split())
    # The SHA is expected to differ after the rebase; say so.
    assert "legitimately" in flat and "differs" in flat
    # The proof is the commit's own changes, byte-identical, at zero context.
    assert "unified=0" in flat
    assert "byte-identical" in flat
    assert "range-diff" in flat
    # Context makes hunk line numbers move and yields a false DIFFERS.
    assert "false DIFFERS" in flat
    # Subject/sibling matching is corroboration, never the proof.
    assert "corroboration only" in flat and "never the proof" in flat
    # The retired patch-identity claim must not creep back.
    assert "patch identity" not in flat
    # The room rm guard is the actual safety gate.
    assert "room rm" in flat


@pytest.mark.unit
def test_briefing_says_write_ritz_not_c():
    """AGAST #4673: every room is told the c"" POLICY, and rz checks for it.

    The step sits between "Test first" (2) and "Subagents" (3); it is `2a`
    so the 40-odd "step N" references to the later steps stay true.
    """
    text = SKILL.read_text()
    briefing = ROOM.read_text()  # the room's rules (AGAST #4698)
    step2 = briefing.index("2. **Test first.**")
    step3 = briefing.index("3. **Subagents (Agent tool)")
    at = briefing.index("2a. **Write Ritz, not C.**")
    assert step2 < at < step3
    flat = " ".join(briefing[at:step3].split())
    assert "only for C interop" in flat
    assert "NUL termination" in flat
    assert 'no new `c""` outside an interop boundary' in flat
    assert "take `StrView`" in flat
    assert "docs/RITZ_NOT_C.md" in flat
    # The reap side: rz reads a REAP's diff for added c"" and bounces it.
    reap_at = text.index("2. **Check each REAP line before it boards.**")
    reap_end = text.index("3. **Build the train**", reap_at)
    reap = " ".join(text[reap_at:reap_end].split())
    assert 'added `c"`' in reap
    assert "interop boundary" in reap
    assert "Bounce any added literal outside an interop boundary" in reap


@pytest.mark.unit
def test_briefing_template_is_at_most_150_words_and_points_at_room_md():
    """AGAST #4698: the briefing sent to every room (and inside every host
    SPAWN) carries only what changes per ticket; the standing rules are in
    ROOM.md, which the room reads from its own worktree."""
    text = SKILL.read_text()
    at = text.index("### The briefing (send verbatim")
    start = text.index("```markdown\n", at) + len("```markdown\n")
    end = text.index("\n```\n", start)
    template = text[start:end]
    assert template.startswith("## #<id> <title>")
    words = len(template.split())
    assert words <= 150, words
    assert ".claude/skills/rz-iterate/ROOM.md" in template
    assert "claim <claim name>" in template and "callback rz" in template
    assert "rz-train/<tail12>" in template
    # ROOM.md carries the rules the briefing used to: steps 0-9 (with 2a),
    # the self-restart, the never-do list, remote and spot hosts.
    room = ROOM.read_text()
    for step in ["0.", "1.", "2.", "2a.", "3.", "4.", "5.", "6.", "7.", "8.", "9."]:
        assert f"\n{step} **" in room, step
    for head in ["**Never end a turn with work pending:**",
                 "restart-self", "**Never** check out or push `main`",
                 "## Remote host", "## Spot host"]:
        assert head in room, head
    # A "Messages" rule for agent-to-agent traffic stays in the skill.
    assert "### Messages" in text
