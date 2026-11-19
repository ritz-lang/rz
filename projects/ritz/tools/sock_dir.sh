# sock_dir.sh - a fresh dir for unix sockets (AGAST #4135, #4274, #4282)
#
# Source it:  . "$REPO/projects/ritz/tools/sock_dir.sh"
#
#   SOCK_DIR="$(sock_dir rz_bench_sock. zeus_bench_inmem.sock)" || exit 1
#
# sock_dir PREFIX NAME prints a new `mktemp -d` dir, PREFIX + 8 random chars,
# where NAME (the longest socket name the caller will bind) fits sun_path:
# 108 bytes with the NUL, so 107 usable. Past that, bind() fails and a
# harness only sees "socket never appeared". The caller removes the dir.
#
# Candidates, in order; the first where the path fits AND mktemp succeeds:
#   $TMPDIR           the run's own, if short enough (a gate's sits deep in
#                     its worktree and usually is not);
#   $XDG_RUNTIME_DIR  /run/user/<uid>, short and per-user;
#   /tmp              last ($SOCK_DIR_LAST overrides it, for tests only).
# Unset, empty and relative candidates are skipped. A failed mktemp (a full
# /tmp: ENOSPC on every gate, bangerang 2026-11-19) moves on to the next.
# With none left it fails (status 1), naming each candidate and why.
#
# Sourced by bench/run.sh, nexus/test/e2e_large_page.sh and
# harland/tools/test_tier1_boot.sh; the one copy (#4282).
# smoke_stack's harness.short_sock_dir is the Python twin; both are pinned
# row for row by projects/ritz/tools/test_harness_sock_path.py.

SOCK_DIR_SUN_PATH_MAX=107

sock_dir() {
    # LC_ALL=C: ${#x} counts bytes, as sun_path does, not characters.
    local prefix="$1" name="$2" cand d why="" LC_ALL=C
    for cand in "${TMPDIR:-}" "${XDG_RUNTIME_DIR:-}" "${SOCK_DIR_LAST:-/tmp}"; do
        if [[ "$cand" != /* ]]; then
            [[ -n "$cand" ]] && why+=" $cand (relative);"
            continue
        fi
        cand="${cand%/}"
        # <cand>/<prefix>XXXXXXXX/<name>
        if (( ${#cand} + 1 + ${#prefix} + 8 + 1 + ${#name} > SOCK_DIR_SUN_PATH_MAX )); then
            why+=" $cand (too long);"
            continue
        fi
        if d="$(mktemp -d "$cand/${prefix}XXXXXXXX" 2>/dev/null)"; then
            printf '%s\n' "$d"
            return 0
        fi
        why+=" $cand (mktemp failed);"
    done
    echo "sock_dir: no socket dir for $name:${why%;}" >&2
    return 1
}
