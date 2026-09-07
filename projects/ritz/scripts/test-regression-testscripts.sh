#!/bin/bash
# Self-test for regression.sh's test.sh correctness gate — AGAST #1359.
#
# An example's test.sh is the only thing in the whole regression suite that
# asserts a program produces the *right* answer.  Every other stage compares
# ritz0 against ritz1 against ritz1_selfhosted, and three compilers agreeing on
# the same wrong output passes that comparison.
#
# The gate used to be keyed on a hardcoded list of example names:
#
#     INTERACTIVE_EXAMPLES="05_cat 06_grep 07_wc 08_echo 09_head 10_tail"
#
# Four of those six names had stopped existing when the corpus was renumbered.
# So of the 68 examples shipping a test.sh, exactly 2 ever had it executed, and
# the suite reported green the whole time.  That is the third allowlist in this
# repo to rot silently (see also #1327, #1333).
#
# Being freshly correct is therefore not good enough — the replacement has to
# be *unable* to rot.  It keys off the filesystem, and
# assert_test_scripts_all_ran() fails the suite if an example ships assertions
# that were never executed.  This file proves that floor can actually go red,
# because a floor that has never been observed failing is indistinguishable
# from no floor at all.
#
# Hermetic: builds a synthetic examples/ tree in a temp dir, compiles nothing,
# runs in well under a second.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

# regression.sh installs an EXIT trap that deletes the real .regression build
# dir and points BUILD_DIR/EXAMPLES_DIR at the real tree.  Drop both: a self
# test must not be able to disturb, or read, a real run.
trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT
BUILD_DIR="$SCRATCH/build"
EXAMPLES_DIR="$SCRATCH/examples"
mkdir -p "$BUILD_DIR" "$EXAMPLES_DIR"
TEST_SCRIPTS_RAN_FILE="$BUILD_DIR/test_scripts_ran.txt"

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

# Build a synthetic example.
# Args: $1=relative dir, $2=ritz.toml body, $3=test.sh body ("" = no test.sh),
#       $4(optional)="no-exec" to leave test.sh mode 644
make_example() {
    local dir="$EXAMPLES_DIR/$1"
    mkdir -p "$dir/src"
    echo 'fn main() -> i32' > "$dir/src/main.ritz"
    printf '%s\n' "$2" > "$dir/ritz.toml"
    if [[ -n "$3" ]]; then
        printf '%s\n' "$3" > "$dir/test.sh"
        if [[ "${4:-}" == "no-exec" ]]; then
            chmod 644 "$dir/test.sh"
        else
            chmod 755 "$dir/test.sh"
        fi
    fi
    echo "$dir"
}

# A stand-in for a compiled example binary: exits with the code it is given.
make_binary() {
    local path="$SCRATCH/$1"
    printf '#!/bin/bash\nexit %s\n' "$2" > "$path"
    chmod 755 "$path"
    echo "$path"
}

echo "regression.sh test.sh-gate self-test"
echo "===================================="

# ---------------------------------------------------------------------------
# has_test_script: presence, not membership of a list
# ---------------------------------------------------------------------------

d_with=$(make_example "tier1/01_with" $'[package]\nname = "with"' 'exit 0')
d_without=$(make_example "tier1/02_without" $'[package]\nname = "without"' '')

has_test_script "$d_with"; check "has_test_script true when test.sh exists" 0 $?
has_test_script "$d_without"; check "has_test_script false when it does not" 1 $?

# The regression this whole change exists to prevent: a name-keyed gate.  None
# of these synthetic dirs are in any hardcoded list, and they must still be
# recognised.  If someone reintroduces a list, this assertion is what catches it.
d_odd=$(make_example "tier9/99_never_listed_anywhere" $'[package]\nname = "odd"' 'exit 0')
has_test_script "$d_odd"; check "an example in no allowlist is still gated" 0 $?

# ---------------------------------------------------------------------------
# resolve_bin_name: [[bin]] wins, [package] is the common fallback
# ---------------------------------------------------------------------------

d_bin=$(make_example "tier1/03_bin" \
    $'[package]\nname = "pkgname"\n\n[[bin]]\nname = "binname"\npath = "src/main.ritz"' 'exit 0')
check "resolve_bin_name prefers [[bin]] name" "binname" "$(resolve_bin_name "$d_bin")"

# 50 of 81 real examples have no [[bin]] section at all, so this branch is the
# common case, not the exception.  The old code fell back to basename($dir),
# which for `02_exitcode` yields `02_exitcode` where the package is `exitcode`:
# the symlink was created under a name test.sh never looks for, the test ran
# against a missing binary, and the result was empty output.  Usually that
# scored as a spurious failure; for any test expecting empty output it scored
# as a false pass.
check "resolve_bin_name falls back to [package] name" "with" "$(resolve_bin_name "$d_with")"
check "resolve_bin_name is empty when ritz.toml names nothing" "" "$(resolve_bin_name "$SCRATCH/nonexistent")"

# ---------------------------------------------------------------------------
# run_test_script: pass, fail, and the two sentinels
# ---------------------------------------------------------------------------

bin_ok=$(make_binary "ok.bin" 0)

d_pass=$(make_example "tier1/04_pass" $'[package]\nname = "p4"' \
    'test -x ./p4 || exit 1
./p4 || exit 1
exit 0')
run_test_script "$d_pass" "$bin_ok"
check "passing test.sh returns 0 (and found the binary by package name)" 0 $?

d_fail=$(make_example "tier1/05_fail" $'[package]\nname = "p5"' 'exit 1')
run_test_script "$d_fail" "$bin_ok"
check "failing test.sh propagates its failure" 1 $?

# Sentinels are 200/201, not 2/3.  A test.sh is free to `exit 2`, and callers
# distinguish "no test script" from "test failed" by return value; overlapping
# the ranges would let a genuinely failing test be reported as an absent one.
d_exit2=$(make_example "tier1/06_exit2" $'[package]\nname = "p6"' 'exit 2')
run_test_script "$d_exit2" "$bin_ok"
check "a test.sh exiting 2 is a failure, not 'no test script'" 2 $?

run_test_script "$d_without" "$bin_ok"
check "absent test.sh returns the 200 sentinel" 200 $?

d_noname=$(make_example "tier1/07_noname" $'[build]\nnothing = true' 'exit 0')
run_test_script "$d_noname" "$bin_ok"
check "unresolvable binary name returns the 201 sentinel" 201 $?

# A lost +x bit must not be silently equivalent to "this example has no tests".
# Four real test.sh files (52_uring, 53_async, 54_async_fs,
# 55_async_state_machine) are committed mode 100644; under the old `[[ ! -x ]]`
# guard they returned "no test script" and were counted as skips.
d_noexec=$(make_example "tier1/08_noexec" $'[package]\nname = "p8"' 'exit 1' no-exec)
run_test_script "$d_noexec" "$bin_ok"
check "a non-executable test.sh still runs (and can still fail)" 1 $?

# ---------------------------------------------------------------------------
# check_test_script: the caller-facing verdict, and the ledger
# ---------------------------------------------------------------------------

: > "$TEST_SCRIPTS_RAN_FILE"

check_test_script "$d_pass" "tier1_04_pass" "$bin_ok" >/dev/null
check "check_test_script: pass -> 0" 0 $?

check_test_script "$d_fail" "tier1_05_fail" "$bin_ok" >/dev/null
check "check_test_script: fail -> 1" 1 $?

check_test_script "$d_without" "tier1_02_without" "$bin_ok" >/dev/null
check "check_test_script: no test.sh -> 0 (nothing to assert)" 0 $?

# Present-but-unrunnable must be a FAILURE, never a pass.  An example whose
# assertions cannot be executed is the exact shape of the defect this change
# exists to stop reporting as green.
check_test_script "$d_noname" "tier1_07_noname" "$bin_ok" >/dev/null
check "check_test_script: present but unrunnable -> 1" 1 $?

check "ledger records the examples whose test.sh ran" \
    $'tier1_04_pass\ntier1_05_fail' "$(sort "$TEST_SCRIPTS_RAN_FILE")"

# An example with no test.sh must not enter the ledger — otherwise the floor
# below would count it as covered and the coverage number would be a lie.
grep -qxF "tier1_02_without" "$TEST_SCRIPTS_RAN_FILE"
check "an example with no test.sh is not counted as covered" 1 $?

# ---------------------------------------------------------------------------
# assert_test_scripts_all_ran: the floor, proven red-capable
# ---------------------------------------------------------------------------

# Every example that ships a test.sh is in the ledger => green.
: > "$TEST_SCRIPTS_RAN_FILE"
while read -r ts; do example_key "${ts%/test.sh}"; done \
    < <(find "$EXAMPLES_DIR" -mindepth 2 -name test.sh) >> "$TEST_SCRIPTS_RAN_FILE"
assert_test_scripts_all_ran >/dev/null
check "floor is green when every test.sh ran" 0 $?

# Drop one => red.  This is the original defect in miniature: an example ships
# assertions, the suite never executes them, and before this floor existed the
# run still exited 0.
grep -vxF "tier1_04_pass" "$TEST_SCRIPTS_RAN_FILE" > "$SCRATCH/tmp" && mv "$SCRATCH/tmp" "$TEST_SCRIPTS_RAN_FILE"
assert_test_scripts_all_ran >/dev/null
check "floor goes RED when an example's test.sh never ran" 1 $?

# ...unless that example legitimately failed to compile, in which case there
# was no binary to test and the compile failure is already reported.
assert_test_scripts_all_ran "tier1_04_pass" >/dev/null
check "a compile-failed example is excused from the floor" 0 $?

# Excusing an UNRELATED example must not launder the missing one.  Otherwise a
# long excuse list would silently re-create the allowlist hole.
assert_test_scripts_all_ran "tier1_05_fail" >/dev/null
check "excusing a different example does not launder the gap" 1 $?

# The scenario that started all this: the ledger is nearly empty because the
# gate matched almost nothing.  2 of 68 executed exited 0 for seven months.
: > "$TEST_SCRIPTS_RAN_FILE"
echo "tier1_04_pass" >> "$TEST_SCRIPTS_RAN_FILE"
assert_test_scripts_all_ran >/dev/null
check "the original '2 of 68 ran' scenario goes red" 1 $?

# A new example dropped into the corpus with a test.sh nobody wired up is the
# rot case.  It must be red on arrival, with no list to update.
make_example "tier7/70_brand_new" $'[package]\nname = "brandnew"' 'exit 0' >/dev/null
: > "$TEST_SCRIPTS_RAN_FILE"
while read -r ts; do
    key=$(example_key "${ts%/test.sh}")
    [[ "$key" == "tier7_70_brand_new" ]] && continue
    echo "$key"
done < <(find "$EXAMPLES_DIR" -mindepth 2 -name test.sh) >> "$TEST_SCRIPTS_RAN_FILE"
assert_test_scripts_all_ran >/dev/null
check "a newly added example that was never run goes red without any list edit" 1 $?

echo "===================================="
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "All $TESTS_RUN test.sh-gate assertions held."
    exit 0
fi
echo "$TESTS_FAILED of $TESTS_RUN test.sh-gate assertions FAILED."
exit 1
