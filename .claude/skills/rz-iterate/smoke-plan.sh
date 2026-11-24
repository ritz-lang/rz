#!/usr/bin/env bash
#
# Subsystem smoke check: what a room runs before it REAPs (AGAST #4580 item
# 9; Aaron, 2026-11-23: "Instead of completely ungated, we should smoke test
# the subsystems we've changed.  The whole gate gets run on the whole train
# before merging, to keep the main branch stable.").  One script, so a room
# and rz agree on what "the subsystems changed" means.
#
#   smoke-plan.sh plan [<rev-range>]    the targets for the diff, one per
#                                       line: `<target>\t<command>`
#   smoke-plan.sh run [<rev-range>]     run them, every one in full (not a
#                                       fail-fast subset: #4450 ran 59 files
#                                       of ~24k tests and cost two trains),
#                                       then print the REAP quote as the
#                                       last line; exits 0 only if all pass
#   smoke-plan.sh check <sha> <quote>   rz's REAP check (SKILL.md Reaping
#                                       step 2): 0 if <quote> covers <sha>
#
# <rev-range> defaults to HEAD^..HEAD: a room's one squashed commit.  A
# range is anything `git diff --name-only` takes (A..B, A B, <sha>^!).
#
# The REAP quote (machine-checkable):
#   smoke <sha12> [<target> <target> ...] EXIT=<rc>
# <sha12> is HEAD when `run` started; `run` refuses a dirty tree and
# reports EXIT=99 if HEAD moved, as run-gate.sh does.  `check` also accepts
# a full gate quote, `gate <log> SHA=<12> EXIT=0` (or the terminal
# `EXIT=2 budget-only: ...` verdict), since a full gate covers any diff, and
# rz's interim hand-written form of 2026-11-23, `verified
# <t1>+<t2>+... on <base12> (unit: <N> passed, 0 failed)`: it names no SHA
# or exit, so only its targets (and any "N failed" being 0) are checked.
#
# Paths -> targets (first match per path; every diff also runs `smoke`):
#   *.md, docs/**                        doc-only: no target (smoke alone),
#     except projects/ritz/**.md         doc-examples
#   projects/ritz/ritz0/**, ritz1/**,
#     grammars/**, runtime/**            tools-ratchets unit ritz1-bootstrap
#                                        matrix (the compiler set rz briefs,
#                                        2026-11-23; tools-ratchets is the
#                                        tools/ tests that read compiler
#                                        sources plus ritz0's in-process
#                                        tests (`-m inproc`), `make
#                                        tools-ratchets`, ~1 min: #4587 and
#                                        #4622, trains went red on one of
#                                        each; full tools-unit is 4-6 min)
#   projects/ritz/ritzlib/**             ritzlib matrix
#   projects/ritz/test/**                ritz-tests matrix
#   projects/ritz/examples/**            examples
#   projects/ritz/tools/**               tools-unit
#   projects/ritz/scripts/**             harness-selftest
#   projects/ritz/<anything else>        unit tools-unit (build.py & co.)
#   projects/<pkg>/**                    pkg:<pkg>  (./rz build + ./rz test)
#   .claude/**                           tools-unit (tools/ tests read
#                                        SKILL.md, hooks and settings), plus:
#   .claude/skills/<skill>/**            skill:<skill> (shellcheck -S error,
#                                        then every test-*.sh in it; a
#                                        test-*-systemd.sh through
#                                        .claude/room-unit.sh)
#   .claude/host-env.sh                  skill:rz-iterate (train.sh sources it)
#   rz, rz.toml                          build-all
#   anything else (.github, known-failures)  smoke alone; the
#                                        train's full gate covers it
# tools-unit and unit together subsume tools-ratchets (tools/ and all of
# ritz0): a diff that plans both runs only tools-unit.  Every path that plans
# tools-ratchets also plans unit, so tools-unit alone is the test.
#
# Env (tests): RZ_SMOKE_RUNNER, a program run as `<runner> <target>
# <command>` instead of `bash -c <command>`.
set -uo pipefail

die() { echo "error: $*" >&2; exit 2; }

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not in a git tree"

# cmd_of <target>: the command, run from the repo root.
cmd_of() {
    case "$1" in
        smoke)            echo "make -C projects/ritz smoke" ;;
        unit)             echo "make -C projects/ritz unit" ;;
        ritz1-bootstrap)  echo "make -C projects/ritz ritz1-bootstrap" ;;
        matrix)           echo "make -C projects/ritz matrix-quick" ;;
        tools-unit)       echo "make -C projects/ritz tools-unit" ;;
        tools-ratchets)   echo "make -C projects/ritz tools-ratchets" ;;
        harness-selftest) echo "make -C projects/ritz harness-selftest" ;;
        doc-examples)     echo "make -C projects/ritz check-doc-examples" ;;
        ritzlib)          echo "./rz test ritz/ritzlib/tests" ;;
        ritz-tests)       echo "make -C projects/ritz ritz" ;;
        examples)         echo "make -C projects/ritz examples" ;;
        build-all)        echo "./rz build --all" ;;
        pkg:*)            echo "./rz build ${1#pkg:} && ./rz test ${1#pkg:}" ;;
        skill:*)          local d=".claude/skills/${1#skill:}"
                          # A test that starts real units (test-*-systemd.sh)
                          # runs through room-unit.sh: rooms may not call
                          # systemd-run directly (#1811, #3568).  TMPDIR goes
                          # with it: the units it starts don't share the
                          # room's private /tmp, so its mktemp must not use it.
                          echo "shellcheck -S error -x $d/*.sh && rc=0 && for t in $d/test-*.sh; do [ -e \"\$t\" ] || continue; case \"\$t\" in *-systemd.sh) bash .claude/room-unit.sh --pipe \${TMPDIR:+--setenv=TMPDIR=\$TMPDIR} -- bash \"\$PWD/\$t\" || rc=1 ;; *) bash \"\$t\" || rc=1 ;; esac; done && exit \$rc" ;;
        *)                die "unknown target $1" ;;
    esac
}

# targets_of <path>: the targets one changed path needs (see the header).
targets_of() {
    local p="$1" rest
    # Anything under .claude/ (markdown too) runs tools-unit: tools/ tests
    # read SKILL.md, the hooks and settings (AGAST #4580's first train
    # failed on two that assert the briefing's text).  Checked before the
    # *.md rule below, which would otherwise make SKILL.md smoke-only.
    case "$p" in
        .claude/*) echo tools-unit ;;
    esac
    case "$p" in
        projects/ritz/*.md|projects/ritz/docs/*)     # case globs: * crosses /
            echo doc-examples; return ;;
        .claude/skills/*/*)       rest="${p#.claude/skills/}"; echo "skill:${rest%%/*}" ;;
        .claude/host-env.sh)      echo skill:rz-iterate ;;
        *.md|docs/*) return ;;
        projects/ritz/ritz0/*|projects/ritz/ritz1/*|projects/ritz/grammars/*|projects/ritz/runtime/*)
                                  echo tools-ratchets; echo unit; echo ritz1-bootstrap; echo matrix ;;
        projects/ritz/ritzlib/*)  echo ritzlib; echo matrix ;;
        projects/ritz/test/*)     echo ritz-tests; echo matrix ;;
        projects/ritz/examples/*) echo examples ;;
        projects/ritz/tools/*)    echo tools-unit ;;
        projects/ritz/scripts/*)  echo harness-selftest ;;
        projects/ritz/*)          echo unit; echo tools-unit ;;
        projects/*/*)             rest="${p#projects/}"; echo "pkg:${rest%%/*}" ;;
        rz|rz.toml)               echo build-all ;;
    esac
}

# The fixed order targets run and are quoted in: cheap and broad first.
ORDER=(smoke doc-examples tools-unit tools-ratchets harness-selftest ritzlib ritz-tests examples unit ritz1-bootstrap matrix build-all)

# plan_targets <range...>: every target for the diff, smoke first, in ORDER,
# then pkg:/skill: targets sorted.
plan_targets() {
    local files t o extra=()
    local -A want=()
    files="$(git -C "$ROOT" diff --name-only "$@")" || die "bad range: $*"
    want[smoke]=1
    while IFS= read -r f; do
        [[ -n "$f" ]] || continue
        while IFS= read -r t; do [[ -n "$t" ]] && want[$t]=1; done < <(targets_of "$f")
    done <<<"$files"
    # tools-unit runs all of tools/ (#4587); unit, always planned with
    # tools-ratchets, runs all of ritz0, its -m inproc half included (#4622).
    [[ -z "${want[tools-unit]:-}" ]] || unset 'want[tools-ratchets]'
    for o in "${ORDER[@]}"; do [[ -n "${want[$o]:-}" ]] && echo "$o"; done
    for t in "${!want[@]}"; do case "$t" in pkg:*|skill:*) extra+=("$t") ;; esac; done
    [[ ${#extra[@]} -eq 0 ]] || printf '%s\n' "${extra[@]}" | sort
}

range_args() { if [[ $# -eq 0 ]]; then echo "HEAD^" "HEAD"; else echo "$@"; fi; }

cmd_plan() {
    local t
    # shellcheck disable=SC2046  # range words
    while IFS= read -r t; do printf '%s\t%s\n' "$t" "$(cmd_of "$t")"; done \
        < <(plan_targets $(range_args "$@"))
}

cmd_run() {
    local head t rc=0 r names=() failed=()
    git -C "$ROOT" diff --quiet HEAD -- && git -C "$ROOT" diff --cached --quiet HEAD -- \
        || die "uncommitted changes: commit (squash) first, so the quote names what ran"
    head="$(git -C "$ROOT" rev-parse HEAD)"
    # shellcheck disable=SC2046
    mapfile -t names < <(plan_targets $(range_args "$@"))
    echo "smoke-plan: ${head:0:12}: ${names[*]}" >&2
    for t in "${names[@]}"; do
        echo "=== [$t] $(cmd_of "$t")" >&2
        if [[ -n "${RZ_SMOKE_RUNNER:-}" ]]; then
            (cd "$ROOT" && "$RZ_SMOKE_RUNNER" "$t" "$(cmd_of "$t")"); r=$?
        else
            (cd "$ROOT" && bash -c "$(cmd_of "$t")"); r=$?
        fi
        echo "=== [$t] EXIT=$r" >&2
        if [[ $r -ne 0 ]]; then failed+=("$t"); [[ $rc -ne 0 ]] || rc=$r; fi
    done
    [[ "$(git -C "$ROOT" rev-parse HEAD)" == "$head" ]] || { rc=99; echo "HEAD moved during the run" >&2; }
    [[ ${#failed[@]} -eq 0 ]] || echo "FAILED: ${failed[*]}" >&2
    echo "smoke ${head:0:12} [${names[*]}] EXIT=$rc"
    return $rc
}

# cmd_check <sha> <quote...>: does the REAP quote cover <sha>?
cmd_check() {
    [[ $# -ge 2 ]] || die "usage: $0 check <sha> <quote>"
    local sha q got want missing=() t
    sha="$(git -C "$ROOT" rev-parse -q --verify "$1^{commit}")" || { echo "REFUSED: no such commit $1"; return 1; }
    shift; q="$*"
    if [[ "$q" =~ ^gate\ [^\ ]+\ SHA=([0-9a-f]{7,40})\ EXIT=(0|2\ budget-only:.*)$ ]]; then
        [[ "$sha" == "${BASH_REMATCH[1]}"* ]] || { echo "REFUSED: gate quote is for ${BASH_REMATCH[1]}, not ${sha:0:12}"; return 1; }
        echo "OK full gate ${sha:0:12}"; return 0
    fi
    if [[ "$q" =~ ^verified\ ([a-z0-9:+_-]+)\ on\ [0-9a-f]{7,40}(\ \((.*)\))?$ ]]; then
        local tl="${BASH_REMATCH[1]}" paren="${BASH_REMATCH[3]}"
        if [[ "$paren" =~ ([0-9]+)\ failed ]] && [[ "${BASH_REMATCH[1]}" != 0 ]]; then
            echo "REFUSED: verified line reports failures: $paren"; return 1
        fi
        got=" ${tl//+/ } "
        want="$(plan_targets "$sha^!")"
        while IFS= read -r t; do [[ "$got" == *" $t "* ]] || missing+=("$t"); done <<<"$want"
        [[ ${#missing[@]} -eq 0 ]] || { echo "REFUSED: verified line for ${sha:0:12} misses ${missing[*]}"; return 1; }
        echo "OK verified (interim form) ${sha:0:12}"; return 0
    fi
    if [[ ! "$q" =~ ^smoke\ ([0-9a-f]{7,40})\ \[([^]]*)\]\ EXIT=([0-9]+)$ ]]; then
        echo "REFUSED: not a smoke quote (smoke <sha12> [<targets>] EXIT=0) or gate quote: $q"; return 1
    fi
    [[ "$sha" == "${BASH_REMATCH[1]}"* ]] || { echo "REFUSED: smoke quote is for ${BASH_REMATCH[1]}, not ${sha:0:12}"; return 1; }
    [[ "${BASH_REMATCH[3]}" == 0 ]] || { echo "REFUSED: smoke EXIT=${BASH_REMATCH[3]}"; return 1; }
    got=" ${BASH_REMATCH[2]} "
    want="$(plan_targets "$sha^!")"
    while IFS= read -r t; do [[ "$got" == *" $t "* ]] || missing+=("$t"); done <<<"$want"
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "REFUSED: smoke quote for ${sha:0:12} misses ${missing[*]} (the plan: $(tr '\n' ' ' <<<"$want"| sed 's/ $//'))"; return 1
    fi
    echo "OK smoke ${sha:0:12} [$(tr '\n' ' ' <<<"$want" | sed 's/ $//')]"
}

case "${1:-}" in
    plan)  shift; cmd_plan "$@" ;;
    run)   shift; cmd_run "$@" ;;
    check) shift; cmd_check "$@" ;;
    *)     die "usage: $0 plan|run [<rev-range>] | check <sha> <quote>" ;;
esac
