#!/usr/bin/env bash
#
# Subsystem smoke check: what a room runs before it REAPs (AGAST #4580 item
# 9; Aaron, 2026-11-23: "Instead of completely ungated, we should smoke test
# the subsystems we've changed.  The whole gate gets run on the whole train
# before merging, to keep the main branch stable.").  One script, so a room
# and rz agree on what "the subsystems changed" means.
#
#   smoke-plan.sh plan [<rev-range>] [+<target>...]
#                                       the targets for the diff, one per
#                                       line: `<target>\t<command>`; each
#                                       +<target> is an extra the room adds
#                                       (ROOM.md step 6), after the plan's
#   smoke-plan.sh run [<rev-range>] [+<target>...]
#                                       run them, every one in full (not a
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
# Paths -> targets (first match per path; every diff also runs `smoke` and
# `tools-ratchets`, below):
#   *.md, docs/**                        doc-only: no target of its own,
#     except projects/ritz/**.md         doc-examples
#     and docs/LANGUAGE_SPEC.md          doc-examples build-all-ritz1
#   projects/ritz/ritz0/**, grammars/**,
#     runtime/**                         unit ritz1-bootstrap matrix (the
#                                        compiler set rz briefs, 2026-11-23)
#                                        build-all-ritz1
#   projects/ritz/ritz1/test/**          the compiler set, ritz1-unit
#   projects/ritz/ritz1/** (the rest)    the compiler set, ritz1-unit,
#                                        build-all-ritz1
#   projects/ritz/ritzlib/**             ritzlib matrix build-all-ritz1
#   projects/ritz/test/**                ritz-tests matrix
#   projects/ritz/examples/**            examples
#   projects/ritz/tools/**               tools-unit
#   projects/ritz/scripts/**             harness-selftest
#   projects/ritz/<anything else>        unit tools-unit (build.py & co.)
#   projects/builder/**                  builder (projects/builder/test.sh:
#                                        the image build and its in-container
#                                        checks; no ritz.toml, AGAST #4822)
#   projects/harland/**                  unit as well as the package rule
#                                        below (AGAST #4898: train 0000283f
#                                        went red after #4882 changed
#                                        kernel/src/drivers/virtio/blk.ritz,
#                                        which ritz0/tests/test_harland_*.py
#                                        compile; they read kernel/src, boot,
#                                        the *_abi trees, tools, build.py and
#                                        ritz.toml, so every harland path)
#   projects/<pkg>/**                    ritz1-bootstrap pkg:<pkg>  (./rz
#                                        build under ritz0, ritz1 and
#                                        ritz1_selfhosted, then ./rz test),
#                                        plus pkg:<pkg>/<sub> for a nested
#                                        package (its own ritz.toml, not in
#                                        rz.toml's [workspace.exclude])
#     but a top-level package that       ritz1-bootstrap entry:<pkg>  (`make
#     [workspace.exclude] names          -C projects/<pkg> test`, its
#                                        dedicated entry: buddhafinger is
#                                        ritz1_selfhosted only, #4813)
#   .claude/**                           tools-unit (tools/ tests read
#                                        SKILL.md, hooks and settings), plus:
#   .claude/skills/<skill>/**            skill:<skill> (shellcheck -S error,
#                                        then every test-*.sh in it; a
#                                        test-*-systemd.sh through
#                                        .claude/room-unit.sh)
#   .claude/host-env.sh                  skill:rz-iterate (train.sh sources it)
#   any path a projects/ritz/tools/      ci:<file>, as well as the above
#     test_ci_*.py names (outside        (that one pin under xdist; AGAST
#     projects/ritz/tools/)              #4752: train e0f78f1e went red on
#                                        test_ci_msix_boot.py after a car
#                                        changed test_msix_boot.sh, which
#                                        planned pkg:harland alone)
#   rz, rz.toml                          build-all
#   anything else (.github, known-failures)  nothing of its own; the
#                                        train's full gate covers it
# tools-ratchets, every diff (AGAST #4672): the guards and ratchets, `make
# tools-ratchets` (the tools/ tests that read compiler sources plus ritz0's
# in-process tests, `-m inproc`), ~15 s.  Trains went red on ratchets a car's
# smoke never ran: #4587 and #4622 for compiler changes, then #4653 and
# #4654 on test_standard_callers.py, whose cars ran tools-ratchets without
# it.  The train conductor runs the same target on the train tip before it
# gates (train.sh precheck).  tools-unit and unit together subsume it
# (tools/ and all of ritz0): a diff that plans both runs only those; either
# alone does not.  So every plan holds tools-ratchets or tools-unit, and both
# run the tree guards (AGAST #4902): tracked *.orig/*.rej/*.old leftovers
# (test_project_root_hygiene.py) and ritz0/ritzlib orphans
# (test_check_liveness.py::test_real_tree_is_live).  #4773's car tracked
# ritz1/src/monomorph.ritz.orig; its ritz1-only smoke ran no tools-unit and
# the train gate was first to see it.  ~3.3 s of work in tools-ratchets'
# faster half.
#
# The floor, not the whole check (AGAST #4777, ROOM.md step 6): a room adds
# targets for what its change can break beyond the files it touched, and
# `check` accepts the extras.  Two trains went red on cars whose smoke
# passed: #4772 changed ritz1/src and broke a ritz1/test suite (ritz1-unit,
# `make ritz1-unit`, planned by nothing), and #4739 changed a package only
# ritz1 refused (pkg: built it with ritz0 alone).  Hence ritz1-unit for
# ritz1/**, pkg: under all three compilers, and build-all-ritz1 (`make
# build-all-ritz1`: every package under ritz1 and ritz1_selfhosted, the
# gate's step) for a compiler or language change.  Measured on starbux
# (2026-11-26; the ticket named omegalisk, this room ran on starbux), ritz1
# already bootstrapped (~2 min cold): ritz1-unit ~5 s; build-all-ritz1
# ~142 s first, ~49 s warm; pkg:harland ~11 s and pkg:harland/netstack ~6 s
# under all three compilers.  Each was red on its failure and green on its
# fix: ritz1-unit on #4772's car e0310a8e5 / e61f32567, and
# pkg:harland/netstack and build-all-ritz1 on 25d60cd90 / 67c23c597ea6
# (#4739's arp.ritz broke only with #4758's ritz1 on the train: its own car
# built clean under ritz1, so #4758's car is the one build-all-ritz1 flags).
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
        ritz1-unit)       echo "make -C projects/ritz ritz1-unit" ;;
        ritzlib-ritz1)    echo "make -C projects/ritz ritzlib-tests-ritz1" ;;
        build-all)        echo "./rz build --all" ;;
        build-all-ritz1)  echo "make -C projects/ritz build-all-ritz1" ;;
        builder)          echo "bash projects/builder/test.sh" ;;
        # One CI pin: tools-unit's invocation, on that file alone.
        ci:*)             echo "cd projects/ritz && python3 -m pytest -q -n 8 --dist loadgroup tools/${1#ci:}" ;;
        # The package under every compiler the gate builds it with (#4777:
        # #4739's package built under ritz0 and only ritz1 refused it), all
        # three in full, then its tests.  A compiler whose known-failures/
        # `build` entries excuse the package is skipped, as `rz build --all`
        # excuses it; the plan's ritz1-bootstrap built the compilers first.
        # An excluded top-level package's own gate (#4813): pkg:'s
        # three-compiler build is the sweep its exclusion keeps it out of.
        entry:*)          echo "make -C projects/${1#entry:} test" ;;
        pkg:*)            local p="${1#pkg:}"
                          echo "rc=0; for c in ritz0 ritz1 ritz1_selfhosted; do if python3 projects/ritz/tools/known_failures.py list --gate build --compiler \$c | cut -f1 | grep -qxF '$p'; then echo \"$p: build under \$c excused by known-failures/\"; else ./rz build $p --compiler \$c || rc=1; fi; done; ./rz test $p || rc=1; exit \$rc" ;;
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

# pkg_of <path>: `pkg:<id>` for the nearest package below projects/<top>/
# that holds <path>, if it is not <top> itself (#4777: #4739 changed
# harland/netstack, which harland's build never compiles).  A package is a
# dir with a ritz.toml in plan_targets' MANIFESTS, not one rz.toml excludes
# (harland/boot: harland builds it), or anything under one.
pkg_of() {
    local d="${1%/*}" rest="${1#projects/}" top e
    top="projects/${rest%%/*}"
    while [[ "$d" == "$top"/* ]]; do
        if grep -qxF -- "$d" <<<"$MANIFESTS"; then
            while IFS= read -r e; do
                [[ -n "$e" && ( "$d" == "$e" || "$d" == "$e"/* ) ]] && return 0
            done <<<"$EXCLUDED"
            echo "pkg:${d#projects/}"; return 0
        fi
        d="${d%/*}"
    done
}

# pins_of <path>: `ci:<file>` for each projects/ritz/tools/test_ci_*.py in
# the planned tree that names <path> (a tools/ path is tools-unit's, which
# runs every pin).
pins_of() {
    local f
    [[ "$1" != projects/ritz/tools/* ]] || return 0
    git -C "$ROOT" grep -lF -- "$1" "$TIP" -- 'projects/ritz/tools/test_ci_*.py' 2>/dev/null \
        | while IFS= read -r f; do echo "ci:${f##*/}"; done
}

# targets_of <path>: the targets one changed path needs (see the header).
targets_of() {
    local p="$1" rest
    pins_of "$p"
    # Anything under .claude/ (markdown too) runs tools-unit: tools/ tests
    # read SKILL.md, the hooks and settings (AGAST #4580's first train
    # failed on two that assert the briefing's text).  Checked before the
    # *.md rule below, which would otherwise make SKILL.md smoke-only.
    case "$p" in
        .claude/*) echo tools-unit ;;
    esac
    case "$p" in
        projects/ritz/docs/LANGUAGE_SPEC.md)
            echo doc-examples; echo build-all-ritz1; return ;;
        projects/ritz/*.md|projects/ritz/docs/*)     # case globs: * crosses /
            echo doc-examples; return ;;
        .claude/skills/*/*)       rest="${p#.claude/skills/}"; echo "skill:${rest%%/*}" ;;
        .claude/host-env.sh)      echo skill:rz-iterate ;;
        *.md|docs/*) return ;;
        projects/ritz/ritz1/test/*)
                                  echo unit; echo ritz1-bootstrap; echo ritz1-unit; echo matrix ;;
        projects/ritz/ritz1/*)    echo unit; echo ritz1-bootstrap; echo ritz1-unit; echo matrix; echo build-all-ritz1 ;;
        projects/ritz/ritz0/*|projects/ritz/grammars/*|projects/ritz/runtime/*)
                                  echo unit; echo ritz1-bootstrap; echo matrix; echo build-all-ritz1 ;;
        projects/ritz/ritzlib/*)  echo ritzlib; echo matrix; echo build-all-ritz1 ;;
        projects/ritz/test/*)     echo ritz-tests; echo matrix ;;
        projects/ritz/examples/*) echo examples ;;
        projects/ritz/tools/*)    echo tools-unit ;;
        projects/ritz/scripts/*)  echo harness-selftest ;;
        projects/ritz/*)          echo unit; echo tools-unit ;;
        projects/builder/*)       echo builder ;;
        projects/*/*)             rest="${p#projects/}"; echo ritz1-bootstrap
                                  # ritz0's test_harland_*.py compile and
                                  # read harland's trees (#4898).
                                  [[ "$p" != projects/harland/* ]] || echo unit
                                  if grep -qxF -- "projects/${rest%%/*}" <<<"$EXCLUDED"; then
                                      echo "entry:${rest%%/*}"; return
                                  fi
                                  echo "pkg:${rest%%/*}"
                                  pkg_of "$p" ;;
        rz|rz.toml)               echo build-all ;;
    esac
}

# The fixed order targets run and are quoted in: cheap and broad first.
ORDER=(smoke doc-examples tools-unit tools-ratchets harness-selftest ritzlib ritz-tests examples unit ritz1-bootstrap ritz1-unit matrix build-all build-all-ritz1 builder)

# plan_targets <range...>: every target for the diff, smoke first, in ORDER,
# then ci:/entry:/pkg:/skill: targets sorted.
plan_targets() {
    local files t o extra=() tip last
    local -A want=()
    files="$(git -C "$ROOT" diff --name-only "$@")" || die "bad range: $*"
    # The commit whose tree says where packages are (pkg_of): the range's
    # far end, so rz's `check <sha>` and the room's `run` agree.
    last="${*: -1}"
    case "$last" in
        *^!) tip="${last%^!}" ;;
        *..*) tip="${last##*..}"; tip="${tip:-HEAD}" ;;
        *)   if [[ $# -ge 2 ]]; then tip="$last"; else tip=HEAD; fi ;;
    esac
    # Read by pkg_of and pins_of (bash's dynamic scope reaches targets_of's
    # subshells).
    local MANIFESTS EXCLUDED TIP="$tip"
    MANIFESTS="$(git -C "$ROOT" ls-tree -r --name-only "$tip" -- projects 2>/dev/null | sed -n 's#/ritz\.toml$##p')"
    EXCLUDED="$(git -C "$ROOT" show "$tip:rz.toml" 2>/dev/null \
        | sed -n '/^\[workspace\.exclude\]/,/^\[[a-z]/s/^"\([^"]*\)" *=.*/\1/p')"
    want[smoke]=1
    want[tools-ratchets]=1
    while IFS= read -r f; do
        [[ -n "$f" ]] || continue
        while IFS= read -r t; do [[ -n "$t" ]] && want[$t]=1; done < <(targets_of "$f")
    done <<<"$files"
    # tools-unit runs all of tools/ (#4587) and unit all of ritz0, its
    # -m inproc half included (#4622): both, and the ratchets are covered.
    [[ -z "${want[tools-unit]:-}" || -z "${want[unit]:-}" ]] || unset 'want[tools-ratchets]'
    for o in "${ORDER[@]}"; do [[ -n "${want[$o]:-}" ]] && echo "$o"; done
    for t in "${!want[@]}"; do case "$t" in entry:*|pkg:*|skill:*|ci:*) extra+=("$t") ;; esac; done
    [[ ${#extra[@]} -eq 0 ]] || printf '%s\n' "${extra[@]}" | sort
}

range_args() { if [[ $# -eq 0 ]]; then echo "HEAD^" "HEAD"; else echo "$@"; fi; }

# all_targets [<rev-range>] [+<target>...]: the plan (the floor), then each
# `+<target>` the room added by judgment (ROOM.md step 6) that the plan
# lacks, in the order given.  An unknown extra is an error, not a skip.
all_targets() {
    local a range=() extras=() planned t
    for a in "$@"; do
        case "$a" in +*) extras+=("${a#+}") ;; *) range+=("$a") ;; esac
    done
    # shellcheck disable=SC2046  # range words
    planned="$(plan_targets $(range_args "${range[@]}"))" || exit 2
    echo "$planned"
    for t in "${extras[@]}"; do
        cmd_of "$t" >/dev/null || exit 2
        grep -qxF -- "$t" <<<"$planned" && continue
        planned+=$'\n'"$t"; echo "$t"
    done
}

cmd_plan() {
    local t names
    names="$(all_targets "$@")" || exit 2
    while IFS= read -r t; do printf '%s\t%s\n' "$t" "$(cmd_of "$t")"; done <<<"$names"
}

cmd_run() {
    local head t rc=0 r names=() failed=()
    git -C "$ROOT" diff --quiet HEAD -- && git -C "$ROOT" diff --cached --quiet HEAD -- \
        || die "uncommitted changes: commit (squash) first, so the quote names what ran"
    head="$(git -C "$ROOT" rev-parse HEAD)"
    r="$(all_targets "$@")" || exit 2
    mapfile -t names <<<"$r"
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
