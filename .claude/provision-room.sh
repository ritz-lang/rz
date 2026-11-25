#!/usr/bin/env bash
#
# Provision a freshly-created task-room worktree so a HEADLESS Adele agent can
# work in it without stalling on a permission prompt nobody is there to answer.
#
#   .claude/provision-room.sh <worktree-path>
#   .claude/provision-room.sh --verify <worktree-path>   # check only, no writes
#   .claude/provision-room.sh --remove <worktree-path>   # drop worktree trust entry (reap)
#
#   --room ritz-task-<id>, before the path, with any mode: the room's Claude
#   account (AGAST #4699, .claude/room-account.sh) decides the config file,
#   so trust and the allow list land in the .claude.json the room reads.
#   Apply installs the room's account drop-in first and refuses a logged-out
#   account; --verify checks the drop-in; --remove drops it.  Without
#   --room, the caller's environment decides, as before.
#
# Config file: ${CLAUDE_CONFIG_DIR:-$HOME}/.claude.json, or the room's
# account's with --room.  Trust is set under the
# MAIN checkout's path (the key the CLI checks for a worktree, AGAST #2746; for
# a worktree of a BARE repo, the repo dir itself, #4256) and under the
# worktree's own path.  See TRUST_KEY below.
#
# ---------------------------------------------------------------------------
# WHY THIS EXISTS  (AGAST #1378 — measured 2026-09-08, not theorised)
# ---------------------------------------------------------------------------
# ritz-task-1373 burned 30 minutes of wall clock doing nothing:
#
#   21:35:53  DESTRUCTIVE tool requires approval: Write - /tmp/migrate_amp.py
#   22:05:53  approval timed out after 1800.0s -> deny
#
# The causal chain, every link verified against a live SDK client:
#
#   1. `git worktree add` creates a path Claude Code has never seen.
#   2. A path absent from ~/.claude.json "projects" is an UNTRUSTED workspace.
#   3. Claude Code IGNORES every permissions.allow entry in an untrusted
#      workspace's .claude/settings.json.  It says so out loud:
#        "Ignoring 1 permissions.allow entry from .claude/settings.json:
#         this workspace has not been trusted."
#   4. With nothing to shadow it, adele's can_use_tool callback is consulted.
#   5. adele classifies Write as DESTRUCTIVE (llm_agents/claude/permissions.py)
#      and blocks on a WebSocket approval from a human.
#   6. A spawned room has no human in it.  30 minutes later: denied.
#
# The parent room does not hit this because ~/dev/ritz-lang/rz has
# hasTrustDialogAccepted: true.  In September 2026 each worktree needed its own
# entry.  Since CLI 2.1.316 (AGAST #2746) the CLI looks a worktree up under the
# MAIN checkout's key instead, so a host whose main checkout was never trusted
# ignores every room's allow list.  This script now trusts both keys.
#
# ---------------------------------------------------------------------------
# TWO FACTS THAT LOOK LIKE TYPOS AND ARE NOT
# ---------------------------------------------------------------------------
# (a) The rule is a BARE tool name, `Write`, not `Write(<path>/**)`.
#     Only a whole-tool allow entry auto-approves BEFORE can_use_tool is
#     consulted; a path-scoped entry still falls through to the callback, which
#     is the thing that blocks.  Measured:
#         Edit(//tmp/permtest/**)  -> callback INVOKED (would hang under adele)
#         Write                    -> callback NOT invoked   <- what we need
#
# (b) `Write(<path>)` rules are INERT for file permission checks.  The CLI
#     rejects them explicitly:
#         "Write(/tmp/**) is not matched by file permission checks - only
#          Edit(path) rules are.  Use Edit(/tmp/**) instead."
#     ~/.claude/settings.json has carried a `Write(/tmp/**)` entry that has
#     never done anything.  Path-scoped file rules must be spelled Edit(...),
#     and an absolute path needs a DOUBLE leading slash: Edit(//tmp/**).
#     Edit(/tmp/**) is interpreted relative to the project root and does not
#     match /tmp.  Measured: //tmp/permtest/** wrote the file, /tmp/permtest/**
#     did not.
#
# ---------------------------------------------------------------------------
# WHY NOT JUST FIX ~/.claude/settings.json
# ---------------------------------------------------------------------------
# A bare `Write` at the user level would auto-approve Write for every room on
# this machine, including interactive ones where a human review of a
# destructive tool is the point.  Scoping it to the spawned worktree keeps the
# blast radius to rooms that have no human in them by construction.
#
set -euo pipefail
# Borque's hostd runs this as a hook with a clean environment (AGAST #3722,
# .borque/profile.toml): maybe no HOME or PATH.  Supply the standard ones.
# With no PATH, the gate's venv goes first, as it does on a host's own PATH:
# ~/dev/.venv (most hosts), then ~/dev/nevelis/.venv (omegalisk), if present.
# "No PATH" includes bash's own fallback, which it sets but doesn't export.
: "${HOME:=$(getent passwd "$(id -u)" | cut -d: -f6)}"
# Pure bash: with no PATH yet, there may be no dirname to run.
_d="${BASH_SOURCE[0]%/*}"; [[ "$_d" != "${BASH_SOURCE[0]}" ]] || _d=.
# shellcheck source=host-env.sh
source "$_d/host-env.sh"
ROOM_ACCOUNT="$_d/room-account.sh"
unset _d
if [[ -z "${PATH:-}" || "$(declare -p PATH)" != "declare -x"* ]]; then
    PATH="$(rz_venv_path /usr/local/bin:/usr/bin:/bin)"
fi
export HOME PATH

MODE=apply
ROOM=""
while [[ $# -gt 1 ]]; do
    case "$1" in
        --verify) MODE=verify; shift ;;
        --remove) MODE=remove; shift ;;
        # The host checks below and nothing else: "could this host gate a room?"
        # Any dir on the build filesystem will do, e.g. ~/dev/ritz-lang.
        --check-host) MODE=check; shift ;;
        --room) ROOM="$2"; shift 2 ;;
        *) break ;;
    esac
done

if [[ $# -ne 1 ]]; then
    echo "usage: $0 [--verify|--remove|--check-host] [--room ritz-task-<id>] <worktree-path>" >&2
    exit 2
fi

# Resolve to an absolute, symlink-free path.  ~/.claude.json is keyed by the
# exact string Claude Code computes for cwd; a relative or symlinked spelling
# creates an entry that is never consulted, which fails EXACTLY like having no
# entry at all — silently.
#
# --remove runs AFTER `git worktree remove`, so the directory is usually gone by
# then.  Fall back to a lexical absolute path rather than refusing: leaving a
# stale trust entry behind is the whole thing this mode exists to prevent.
if WT="$(cd "$1" 2>/dev/null && pwd -P)"; then
    :
elif [[ $MODE == remove ]]; then
    WT="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$1")"
else
    echo "error: worktree does not exist: $1" >&2
    exit 1
fi

SETTINGS="$WT/.claude/settings.json"

# The global config the CLI reads: $CLAUDE_CONFIG_DIR/.claude.json when that is
# set, else ~/.claude.json.  The CLI's own warning names the file it consults.
CLAUDE_JSON="${CLAUDE_CONFIG_DIR:-$HOME}/.claude.json"

# room_claude_json: with --room, the .claude.json of the config dir the room
# runs under (room-account.sh --config-dir: the installed drop-in's record,
# else host.env's choice).  `inherit` (no RZ_ROOM_ACCOUNTS) keeps the above.
room_claude_json() {
    [[ -n "$ROOM" ]] || return 0
    local d
    d="$("$ROOM_ACCOUNT" --config-dir "$ROOM")" || return 1
    case "$d" in
        inherit) ;;
        default) CLAUDE_JSON="$HOME/.claude.json" ;;
        *) CLAUDE_JSON="$d/.claude.json" ;;
    esac
}

# The key the CLI checks trust under.  For a git WORKTREE, Claude Code (at
# least 2.1.316 .. 2.1.322) does NOT look up the worktree's own path: it looks
# up the MAIN checkout's.  Measured (AGAST #1378, 2026-11-11), cwd = worktree:
#   trusted: worktree only   -> "Ignoring 7 permissions.allow entries ...
#                                set projects["<main checkout>"]..."  (callback hit)
#   trusted: main checkout   -> entries honoured, callback never reached
# This script used to trust only the worktree path, and --verify checked that
# same path, so it passed while every Ritz room's allow list was ignored.
# The CLI's key is the common git dir minus a trailing /.git: for a normal
# checkout, its parent (the main checkout); for a BARE repo, the repo dir
# itself.  Borque's hostd makes room worktrees from a bare mirror
# (~/borque/mirrors/ritz.git), and this script used to fall back to the
# worktree path there, so every Borque room's allow list was ignored while
# --verify passed (AGAST #4256; measured on CLI 2.1.326 for bare, bare without
# a .git suffix, and non-bare).  --verify checks this same key.  Not a
# worktree (or --remove after the dir is gone): fall back to the path itself.
TRUST_KEY="$WT"
if COMMON="$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
    COMMON="$(cd "$COMMON" && pwd -P)"
    if [[ "$(basename "$COMMON")" == .git ]]; then
        TRUST_KEY="$(dirname "$COMMON")"
    else
        TRUST_KEY="$COMMON"   # bare repo: the CLI keys on the repo dir
    fi
fi

# Tools a headless room must never block on.  Bare names only — see fact (a).
#
# Bash is already allowed at the user level, but it is repeated here so the
# room's permission surface is readable in one file instead of inferred from
# two.  Read/Glob/Grep are read-only tiers adele auto-approves anyway; they are
# listed for the same reason.
#
# DENY: direct systemd-run, every spelling (AGAST #3568).  The room's 5G cap
# is on its own unit (adele-agent@<room>.service MemoryMax), not on
# ritz-rooms.slice (32G), so `systemd-run --user make ...` takes a build out
# of the cap.  With bare Bash allowed it ran without a prompt.  A deny beats
# the bare allow and is refused outright, so it never waits for a human.
# Tests that need a real unit, and the self-restart, go through
# .claude/room-unit.sh, which pins the unit inside the room.  Scripts that
# call systemd-run themselves (run-gate.sh) are not affected: the CLI only
# sees `bash <script>`.
#
# /tmp scratch (mktemp, cp, sed -i, rm under /tmp) needs no entry: bare Bash
# and Write cover it, measured 2026-11-16 with CLI 2.1.322.
#
# One /tmp exception, also beyond any entry here (AGAST #4215, bisected with
# `claude -p` and these settings on CLI 2.1.322): the CLI asks when ONE Bash
# call combines `rm -rf`, a loop that backgrounds `bash -c '...' &` into a $!
# array, and `kill` of that array (ritz-task-4078's load repro).  Drop any one
# part and it runs.  Adele tiers that ask "destructive" and holds it for a
# human.  The same text run as `bash /tmp/<script>.sh`, or with the `rm -rf`
# in a call of its own, does not ask; the briefing says so.
#
# What no entry here can fix (measured, same day): the CLI ASKS for every
# write under a `.claude/` directory (Write, Edit, `cp`/`sed -i`/`rm`/`>`
# into it), whatever the allow list, a path rule like Edit(/.claude/**), or a
# PreToolUse hook answering "allow" say.  In a room that ask goes to adele's
# callback, which auto-approves Edit, cp, sed -i and > but holds Write and
# any `rm` for a human: that is what stalled ritz-task-3567.  The briefing
# (rz-iterate SKILL.md) tells rooms how to work around it.
read -r -d '' ALLOW_JSON <<'EOF' || true
{
  "_comment": "Written by .claude/provision-room.sh — see that file for why these are bare tool names and why systemd-run is denied. Machine-local; gitignored. AGAST #1378, #3568.",
  "permissions": {
    "allow": ["Write", "Edit", "NotebookEdit", "Read", "Glob", "Grep", "Bash"],
    "deny": ["Bash(systemd-run:*)", "Bash(/usr/bin/systemd-run:*)", "Bash(/bin/systemd-run:*)"]
  }
}
EOF

trusted() {
    python3 - "$1" "$CLAUDE_JSON" <<'PY'
import json, pathlib, sys
wt = sys.argv[1]
p = pathlib.Path(sys.argv[2])
try:
    d = json.loads(p.read_text())
except Exception:
    sys.exit(1)
sys.exit(0 if d.get('projects', {}).get(wt, {}).get('hasTrustDialogAccepted') is True else 1)
PY
}

if [[ $MODE == remove ]]; then
    # A teardown is never blocked: a host.env broken since the spawn falls
    # back to the caller's config file, and says so.
    room_claude_json || echo "  warning: no account for $ROOM; using $CLAUDE_JSON" >&2
    # Drops the WORKTREE's own entry only.  The main checkout's entry is shared
    # by the parent room and every live worktree; never remove it here.
    python3 - "$WT" "$CLAUDE_JSON" <<'PY'
import json, pathlib, sys
wt = sys.argv[1]
p = pathlib.Path(sys.argv[2])
d = json.loads(p.read_text())
gone = d.get('projects', {}).pop(wt, None)
p.write_text(json.dumps(d, indent=2))
print(f"  {'dropped' if gone is not None else 'no'} trust entry for {wt}")
PY
    if [[ -n "$ROOM" ]]; then
        "$ROOM_ACCOUNT" --remove "$ROOM" | sed 's/^/  /'
    fi
    exit 0
fi

if [[ $MODE == verify ]]; then
    rc=0
    room_claude_json || exit 1
    if [[ -n "$ROOM" ]]; then
        if out="$("$ROOM_ACCOUNT" --verify "$ROOM")"; then
            echo "  ✓ $out"
        else
            rc=1
        fi
    fi
    if trusted "$TRUST_KEY"; then
        echo "  ✓ trusted in $CLAUDE_JSON under the key the CLI checks: $TRUST_KEY"
    else
        echo "  ✗ NOT trusted under $TRUST_KEY in $CLAUDE_JSON — project permissions will be IGNORED" >&2
        rc=1
    fi
    if [[ -f "$SETTINGS" ]] && python3 - "$SETTINGS" <<'PY'
import json, sys
allow = json.load(open(sys.argv[1])).get('permissions', {}).get('allow', [])
sys.exit(0 if {'Write', 'Bash'} <= set(allow) else 1)
PY
    then
        echo "  ✓ bare 'Write' and 'Bash' allow entries present: $SETTINGS"
    else
        echo "  ✗ $SETTINGS missing a bare 'Write' or 'Bash' allow entry" >&2
        rc=1
    fi
    if [[ -f "$SETTINGS" ]] && python3 - "$SETTINGS" <<'PY'
import json, sys
deny = json.load(open(sys.argv[1])).get('permissions', {}).get('deny', [])
want = {'Bash(systemd-run:*)', 'Bash(/usr/bin/systemd-run:*)', 'Bash(/bin/systemd-run:*)'}
sys.exit(0 if want <= set(deny) else 1)
PY
    then
        echo "  ✓ direct systemd-run denied (tests use .claude/room-unit.sh)"
    else
        echo "  ✗ $SETTINGS missing a systemd-run deny entry: builds could leave the room's cap" >&2
        rc=1
    fi
    [[ $rc -eq 0 ]] && echo "  room permissions OK — a headless Write will not block"
    exit $rc
fi

# --- host checks (apply only) -------------------------------------------------
# What a room's gate needs that Borque's host probe can't see (AGAST #3722):
# the probe reports python/pytest/llvm/lld from PATH, not the venv's modules,
# qemu, OVMF, lld-link, disk for a build, or a scratch dir that can run a binary.
# A host missing one would pass the probe, take the room, and fail its gate
# hours later, so refuse here instead: exit 1 with ONE line naming every
# problem, before anything is written.  Presence and version checks only:
# this runs at every spawn.  --verify and --remove skip it, so a host that
# has since lost a tool can still verify and tear down.
#
#   RZ_PROVISION_HOST_CHECKS=0   skip (test_provision_room.py; CI has no qemu)
#   RZ_LLVM_BIN   LLVM's bin dir, added to PATH           (default /usr/lib/llvm-21/bin)
#   OVMF_CODE     the firmware; else harland/boot/test.sh's search list
#   RZ_MIN_DISK_GB  free space on the worktree's filesystem (default 20)
#   RZ_EXEC_DIRS  colon list; one must run a binary
#                 (default $TMPDIR:/tmp:~/tmp:$RZ_GATE_DIR or ~/dev/ritz-lang/gate-logs:~)
#
# Which python: the one the gate runs.  run-gate.sh passes its PATH on, so
# under the room's unit that is PATH's first python3, looked up before LLVM's
# bin dir and ~/.local/bin (where starbux and chungus keep lld-link) go on
# PATH here.  A plain SSH/login shell is NOT the unit though: its PATH has
# /usr/bin/python3, which has no llvmlite and no pytest, and refusing that
# sent spawners off to "fix" a healthy machine (AGAST #4432, starbux
# 2026-11-21).  room_python resolves the interpreter, using the venv the
# unit puts first when PATH's own python cannot gate, and the caller says
# which one it judged.  No venv path is hardcoded in a branch: rz_venv_path
# names ~/dev/.venv and ~/dev/nevelis/.venv (omegalisk).
# Tests: projects/ritz/tools/test_borque_hooks.py.

# room_venv_bins: the venv bin dirs a room unit puts first on PATH, in the
# order rz_venv_path prepends them (the last prepended ends up first):
# ~/dev/.venv, then ~/dev/nevelis/.venv.  Only the ones that exist.
room_venv_bins() {
    local IFS=: v
    for v in $(rz_venv_path ""); do
        [[ -n "$v" ]] && printf '%s\n' "$v"
    done
}

# same_dir <a> <b>: both name the same physical directory.
same_dir() {
    local a b
    a="$(cd "$1" 2>/dev/null && pwd -P)" || return 1
    b="$(cd "$2" 2>/dev/null && pwd -P)" || return 1
    [[ "$a" == "$b" ]]
}

# pylacks <python>: print what <python> lacks to run the gate's Python side
# (llvmlite, yaml, pytest < 9.2); return 0 when it can gate, 1 when it cannot.
# A crashed interpreter prints nothing, so callers say "<path> failed".
pylacks() {
    "$1" - "$1" 2>&1 <<'PY'
import importlib.metadata as md, importlib.util as iu, sys
py = sys.argv[1]
bad = [f"{m} not importable by {py}" for m in ("llvmlite", "yaml") if iu.find_spec(m) is None]
try:
    v = md.version("pytest")
    if tuple(int(x) for x in v.split(".")[:2] if x.isdigit()) >= (9, 2):
        bad.append(f"pytest {v} at {py} (need < 9.2, requirements.txt)")
except md.PackageNotFoundError:
    bad.append(f"no pytest at {py}")
print("; ".join(bad))
sys.exit(1 if bad else 0)
PY
}

# room_python: print the python3 the gate will run, or nothing when PATH has
# no python3 at all.  PATH's own python wins while it can gate.  When it
# cannot and it is NOT one of the room venvs' interpreters, PATH is not the
# unit's (a login shell's /usr/bin/python3), so take the venv the unit puts
# first -- that is the #4432 fix; the venv is then judged like any other, so
# a broken one still refuses.  A python already selected FROM a room venv IS
# the gate's: a second venv must not mask it.
room_python() {
    local py vbin alt=""
    py="$(command -v python3)" || py=""
    [[ -n "$py" ]] || return 0
    if pylacks "$py" >/dev/null 2>&1; then
        printf '%s\n' "$py"
        return 0
    fi
    while IFS= read -r vbin; do
        if same_dir "$vbin" "$(dirname "$py")"; then
            printf '%s\n' "$py"
            return 0
        fi
        if [[ -z "$alt" && -x "$vbin/python3" ]]; then
            alt="$vbin/python3"
        fi
    done < <(room_venv_bins)
    printf '%s\n' "${alt:-$py}"
}

host_problems() {
    local py p=() tool f ovmf="" tmp out
    py="$(room_python)"
    local PATH="${RZ_LLVM_BIN:-/usr/lib/llvm-21/bin}:$HOME/.local/bin:$PATH"
    if [[ -z "$py" ]]; then
        p+=("no python3 on PATH ($PATH)")
    elif ! out="$(pylacks "$py")"; then
        p+=("${out:-$py failed}")
    fi
    for tool in qemu-system-x86_64 lld-link; do
        command -v "$tool" >/dev/null || p+=("no $tool on PATH")
    done
    if [[ -n "${OVMF_CODE:-}" ]]; then
        [[ -f "$OVMF_CODE" ]] && ovmf="$OVMF_CODE"
    else
        for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd \
            /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd; do
            [[ -f "$f" ]] && { ovmf="$f"; break; }
        done
    fi
    [[ -n "$ovmf" ]] || p+=("no OVMF firmware (${OVMF_CODE:-install the ovmf package})")
    local min="${RZ_MIN_DISK_GB:-20}" free
    free="$(df -Pk "$WT" 2>/dev/null | awk 'NR == 2 { print int($4 / 1048576) }')"
    if [[ -z "$free" || "$free" -lt "$min" ]]; then
        p+=("free disk ${free:-unknown} GB on $WT (need $min)")
    fi
    # A gate needs SOME dir that can run a binary, not $TMPDIR in particular:
    # bangerang's /tmp is noexec for good (CIS policy), and #3704 gives each
    # gate its own TMPDIR under the gate dir.  Pass on the first usable one.
    local dirs d ok=""
    dirs="${RZ_EXEC_DIRS:-${TMPDIR:+$TMPDIR:}/tmp:$HOME/tmp:${RZ_GATE_DIR:-$HOME/dev/ritz-lang/gate-logs}:$HOME}"
    local IFS=:
    for d in $dirs; do
        [[ -d "$d" ]] || continue
        tmp="$(mktemp "$d/rz-exec.XXXXXX" 2>/dev/null)" || continue
        printf '#!/bin/sh\nexit 0\n' > "$tmp" && chmod +x "$tmp" && "$tmp" 2>/dev/null && ok="$d"
        rm -f "$tmp"
        [[ -n "$ok" ]] && break
    done
    unset IFS
    [[ -n "$ok" ]] || p+=("no exec-able scratch dir (tried $dirs; noexec or unwritable)")
    local line="" x
    for x in ${p[@]+"${p[@]}"}; do line+="${line:+; }$x"; done
    echo "$line"
}

if [[ $MODE == check || "${RZ_PROVISION_HOST_CHECKS:-1}" != 0 ]]; then
    problems="$(host_problems)"
    if [[ -n "$problems" ]]; then
        echo "provision-room: host can't gate a room: $problems" >&2
        # "Clear Ritz caches" did nothing when the CAS was empty: the space is
        # stale sandbox working sets, which `rz cache gc` now evicts by age
        # (AGAST #4421). Print the recipe that actually reclaims it. stdout,
        # so the one-line refusal on stderr stays one line.
        if [[ "$problems" == *"free disk "* ]]; then
            cat <<'EOF'
provision-room: free disk is below the gate floor (RZ_MIN_DISK_GB, default 20 GB). Reclaim it with:
provision-room:   rz cache gc
provision-room:     evicts sandbox repo copies and <compiler>/tmp older than 1 day, biggest first
provision-room:   sandbox repo copies live in ~/.cache/ritz/*/home/*/dev/ritz-lang/*
provision-room:     (and ~/.cache/ritz/home/*/dev/ritz-lang/*); each child is one stale clone
provision-room:   ~/tmp orphans: remove a dir only when no live systemd unit, worktree, or open
provision-room:     file (lsof) owns it -- e.g. `systemctl list-units`, `git worktree list`, `lsof +D DIR`
provision-room:   never delete anything under a live gate: a sandbox copy or ~/tmp dir with a
provision-room:     recent mtime is that gate's working set, and rz cache gc leaves it alone
EOF
        fi
        exit 1
    fi
    # Say which interpreter passed.  From a login shell this is a venv's, not
    # PATH's first, and a spawner reading the log needs to see that (#4432).
    echo "  python3 the gate will use: $(room_python)"
fi
if [[ $MODE == check ]]; then
    echo "provision-room: host ok"
    exit 0
fi

# --- apply ------------------------------------------------------------------

# The room's account first: a logged-out one refuses here, before any trust
# is written, and the drop-in it installs records the config dir the rest of
# this script (and --verify, --remove) then writes to.
if [[ -n "$ROOM" ]]; then
    "$ROOM_ACCOUNT" --install "$ROOM" | sed 's/^/  /'
    [[ ${PIPESTATUS[0]} -eq 0 ]] || exit 1
    room_claude_json || exit 1
fi

# Trust the workspace.  Read-modify-write via python so we never mangle the
# rest of ~/.claude.json (it holds auth and per-project history).
# Both keys: the main checkout is what the CLI checks today; the worktree's
# own key is kept so a CLI that keys on cwd again still finds it.
python3 - "$CLAUDE_JSON" "$TRUST_KEY" "$WT" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text())
for key in dict.fromkeys(sys.argv[2:]):
    d.setdefault('projects', {}).setdefault(key, {})['hasTrustDialogAccepted'] = True
    print(f"  trusted workspace key: {key}")
p.write_text(json.dumps(d, indent=2))
PY

mkdir -p "$WT/.claude"
printf '%s\n' "$ALLOW_JSON" > "$SETTINGS"
echo "  wrote: $SETTINGS"

# Keep the settings file out of the child's commits via the worktree's LOCAL
# exclude file, not .gitignore.  The room branches from whatever HEAD was, which
# may predate main's .gitignore entry — and the child is the one process most
# likely to `git add -A`.  info/exclude is branch-independent, so it holds
# regardless of where the branch started.
#
# Measured, not assumed: `git -C <worktree> rev-parse --git-path info/exclude`
# resolves to the COMMON git dir (~/dev/ritz-lang/rz/.git/info/exclude), shared
# by the main checkout and every worktree — not a per-worktree file.  The append
# is idempotent (grep -qxF) precisely because every room writes to the same one.
EXCLUDE="$(git -C "$WT" rev-parse --git-path info/exclude 2>/dev/null || true)"
if [[ -n "$EXCLUDE" ]]; then
    mkdir -p "$(dirname "$EXCLUDE")"
    grep -qxF '.claude/settings.json' "$EXCLUDE" 2>/dev/null \
        || printf '\n# machine-local room permissions (.claude/provision-room.sh)\n.claude/settings.json\n' >> "$EXCLUDE"
    echo "  excluded from git: .claude/settings.json"
fi

# Prove it rather than announce it.
exec "$0" --verify ${ROOM:+--room "$ROOM"} "$WT"
