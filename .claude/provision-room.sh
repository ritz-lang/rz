#!/usr/bin/env bash
#
# Provision a freshly-created task-room worktree so a HEADLESS Adele agent can
# work in it without stalling on a permission prompt nobody is there to answer.
#
#   .claude/provision-room.sh <worktree-path>
#   .claude/provision-room.sh --verify <worktree-path>   # check only, no writes
#   .claude/provision-room.sh --remove <worktree-path>   # drop trust entry (reap)
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
# hasTrustDialogAccepted: true.  Every worktree we spawn starts without it.
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

MODE=apply
case "${1:-}" in
    --verify) MODE=verify; shift ;;
    --remove) MODE=remove; shift ;;
esac

if [[ $# -ne 1 ]]; then
    echo "usage: $0 [--verify|--remove] <worktree-path>" >&2
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

# Tools a headless room must never block on.  Bare names only — see fact (a).
#
# Bash is already allowed at the user level, but it is repeated here so the
# room's permission surface is readable in one file instead of inferred from
# two.  Read/Glob/Grep are read-only tiers adele auto-approves anyway; they are
# listed for the same reason.
read -r -d '' ALLOW_JSON <<'EOF' || true
{
  "_comment": "Written by .claude/provision-room.sh — see that file for why these are bare tool names. Machine-local; gitignored. AGAST #1378.",
  "permissions": {
    "allow": ["Write", "Edit", "NotebookEdit", "Read", "Glob", "Grep", "Bash"]
  }
}
EOF

trusted() {
    python3 - "$WT" <<'PY'
import json, pathlib, sys
wt = sys.argv[1]
p = pathlib.Path.home() / '.claude.json'
try:
    d = json.loads(p.read_text())
except Exception:
    sys.exit(1)
sys.exit(0 if d.get('projects', {}).get(wt, {}).get('hasTrustDialogAccepted') is True else 1)
PY
}

if [[ $MODE == remove ]]; then
    python3 - "$WT" <<'PY'
import json, pathlib, sys
wt = sys.argv[1]
p = pathlib.Path.home() / '.claude.json'
d = json.loads(p.read_text())
gone = d.get('projects', {}).pop(wt, None)
p.write_text(json.dumps(d, indent=2))
print(f"  {'dropped' if gone is not None else 'no'} trust entry for {wt}")
PY
    exit 0
fi

if [[ $MODE == verify ]]; then
    rc=0
    if trusted; then
        echo "  ✓ workspace trusted in ~/.claude.json: $WT"
    else
        echo "  ✗ workspace NOT trusted — project permissions will be IGNORED: $WT" >&2
        rc=1
    fi
    if [[ -f "$SETTINGS" ]] && python3 -c "
import json,sys
allow = json.load(open('$SETTINGS')).get('permissions', {}).get('allow', [])
sys.exit(0 if 'Write' in allow else 1)"; then
        echo "  ✓ bare 'Write' allow entry present: $SETTINGS"
    else
        echo "  ✗ $SETTINGS missing a bare 'Write' allow entry" >&2
        rc=1
    fi
    [[ $rc -eq 0 ]] && echo "  room permissions OK — a headless Write will not block"
    exit $rc
fi

# --- apply ------------------------------------------------------------------

# Trust the workspace.  Read-modify-write via python so we never mangle the
# rest of ~/.claude.json (it holds auth and per-project history).
python3 - "$WT" <<'PY'
import json, pathlib, sys
wt = sys.argv[1]
p = pathlib.Path.home() / '.claude.json'
d = json.loads(p.read_text())
entry = d.setdefault('projects', {}).setdefault(wt, {})
entry['hasTrustDialogAccepted'] = True
p.write_text(json.dumps(d, indent=2))
print(f"  trusted workspace: {wt}")
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
exec "$0" --verify "$WT"
