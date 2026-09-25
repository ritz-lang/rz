#!/bin/bash
# Self-test for server-example port isolation — AGAST #1535.
#
# 74_async_tiers, 75_tier2_uring and 76_tier3_http are servers.  They used to
# bind hard-coded ports (9001, 9002, 8080).  With several rooms gating on one
# host at once, the second regression.sh to reach 75_tier2_uring found 9002
# taken, printed "Failed to bind" and exited 0.  compare_runs saw "stage 1 ran
# forever, stage 3 terminated" and reported
#
#     ✗ 75_tier2_uring: termination behaviour changed (A non-terminating=1, B=0)
#
# That is a false red: the compiler did nothing wrong.  False reds teach people
# to rerun until green, which is how real reds get lost.
#
# The fix has two halves, and this file pins both:
#
#   1. Isolation.  regression.sh picks ONE free port per run and hands it to
#      every example as RITZ_EXAMPLE_PORT in the fixed `env -i` environment.
#      One value per run (not per stage), so 31_env/33_printenv still print
#      byte-identical output in every stage.  The server examples read it.
#
#   2. Classification.  If a bind fails anyway (port stolen between pick and
#      use, or someone runs an example by hand), run_binary marks the run as an
#      infrastructure error and compare_runs says so.  That verdict is
#      distinct from a termination change and is checked FIRST, so it can
#      never be reported as one.
#
# Hermetic: sources regression.sh as a library, compiles nothing, uses shell
# scripts as fake binaries, and runs in about a second.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

# regression.sh installs an EXIT trap that deletes the real .regression build
# dir, and run_binary builds its sandbox under BUILD_DIR.  Point both at
# scratch: a self-test must not be able to disturb a real run.
trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT
BUILD_DIR="$SCRATCH/build"
mkdir -p "$BUILD_DIR"

TESTS_RUN=0
TESTS_FAILED=0

check() {
    local desc="$1" want="$2" got="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$want" == "$got" ]]; then
        echo "ok: $desc"
        return 0
    fi
    echo "FAIL: $desc"
    echo "      want: $want"
    echo "      got:  $got"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    return 1
}

contains() { [[ "$1" == *"$2"* ]] && echo yes || echo no; }

# A fake binary: a shell script run_binary can exec under `env -i`.
fake_bin() {
    local path="$SCRATCH/$1"
    printf '#!/bin/sh\n%s\n' "$2" > "$path"
    chmod +x "$path"
    echo "$path"
}

echo "regression.sh server-port isolation self-test"
echo "============================================="

# ---------------------------------------------------------------------------
# 1. A per-run port exists, is sane, and is not one of the old fixed ports.
# ---------------------------------------------------------------------------
port="${REGRESSION_EXAMPLE_PORT:-}"
check "regression.sh chooses a per-run example port" yes \
    "$([[ "$port" =~ ^[0-9]+$ ]] && echo yes || echo no)"
check "the port is in the unprivileged, non-ephemeral range" yes \
    "$([[ "$port" =~ ^[0-9]+$ && $port -ge 20000 && $port -lt 32768 ]] && echo yes || echo no)"

p1=$(pick_example_port)
check "pick_example_port returns a port" yes \
    "$([[ "$p1" =~ ^[0-9]+$ ]] && echo yes || echo no)"

# A value handed in by the caller wins, so a human can reproduce a run.
over=$(RITZ_EXAMPLE_PORT=23456 RITZ_REGRESSION_LIB_ONLY=1 bash -c \
    "source '$SCRIPT_DIR/regression.sh'; trap - EXIT; echo \$REGRESSION_EXAMPLE_PORT")
check "RITZ_EXAMPLE_PORT from the caller overrides the pick" 23456 "$over"

# ---------------------------------------------------------------------------
# 2. run_binary hands the port to the program under test.
# ---------------------------------------------------------------------------
b=$(fake_bin echo_port 'echo "port=$RITZ_EXAMPLE_PORT"')
run_binary "$b" "$SCRATCH/p.out" "$SCRATCH/p.exit"
check "the program sees RITZ_EXAMPLE_PORT under env -i" \
    "port=$REGRESSION_EXAMPLE_PORT" "$(cat "$SCRATCH/p.out")"

# ---------------------------------------------------------------------------
# 3. The exact false red from the ticket: stage A ran forever, stage B could
#    not bind and exited 0.  Must be an infrastructure error, never a
#    termination change.
# ---------------------------------------------------------------------------
server=$(fake_bin server 'echo "listening"; exec sleep 30')
nobind=$(fake_bin nobind 'echo "Failed to bind"; exit 0')

run_binary "$server" "$SCRATCH/a.out" "$SCRATCH/a.exit"
check "a server killed by the timeout is marked non-terminating" yes \
    "$([[ -f "$SCRATCH/a.exit.nonterminating" ]] && echo yes || echo no)"

run_binary "$nobind" "$SCRATCH/b.out" "$SCRATCH/b.exit"
check "a bind failure is marked as an infrastructure error" yes \
    "$([[ -f "$SCRATCH/b.exit.infra" ]] && echo yes || echo no)"

out=$(compare_runs "75_tier2_uring" \
    "$SCRATCH/a.out" "$SCRATCH/a.exit" "$SCRATCH/b.out" "$SCRATCH/b.exit")
rc=$?
check "compare_runs does not pass a run that never really ran" 1 "$rc"
check "the verdict names an infrastructure error" yes \
    "$(contains "$out" "infrastructure error")"
check "the verdict is NOT a termination change" no \
    "$(contains "$out" "termination behaviour changed")"
check "the verdict says it is not a compiler result" yes \
    "$(contains "$out" "not a compiler result")"

# Symmetric: the failing side may be A (stage 1) just as well.
out=$(compare_runs "75_tier2_uring" \
    "$SCRATCH/b.out" "$SCRATCH/b.exit" "$SCRATCH/a.out" "$SCRATCH/a.exit")
check "an infra error on side A is reported the same way" yes \
    "$(contains "$out" "infrastructure error")"

# The "to port N" variant (50_http, 60_echo_server) is caught too.
nobind2=$(fake_bin nobind2 'echo "Failed to bind to port 8080"; exit 1')
run_binary "$nobind2" "$SCRATCH/c.out" "$SCRATCH/c.exit"
check "'Failed to bind to port N' is also an infrastructure error" yes \
    "$([[ -f "$SCRATCH/c.exit.infra" ]] && echo yes || echo no)"

# A stale marker must not survive into the next run of the same slot.
run_binary "$server" "$SCRATCH/b.out" "$SCRATCH/b.exit"
check "a clean rerun clears a stale infra marker" no \
    "$([[ -f "$SCRATCH/b.exit.infra" ]] && echo yes || echo no)"

# And a genuine termination change is still red, and still says so.
term=$(fake_bin term 'echo "bye"; exit 0')
run_binary "$term" "$SCRATCH/t.out" "$SCRATCH/t.exit"
out=$(compare_runs "x" \
    "$SCRATCH/a.out" "$SCRATCH/a.exit" "$SCRATCH/t.out" "$SCRATCH/t.exit")
check "a real termination change is still reported as one" yes \
    "$(contains "$out" "termination behaviour changed")"

# ---------------------------------------------------------------------------
# 4. The three server examples take the port from the environment.
#
#    Source-level: running them needs a compiler, which is the suite this test
#    stays out of.  What it pins is exactly the regression -- a fixed port
#    creeping back in.  The concurrent end-to-end proof lives in the #1535
#    commit and in every gate, which now runs them with a per-run port.
# ---------------------------------------------------------------------------
for ex in 74_async_tiers 75_tier2_uring 76_tier3_http; do
    src="$RITZ_ROOT/examples/$ex/src/main.ritz"
    check "$ex reads RITZ_EXAMPLE_PORT" yes \
        "$(grep -q 'RITZ_EXAMPLE_PORT' "$src" && echo yes || echo no)"
done

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
