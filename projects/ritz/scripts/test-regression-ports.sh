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
#   1. Isolation.  regression.sh picks a free block of ports per run.  Since
#      examples run in parallel (AGAST #1806) each server example gets its
#      own, base + its corpus index -- the same in every stage -- as
#      RITZ_EXAMPLE_PORT in the fixed `env -i` environment.  Only examples
#      that read RITZ_EXAMPLE_PORT get one, so 31_env/33_printenv print the
#      same bytes in every stage AND every run (Stage 1's results are cached).
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
p2=$(pick_example_port 64)
check "pick_example_port N returns a block that fits below 32768" yes \
    "$([[ "$p2" =~ ^[0-9]+$ && $p2 -ge 20000 && $((p2 + 64)) -le 32768 ]] && echo yes || echo no)"

# A value handed in by the caller wins, so a human can reproduce a run.
over=$(RITZ_EXAMPLE_PORT=23456 RITZ_REGRESSION_LIB_ONLY=1 bash -c \
    "source '$SCRIPT_DIR/regression.sh'; trap - EXIT; echo \$REGRESSION_EXAMPLE_PORT")
check "RITZ_EXAMPLE_PORT from the caller overrides the pick" 23456 "$over"

# ---------------------------------------------------------------------------
# 2. run_binary hands a server its port, and nobody else one.
# ---------------------------------------------------------------------------
b=$(fake_bin echo_port 'echo "port=${RITZ_EXAMPLE_PORT-unset}"')
RUN_PORT=$((REGRESSION_EXAMPLE_PORT + 7)) run_binary "$b" "$SCRATCH/p.out" "$SCRATCH/p.exit"
check "the program sees its RITZ_EXAMPLE_PORT under env -i" \
    "port=$((REGRESSION_EXAMPLE_PORT + 7))" "$(cat "$SCRATCH/p.out")"
run_binary "$b" "$SCRATCH/p.out" "$SCRATCH/p.exit"
check "a program given no port has no RITZ_EXAMPLE_PORT at all" \
    "port=unset" "$(cat "$SCRATCH/p.out")"

mkdir -p "$SCRATCH/ex_srv/src" "$SCRATCH/ex_plain/src"
echo 'let p = getenv(c"RITZ_EXAMPLE_PORT")' > "$SCRATCH/ex_srv/src/main.ritz"
echo 'fn main() -> i32' > "$SCRATCH/ex_plain/src/main.ritz"
check "example_port gives a server base + its index" \
    "$((REGRESSION_EXAMPLE_PORT + 3))" "$(example_port "$SCRATCH/ex_srv" 3)"
check "example_port gives any other example nothing" \
    "" "$(example_port "$SCRATCH/ex_plain" 3)"

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
# 4. Every server example takes its port from the environment (or from the
#    kernel), including the ones outside the corpus.
#
#    Source-level: running them needs a compiler, which is the suite this test
#    stays out of.  What it pins is exactly the regression -- a fixed port
#    creeping back in.  The concurrent end-to-end proof lives in the #1535
#    commit and in every gate, which now runs them with a per-run port.
# ---------------------------------------------------------------------------
# The literal-port detector, shared with section 5.  A literal port
# (1024-65535) assigned to a `port`, passed straight to a bind, or handed to
# htons() (the raw sockaddr_in form) is a port the program cannot be moved off.
LITERAL_PORT_RE='\bport\b[^=(]*= *[1-9][0-9]{3,4}\b|bind\(.*, *[1-9][0-9]{3,4} *\)|htons\( *[1-9][0-9]{3,4} *\)'
# Prints the literal-port lines under the paths given, or nothing.
fixed_ports_in() {
    grep -rsnE --include='*.ritz' --exclude-dir=build "$LITERAL_PORT_RE" "$@"
}
# Args: $1=example dir
fixed_listen_ports() { fixed_ports_in "$1"/src; }
unmovable_port() {
    [[ -n "$(fixed_listen_ports "$1")" ]] &&
        ! grep -rqs --include='*.ritz' --exclude-dir=build 'RITZ_EXAMPLE_PORT' "$1"/src
}
# A single loose .ritz file (not a package) with a literal port it cannot be
# moved off.  Args: $1=file
unmovable_port_file() {
    [[ -n "$(fixed_ports_in "$1")" ]] && ! grep -q 'RITZ_EXAMPLE_PORT' "$1"
}
# A shell script that pins PORT=<literal> without deferring to
# RITZ_EXAMPLE_PORT.  Args: $1=script
unmovable_port_script() {
    grep -qE '^[[:space:]]*(export[[:space:]]+)?PORT=[1-9][0-9]{3,4}\b' "$1" &&
        ! grep -q 'RITZ_EXAMPLE_PORT' "$1"
}

# The servers that take a port: each reads RITZ_EXAMPLE_PORT.
for ex in 74_async_tiers 75_tier2_uring 76_tier3_http tier5_async/50_http; do
    src="$RITZ_ROOT/examples/$ex/src/main.ritz"
    check "$ex reads RITZ_EXAMPLE_PORT" yes \
        "$(grep -q 'RITZ_EXAMPLE_PORT' "$src" && echo yes || echo no)"
done

# The client/server self-tests (AGAST #1542, fixed by #3136): they need no
# outside port at all, so they bind port 0 and ask the kernel which one they
# got.  No literal port, and their test.sh (run with the ambient env, not
# env -i) passes none either.
for ex in tier5_async/59_async_net tier5_async/60_echo_server; do
    check "$ex binds no literal port" "" \
        "$(fixed_listen_ports "$RITZ_ROOT/examples/$ex")"
    check "$ex asks the kernel for its port" yes \
        "$(grep -q 'tcp_getsockname' "$RITZ_ROOT/examples/$ex/src/main.ritz" && echo yes || echo no)"
    check "$ex/test.sh pins no port" no \
        "$(grep -qE 'PORT|[^0-9][1-9][0-9]{3,4}([^0-9]|$)' "$RITZ_ROOT/examples/$ex/test.sh" && echo yes || echo no)"
done

# The detectors, on fixtures, so a broken regex cannot pass vacuously.
mkdir -p "$SCRATCH/fx_loose"
printf 'fn main() -> i32\n    addr.sin_port = htons(9000)\n' > "$SCRATCH/fx_loose/raw.ritz"
printf '# RITZ_EXAMPLE_PORT\nfn main() -> i32\n    addr.sin_port = htons(9000)\n' > "$SCRATCH/fx_loose/raw_env.ritz"
printf 'fn main() -> i32\n    addr.sin_port = htons(port)\n' > "$SCRATCH/fx_loose/raw_var.ritz"
printf 'fn main() -> i32\n    tcp_bind(fd, inaddr_any(), 9000)\n' > "$SCRATCH/fx_loose/nested.ritz"
printf '#!/bin/bash\nPORT=9001\nnc localhost $PORT\n' > "$SCRATCH/fx_loose/fixed.sh"
printf '#!/bin/bash\nPORT=${RITZ_EXAMPLE_PORT:-9001}\n' > "$SCRATCH/fx_loose/env.sh"
check "a literal htons() port in a loose file is unmovable" yes \
    "$(unmovable_port_file "$SCRATCH/fx_loose/raw.ritz" && echo yes || echo no)"
check "a literal htons() default behind RITZ_EXAMPLE_PORT is fine" no \
    "$(unmovable_port_file "$SCRATCH/fx_loose/raw_env.ritz" && echo yes || echo no)"
check "a literal bind port after a nested call is unmovable" yes \
    "$(unmovable_port_file "$SCRATCH/fx_loose/nested.ritz" && echo yes || echo no)"
check "htons() of a variable is fine" no \
    "$(unmovable_port_file "$SCRATCH/fx_loose/raw_var.ritz" && echo yes || echo no)"
check "a script pinning PORT=N is unmovable" yes \
    "$(unmovable_port_script "$SCRATCH/fx_loose/fixed.sh" && echo yes || echo no)"
check "a script defaulting PORT from RITZ_EXAMPLE_PORT is fine" no \
    "$(unmovable_port_script "$SCRATCH/fx_loose/env.sh" && echo yes || echo no)"

# Outside the corpus regression.sh runs: loose .ritz servers (not packages, so
# section 5 never sees them, e.g. tier5_async/async_echo_server.ritz) and the
# hand-run integration scripts (74_async_tiers/test_tier1_integration.sh).
# Run by hand next to a gate, a fixed port collides just the same.
loose_unmovable=()
while read -r f; do
    unmovable_port_file "$f" && loose_unmovable+=("${f#"$RITZ_ROOT"/}")
done < <(find "$RITZ_ROOT/examples" -type f -name '*.ritz' \
            -not -path '*/build/*' -not -path '*/src/*' -not -path '*/test/*' | sort)
check "no loose example .ritz binds a fixed port without RITZ_EXAMPLE_PORT" "" \
    "${loose_unmovable[*]}"
script_unmovable=()
while read -r f; do
    unmovable_port_script "$f" && script_unmovable+=("${f#"$RITZ_ROOT"/}")
done < <(find "$RITZ_ROOT/examples" -type f -name '*.sh' -not -path '*/build/*' | sort)
check "no example script pins a fixed PORT without RITZ_EXAMPLE_PORT" "" \
    "${script_unmovable[*]}"

# ---------------------------------------------------------------------------
# 5. No example in the corpus binds a hard-coded port it cannot be moved off.
#
#    The list in 4 rotted once already: tier5_async_50_http bound a fixed 8080
#    and was never on it, so a host where anything else held 8080 failed the
#    gate as an infrastructure error (AGAST #3136).  59_async_net and
#    60_echo_server bound fixed 9876-9880 for their client/server self-tests and
#    hung until the timeout when those were taken.  So this is a rule over the
#    whole corpus, not a list: a literal port (1024-65535) assigned to a
#    `port` or passed straight to a bind is allowed only in an example that
#    reads RITZ_EXAMPLE_PORT (keeping it as the default when unset).  A
#    self-test that needs a port of its own binds port 0 and asks the kernel
#    which one it got (tcp_getsockname).
# ---------------------------------------------------------------------------
# (fixed_listen_ports / unmovable_port are defined above section 4.)

# The detector itself, on fixtures, so a broken regex cannot pass vacuously.
mkdir -p "$SCRATCH/fx_fixed/src" "$SCRATCH/fx_env/src" "$SCRATCH/fx_zero/src"
printf 'fn main() -> i32\n    var port: i32 = 8080\n' > "$SCRATCH/fx_fixed/src/main.ritz"
printf 'fn main() -> i32\n    let x: i32 = tcp_bind(fd, lh, 9876)\n' >> "$SCRATCH/fx_fixed/src/main.ritz"
printf '# RITZ_EXAMPLE_PORT\nfn main() -> i32\n    var port: i32 = 8080\n' > "$SCRATCH/fx_env/src/main.ritz"
printf 'fn main() -> i32\n    let port: i32 = 0\n    tcp_bind(fd, lh, port)\n' > "$SCRATCH/fx_zero/src/main.ritz"
check "the detector finds a literal port and a literal bind" 2 \
    "$(fixed_listen_ports "$SCRATCH/fx_fixed" | wc -l)"
check "a literal port with no RITZ_EXAMPLE_PORT is unmovable" yes \
    "$(unmovable_port "$SCRATCH/fx_fixed" && echo yes || echo no)"
check "a literal default behind RITZ_EXAMPLE_PORT is fine" no \
    "$(unmovable_port "$SCRATCH/fx_env" && echo yes || echo no)"
check "binding port 0 is fine" no \
    "$(unmovable_port "$SCRATCH/fx_zero" && echo yes || echo no)"

# The corpus regression.sh actually runs.
unmovable=()
while read -r ex; do
    unmovable_port "$ex" && unmovable+=("$(example_key "$ex")")
done < <(get_examples)
check "no corpus example binds a fixed port without RITZ_EXAMPLE_PORT" "" \
    "${unmovable[*]}"

echo ""
echo "$TESTS_RUN checks, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
