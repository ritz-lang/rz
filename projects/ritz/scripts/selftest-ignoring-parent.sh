# Sourced by the regression harness self-tests -- AGAST #3180.
#
# call_ignoring MECH FN [ARGS...] -- call regression.sh's FN in a fresh bash
# that *started* with SIGHUP, SIGINT, SIGQUIT, SIGPIPE and SIGTERM ignored,
# the way a GitHub Actions job starts with SIGPIPE ignored.  It is not enough
# to `trap "" PIPE` in the calling shell: bash can undo an ignore it set
# itself (`trap -`), but not one it inherited, and only the latter is what CI
# does to the harness.
#
# MECH picks regression.sh's signal reset: "default" (what it probed), "env"
# or "perl" (SIGDFL_ENV / SIGDFL_PERL), or "none" (no reset, for proving the
# parent really ignores).  BUILD_DIR, RUN_SANDBOX, RUN_TIMEOUT and
# TEST_SCRIPT_TIMEOUT pass through.  Returns FN's status.
#
# Needs SCRIPT_DIR (the directory holding regression.sh).

call_ignoring() {
    local mech="$1"
    shift
    RITZ_REGRESSION_LIB_ONLY=1 \
    _CI_LIB="$SCRIPT_DIR/regression.sh" _CI_MECH="$mech" \
    _CI_BUILD="$BUILD_DIR" _CI_SANDBOX="${RUN_SANDBOX:-}" \
    _CI_RT="${RUN_TIMEOUT:-}" _CI_TST="${TEST_SCRIPT_TIMEOUT:-30}" \
    bash -c 'trap "" HUP INT QUIT PIPE TERM; exec bash -c "$1" _ "${@:2}"' _ '
        args=("$@")
        set --
        source "$_CI_LIB"
        trap - EXIT
        BUILD_DIR=$_CI_BUILD RUN_SANDBOX=$_CI_SANDBOX
        RUN_TIMEOUT=$_CI_RT TEST_SCRIPT_TIMEOUT=$_CI_TST
        case $_CI_MECH in
            env)  SIGDFL=("${SIGDFL_ENV[@]}") ;;
            perl) SIGDFL=("${SIGDFL_PERL[@]}") ;;
            none) SIGDFL=() ;;
        esac
        "${args[@]}"' "$@"
}
