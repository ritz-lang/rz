#!/bin/bash
# Self-test for run_binary's environment normalisation — AGAST #1376.
#
# The differential stages byte-compare an example's stdout across ritz0, ritz1
# and ritz1_selfhosted. Two corpus examples — 31_env and 33_printenv — print
# `environ` verbatim, so their output is a function of the ambient environment
# rather than of the compiled program.
#
# The harness perturbs that environment itself: stage 2 does
# `cd "$ritz1_dir"` and then `cd "$ROOT_DIR"` to build ritz1, which changes
# OLDPWD. Stage 1 captured
#     OLDPWD=/home/aaron/dev/ritz-lang/rz
# and stage 3 ran with
#     OLDPWD=/home/aaron/dev/ritz-lang/rz/projects/ritz
# giving "output mismatch" on line 50 for a compiler behaving perfectly.
#
# What makes it worth a self-test rather than a one-line fix is that the suite's
# verdict depended on the directory you invoked it from: run from projects/ritz
# it was green, run from the repo root it was red, same commit, same compiler.
# A gate whose answer depends on your shell's history is not a gate.
#
# run_binary now execs the program under `env -i` with a fixed allowlist. This
# file proves that normalisation actually holds, because a normalisation that
# has never been observed working is indistinguishable from none.
#
# Hermetic: no compiler, no corpus, runs in well under a second.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

# regression.sh installs an EXIT trap that deletes the real .regression build
# dir. Drop it: a self test must not disturb, or read, a real run.
trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT
BUILD_DIR="$SCRATCH/build"
mkdir -p "$BUILD_DIR"

PASS=0
FAIL=0

check() {
    local what="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        echo "  ✗ $what"
        echo "      expected: $expected"
        echo "      actual:   $actual"
    fi
}

# A stand-in for a compiled example that prints its environment, exactly as
# 31_env and 33_printenv do. run_binary only requires an executable file.
PRINTENV_BIN="$SCRATCH/print_env"
cat > "$PRINTENV_BIN" <<'EOF'
#!/bin/sh
env | sort
EOF
chmod +x "$PRINTENV_BIN"

run_capture() {
    # $1 = tag, remaining args = VAR=VALUE pairs to pollute the ambient env
    local tag="$1"; shift
    local out="$SCRATCH/$tag.out" ec="$SCRATCH/$tag.exit"
    ( for kv in "$@"; do export "${kv?}"; done
      run_binary "$PRINTENV_BIN" "$out" "$ec" )
    cat "$out"
}

run_capture_from() {
    # $1 = tag, $2 = directory to invoke run_binary from.
    #
    # Setting OLDPWD directly would prove nothing: run_binary does
    # `cd "$sandbox"`, and `cd` overwrites OLDPWD with the caller's cwd. The
    # caller's cwd IS the variable — that is precisely why the real bug
    # depended on which directory you typed the command from.
    local tag="$1" from="$2"
    local out="$SCRATCH/$tag.out" ec="$SCRATCH/$tag.exit"
    ( cd "$from" && run_binary "$PRINTENV_BIN" "$out" "$ec" )
    cat "$out"
}

echo "run_binary environment normalisation (AGAST #1376)"

# --- 1. The actual regression: the caller's cwd must not change the output ---
mkdir -p "$SCRATCH/caller_one" "$SCRATCH/caller/two/three"
A=$(run_capture_from a "$SCRATCH/caller_one")
B=$(run_capture_from b "$SCRATCH/caller/two/three")
check "caller's cwd does not change the program's output" "same" \
      "$([[ "$A" == "$B" ]] && echo same || echo different)"

# --- 2. Generalise: arbitrary ambient variables must not leak through ---
C=$(run_capture c RITZ_SELFTEST_LEAK=hello ANOTHER_LEAK=world)
check "ambient RITZ_SELFTEST_LEAK does not reach the program" "absent" \
      "$(echo "$C" | grep -q RITZ_SELFTEST_LEAK && echo present || echo absent)"
check "polluted run still matches the clean run" "same" \
      "$([[ "$A" == "$C" ]] && echo same || echo different)"

# --- 3. The allowlist is actually delivered, not merely emptied ---
# `env -i` with nothing at all would also make the output stable, and would
# break every example that needs a PATH. Assert the intended set arrives.
for var in PATH HOME LANG LC_ALL TZ SHELL TERM; do
    check "$var is present in the normalised environment" "present" \
          "$(echo "$A" | grep -q "^${var}=" && echo present || echo absent)"
done
check "LANG is pinned to C" "LANG=C" "$(echo "$A" | grep '^LANG=')"
check "TZ is pinned to UTC" "TZ=UTC" "$(echo "$A" | grep '^TZ=')"

# --- 4. The capture is real, not an empty file comparing equal to another ---
# Two things that never ran compare equal; that is the failure mode run_binary's
# own missing-binary guard exists to prevent, and it applies here too.
check "captured output is non-empty" "nonempty" \
      "$([[ -n "$A" ]] && echo nonempty || echo EMPTY)"
check "exit code was recorded as 0" "0" "$(cat "$SCRATCH/a.exit")"

# --- 5. A missing binary must still be refused, not normalised into a pass ---
run_binary "$SCRATCH/does_not_exist" "$SCRATCH/z.out" "$SCRATCH/z.exit"
check "absent binary is rejected" "1" "$?"

echo
if (( FAIL > 0 )); then
    echo "✗ $FAIL assertion(s) failed, $PASS passed"
    exit 1
fi
echo "✓ $PASS assertions passed"
exit 0
