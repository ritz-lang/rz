#!/usr/bin/env bash
#
# Which Claude account a ritz task room runs on (AGAST #4699).
#
#   .claude/room-account.sh <room>              the room's account env, as lines
#                                               (KEY=VALUE set, `-KEY` unset);
#                                               may print a token: host-local use only
#   .claude/room-account.sh --describe <room>   one line, no secret: which account
#                                               the room would authenticate as
#   .claude/room-account.sh --config-dir <room> the CLAUDE_CONFIG_DIR the room runs
#                                               under: a dir, `default` (unset, so
#                                               ~/.claude and ~/.claude.json), or
#                                               `inherit` (no RZ_ROOM_ACCOUNTS)
#   .claude/room-account.sh --install <room>    write the room's unit drop-in;
#                                               before `systemctl start`
#   .claude/room-account.sh --verify <room>     the drop-in is what --install writes
#   .claude/room-account.sh --remove <room>     drop it (teardown)
#
#   <room> is `ritz-task-<id>` or a bare <id>; <id> % N picks the account.
#
# Env overrides (tests): RZ_HOST_ENV           (default ~/.config/rz/host.env)
#                        RZ_SYSTEMD_USER_DIR   (default ~/.config/systemd/user)
#                        RZ_ROOM_ACCOUNT_DIR   (default ~/.config/rz/room-accounts)
#                        RZ_CLAUDE_BIN         (default: claude on PATH or ~/.local/bin)
#
# ---------------------------------------------------------------------------
# THE HOST KEY
# ---------------------------------------------------------------------------
# ~/.config/rz/host.env (format: .claude/host-env.sh):
#
#   RZ_ROOM_ACCOUNTS=<acct0> <acct1> ...
#
# Room <id> runs on account <id> % N: with two accounts, even tickets get the
# first and odd tickets the second (Aaron, 2026-11-25).  Each <acct> is
#   default        ~/.claude: CLAUDE_CONFIG_DIR unset
#   /a/config/dir  that dir's stored login: CLAUDE_CONFIG_DIR=/a/config/dir
#   /an/env/file   a host-local file of CLAUDE_CODE_OAUTH_TOKEN= and/or
#                  CLAUDE_CONFIG_DIR= lines (a `claude setup-token` token);
#                  KEY=VALUE only, no quotes, no other keys
# No key: the room keeps the unit's environment (adele.env), as before #4699.
# Account names live in host.env only, never in this repo: a test keeps them
# out (projects/ritz/tools/test_room_account.py).
#
# ---------------------------------------------------------------------------
# WHY A DROP-IN AND NOT room.env  (measured on huburght, CLI 2.1.322, 2026-11-25)
# ---------------------------------------------------------------------------
# 1. Every room unit reads ~/.config/adele/adele.env, and on most hosts that
#    sets CLAUDE_CODE_OAUTH_TOKEN.  An env token beats any config dir's stored
#    login: `claude auth status` says authMethod "oauth_token" whatever
#    CLAUDE_CONFIG_DIR is.  So a room on a config-dir account must lose the
#    token.  `CLAUDE_CODE_OAUTH_TOKEN=` (empty) does fall back to the stored
#    login (authMethod "claude.ai"), but
# 2. `CLAUDE_CONFIG_DIR=` (empty) does NOT mean ~/.claude: the CLI reports
#    configDirectory '' and loggedIn false.  `default` has to UNSET it, and a
#    room.env line can only set.  systemd's UnsetEnvironment= can, and it
#    runs after every EnvironmentFile=.
# 3. `adele room spawn` rewrites room.env at install and starts the unit at
#    once, so nothing can be added to room.env before the first start.  A
#    drop-in installed beforehand, like 50-ritz-host-budget.conf and
#    60-rz-room-tmpdir.conf, is in place when the unit starts.
# Measured with a scratch unit reading an adele.env (token + dir) and a
# room.env (dir): the drop-in's EnvironmentFile= won over both, and its
# UnsetEnvironment= removed the variable outright.
#
# ---------------------------------------------------------------------------
# LOGGED OUT IS A REFUSAL
# ---------------------------------------------------------------------------
# A .credentials.json can exist with empty tokens (huburght, 2026-11-25), so
# its presence proves nothing.  The check is `claude auth status --json`
# under the room's own environment: loggedIn must be true, or the spawn is
# refused with one line before anything is written.  With an env token the
# CLI reports loggedIn without contacting the server (a bogus token passes),
# so for an env-file account the check proves a token is set, not that it
# is valid; nor does it name the account, so --describe names the file.
# (/api/oauth/profile can't fill the gap: it answers a setup token 403.)
#
# provision-room.sh --room <room> runs this script, so the room's trust and
# its allow list land in the same account's .claude.json the room reads.
set -euo pipefail
: "${HOME:=$(getent passwd "$(id -u)" | cut -d: -f6)}"
: "${PATH:=/usr/local/bin:/usr/bin:/bin}"
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
export HOME PATH XDG_RUNTIME_DIR
_d="${BASH_SOURCE[0]%/*}"; [[ "$_d" != "${BASH_SOURCE[0]}" ]] || _d=.
# shellcheck source=host-env.sh
source "$_d/host-env.sh"
unset _d

MODE=lines
case "${1:-}" in
    --describe) MODE=describe; shift ;;
    --config-dir) MODE=config-dir; shift ;;
    --install) MODE=install; shift ;;
    --verify) MODE=verify; shift ;;
    --remove) MODE=remove; shift ;;
esac
if [[ $# -ne 1 ]]; then
    echo "usage: $0 [--describe|--config-dir|--install|--verify|--remove] <ritz-task-<id> | <id>>" >&2
    exit 2
fi
if [[ "$1" =~ ^[0-9]+$ ]]; then
    ID="$1"; ROOM="ritz-task-$1"
elif [[ "$1" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]*-([0-9]+)$ ]]; then
    ID="${BASH_REMATCH[1]}"; ROOM="$1"
else
    echo "error: room must be <name>-<id> or <id>: '$1'" >&2
    exit 2
fi
ID=$((10#$ID))

UNITS="${RZ_SYSTEMD_USER_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}"
DROPIN_DIR="$UNITS/adele-agent@$ROOM.service.d"
DROPIN="$DROPIN_DIR/55-rz-room-account.conf"
ACCT_DIR="${RZ_ROOM_ACCOUNT_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/rz/room-accounts}"
ACCT_ENV="$ACCT_DIR/$ROOM.env"

# A teardown must work even with a broken host.env, a changed key or a
# logged-out account: it only deletes what --install wrote.
if [[ $MODE == remove ]]; then
    gone=0
    if [[ -e "$DROPIN" ]]; then
        rm -f "$DROPIN"
        rmdir "$DROPIN_DIR" 2>/dev/null || true
        gone=1
    fi
    rm -f "$ACCT_ENV"
    [[ $gone -eq 1 ]] && systemctl --user daemon-reload
    echo "room account removed for $ROOM"
    exit 0
fi

# --config-dir after install: the dir the room was provisioned under, from
# the drop-in, so a host.env edited since then can't send --remove/--verify
# to another account's .claude.json.
if [[ $MODE == config-dir && -f "$DROPIN" ]]; then
    recorded="$(sed -n 's/^# config-dir: //p' "$DROPIN" | head -n1)"
    if [[ -n "$recorded" ]]; then
        echo "$recorded"
        exit 0
    fi
fi

rz_host_env_load || exit 2
ACCOUNTS="${HOST_ENV[RZ_ROOM_ACCOUNTS]:-}"

if [[ -z "$ACCOUNTS" ]]; then
    case "$MODE" in
        lines) ;;   # nothing to change
        describe) echo "$ROOM: no RZ_ROOM_ACCOUNTS in $RZ_HOST_ENV_FILE; the unit's environment (adele.env) decides" ;;
        config-dir) echo inherit ;;
        verify)
            if [[ -e "$DROPIN" ]]; then
                echo "error: $DROPIN is installed but $RZ_HOST_ENV_FILE has no RZ_ROOM_ACCOUNTS; run: $0 --remove $ROOM" >&2
                exit 1
            fi
            echo "room account OK for $ROOM (no RZ_ROOM_ACCOUNTS: adele.env decides)" ;;
        install)
            if [[ -e "$DROPIN" ]]; then
                "$0" --remove "$ROOM" >/dev/null
            fi
            echo "room account for $ROOM: no RZ_ROOM_ACCOUNTS in $RZ_HOST_ENV_FILE; adele.env decides" ;;
    esac
    exit 0
fi

read -r -a ACCTS <<<"$ACCOUNTS"
N=${#ACCTS[@]}
K=$((ID % N))
SPEC="${ACCTS[$K]}"

# What the room's environment becomes: SET[key]=value, UNSET a list.
declare -A SET=()
UNSET=()
SRC_FILE=""   # an env-file account: the drop-in reads that file itself
KEYS=(CLAUDE_CODE_OAUTH_TOKEN CLAUDE_CONFIG_DIR)
if [[ "$SPEC" == default ]]; then
    UNSET=("${KEYS[@]}")
elif [[ -d "$SPEC" ]]; then
    SET[CLAUDE_CONFIG_DIR]="$SPEC"
    UNSET=(CLAUDE_CODE_OAUTH_TOKEN)
elif [[ -f "$SPEC" ]]; then
    SRC_FILE="$SPEC"
    # It holds a token: readable by its owner only, as `chmod 600` leaves it.
    if [[ "$(stat -c %a "$SPEC")" =~ [1-7][0-7]$|[1-7]$ ]]; then
        echo "error: $SPEC holds a token and is readable by others (mode $(stat -c %a "$SPEC")); chmod 600 it" >&2
        exit 2
    fi
    n=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        n=$((n + 1))
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" || "$line" == \#* ]] && continue
        if [[ ! "$line" =~ ^(CLAUDE_CODE_OAUTH_TOKEN|CLAUDE_CONFIG_DIR)=([^\"\'[:space:]]+)$ ]]; then
            # Never echo the line: it may hold a token.
            echo "error: $SPEC:$n: expected CLAUDE_CODE_OAUTH_TOKEN=<token> or CLAUDE_CONFIG_DIR=<dir>, no quotes" >&2
            exit 2
        fi
        SET[${BASH_REMATCH[1]}]="${BASH_REMATCH[2]}"
    done < "$SPEC"
    if [[ ${#SET[@]} -eq 0 ]]; then
        echo "error: $SPEC: sets neither CLAUDE_CODE_OAUTH_TOKEN nor CLAUDE_CONFIG_DIR" >&2
        exit 2
    fi
    for k in "${KEYS[@]}"; do
        [[ -n "${SET[$k]+x}" ]] || UNSET+=("$k")
    done
else
    echo "error: $RZ_HOST_ENV_FILE: RZ_ROOM_ACCOUNTS account $K '$SPEC' is not \`default\`, a dir or an env file" >&2
    exit 2
fi
CONFIG_DIR="${SET[CLAUDE_CONFIG_DIR]:-default}"
WHICH="account $K of $N ($SPEC)"

case "$MODE" in
config-dir)
    echo "$CONFIG_DIR"
    exit 0
    ;;
lines)
    for k in "${KEYS[@]}"; do
        if [[ -n "${SET[$k]+x}" ]]; then echo "$k=${SET[$k]}"; else echo "-$k"; fi
    done
    exit 0
    ;;
esac

# auth_status: `claude auth status --json` under exactly the room's env;
# prints "<loggedIn> <authMethod> <who>" (who: email, else org, else -).
auth_status() {
    local claude="${RZ_CLAUDE_BIN:-}" e=(env) k out
    if [[ -z "$claude" ]]; then
        claude="$(PATH="$PATH:$HOME/.local/bin" command -v claude)" || {
            echo "error: no claude CLI on PATH or in ~/.local/bin to check $ROOM's login" >&2
            return 1
        }
    fi
    for k in "${UNSET[@]}"; do e+=(-u "$k"); done
    for k in "${!SET[@]}"; do e+=("$k=${SET[$k]}"); done
    out="$(cd / && "${e[@]}" "$claude" auth status --json 2>/dev/null)" || true
    python3 -c '
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    print("false unreadable -"); sys.exit(0)
who = d.get("email") or d.get("orgName") or "-"
print("true" if d.get("loggedIn") is True else "false", d.get("authMethod") or "-", who.replace(" ", "_"))
' "$out"
}

if [[ $MODE == describe || $MODE == install ]]; then
    read -r logged method who < <(auth_status) || exit 1
    if [[ "$logged" != true ]]; then
        echo "error: $ROOM: $WHICH is not logged in (claude auth status: loggedIn=$logged, authMethod=$method); log it in or fix RZ_ROOM_ACCOUNTS in $RZ_HOST_ENV_FILE" >&2
        exit 1
    fi
    # A token names no account to the CLI: its file is the account's name.
    [[ "$who" == - && -n "${SET[CLAUDE_CODE_OAUTH_TOKEN]+x}" ]] && who="the token in $SRC_FILE"
    SUMMARY="$ROOM: $WHICH: config dir $CONFIG_DIR, logged in as $who ($method)"
    if [[ $MODE == describe ]]; then
        echo "$SUMMARY"
        exit 0
    fi
fi

# The drop-in.  EnvironmentFile= without `-`: a missing file fails the start
# rather than running the room on adele.env's account.
ENV_FILE="$SRC_FILE"
BODY="# Installed by .claude/room-account.sh (AGAST #4699). Do not edit by hand.
# Removed on reap with: .claude/room-account.sh --remove $ROOM
# $WHICH from $RZ_HOST_ENV_FILE RZ_ROOM_ACCOUNTS
# config-dir: $CONFIG_DIR
[Service]"
if [[ -z "$SRC_FILE" && -n "${SET[CLAUDE_CONFIG_DIR]+x}" ]]; then
    ENV_FILE="$ACCT_ENV"
fi
[[ -n "$ENV_FILE" ]] && BODY+=$'\n'"EnvironmentFile=$ENV_FILE"
BODY+=$'\n'"UnsetEnvironment=${UNSET[*]}"
ENV_BODY="CLAUDE_CONFIG_DIR=${SET[CLAUDE_CONFIG_DIR]:-}"

current() { [[ -f "$1" ]] && [[ "$(cat "$1")" == "$2" ]]; }

if [[ $MODE == verify ]]; then
    if ! current "$DROPIN" "$BODY" || { [[ "$ENV_FILE" == "$ACCT_ENV" ]] && ! current "$ACCT_ENV" "$ENV_BODY"; }; then
        echo "error: $ROOM's account drop-in is missing or stale ($DROPIN); run: $0 --install $ROOM" >&2
        exit 1
    fi
    echo "room account OK for $ROOM ($WHICH: config dir $CONFIG_DIR)"
    exit 0
fi

# install
changed=0
if [[ "$ENV_FILE" == "$ACCT_ENV" ]] && ! current "$ACCT_ENV" "$ENV_BODY"; then
    mkdir -p "$ACCT_DIR"
    (umask 077 && printf '%s\n' "$ENV_BODY" > "$ACCT_ENV.tmp")
    mv -f "$ACCT_ENV.tmp" "$ACCT_ENV"
fi
if [[ "$ENV_FILE" != "$ACCT_ENV" ]]; then
    rm -f "$ACCT_ENV"
fi
if ! current "$DROPIN" "$BODY"; then
    mkdir -p "$DROPIN_DIR"
    printf '%s\n' "$BODY" > "$DROPIN.tmp"
    mv -f "$DROPIN.tmp" "$DROPIN"
    changed=1
fi
[[ $changed -eq 1 ]] && systemctl --user daemon-reload
echo "room account for $SUMMARY"
