#!/bin/bash
# Self-test for the known-failure allowlists and their strict-xpass rule —
# AGAST #1365.
#
# regression.sh keeps two allowlists of examples a compiler cannot build:
#
#     regression-known-failures.txt        (ritz0)
#     regression-known-failures-ritz1.txt  (ritz1 and ritz1_selfhosted, shared)
#
# An entry is a claim about the compiler. Claims go stale, and this repo has
# now had four allowlists rot silently (#1327, #1333, #1359, and this one).
# The two failure modes are:
#
#   (a) the entry names an example that no longer exists — dead weight that
#       reads as compiler debt forever;
#   (b) the compiler learns to build the example and the entry stays — the
#       suite keeps skipping a test that would now pass.
#
# (b) was already detected and then thrown away: the check existed but called
# warn(), so the run stayed green and nothing forced the delisting. That is
# how 74_async_tiers and 75_tier2_uring sat listed as "unmigrated against the
# current async framework" when they were really two `&x` -> `@x` address-of
# migrations, missed by the pass that did every other example on their ladder.
# report_xpass() makes it a hard failure.
#
# This file proves both floors can actually go red. A floor that has never
# been observed failing is indistinguishable from no floor at all.
#
# Hermetic: sources regression.sh as a library, compiles nothing, runs in well
# under a second. The one non-hermetic assertion (entries name real examples)
# reads the real allowlists deliberately — that IS the thing being checked.
#
# Exit codes: 0 all assertions held, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export RITZ_REGRESSION_LIB_ONLY=1
# shellcheck source=/dev/null
source "$SCRIPT_DIR/regression.sh"

# regression.sh installs an EXIT trap that deletes the real .regression build
# dir. Drop it: a self test must not be able to disturb a real run.
trap - EXIT
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

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

echo "regression.sh allowlist / strict-xpass self-test"
echo "==============================================="

# ---------------------------------------------------------------------------
# known_failures_file: ritz1 and ritz1_selfhosted MUST share one file.
#
# Not cosmetic. The shared file is what makes it impossible to hide a
# ritz1 vs ritz1_selfhosted divergence by listing the example under only one
# of them — see the header of regression-known-failures-ritz1.txt.
# ---------------------------------------------------------------------------
f_ritz0=$(known_failures_file ritz0)
f_ritz1=$(known_failures_file ritz1)
f_self=$(known_failures_file ritz1_selfhosted)

check "ritz0 uses the ritz0 allowlist" \
    "regression-known-failures.txt" "$(basename "$f_ritz0")"
check "ritz1 uses the ritz1 allowlist" \
    "regression-known-failures-ritz1.txt" "$(basename "$f_ritz1")"
check "ritz1_selfhosted SHARES ritz1's allowlist" "$f_ritz1" "$f_self"

# ---------------------------------------------------------------------------
# is_known_failure: exact whole-line match, comments and blanks stripped.
# ---------------------------------------------------------------------------
LIST="$SCRATCH/list.txt"
cat > "$LIST" <<'EOF'
# a comment
tier1_basics_01_hello

tier5_async_47_lisp
#tier9_commented_out
partial_name_prefix
EOF

# Point the helper at our synthetic list by shadowing known_failures_file.
known_failures_file() { echo "$LIST"; }

is_known_failure ritz0 "tier1_basics_01_hello"
check "a listed entry is a known failure" 0 $?

is_known_failure ritz0 "tier9_never_listed"
check "an unlisted entry is not a known failure" 1 $?

is_known_failure ritz0 "tier9_commented_out"
check "a commented-out entry is NOT honoured" 1 $?

is_known_failure ritz0 "tier5_async_47_lisp"
check "trailing whitespace on an entry is tolerated" 0 $?

# grep -qxF, not -qF: a substring must not match. Without -x, "partial_name"
# would match the line "partial_name_prefix" and silently excuse an example
# nobody listed.
is_known_failure ritz0 "partial_name"
check "a strict PREFIX of an entry does not match" 1 $?

is_known_failure ritz0 ""
check "the empty key does not match a blank line" 1 $?

# ---------------------------------------------------------------------------
# report_xpass: names the compiler, the example, and the file to edit.
#
# The message is the entire remedy — the operator has to know which of two
# files to open. A message that says only "remove it" sends them looking.
# ---------------------------------------------------------------------------
out=$(report_xpass ritz0 "tier1_basics_01_hello" 2>&1)

case "$out" in
    *tier1_basics_01_hello*) got_name=yes ;;
    *)                       got_name=no ;;
esac
check "xpass message names the example" yes "$got_name"

case "$out" in
    *COMPILES*) got_why=yes ;;
    *)          got_why=no ;;
esac
check "xpass message says the example COMPILES" yes "$got_why"

case "$out" in
    *list.txt*) got_file=yes ;;
    *)          got_file=no ;;
esac
check "xpass message names the file to edit" yes "$got_file"

# Restore the real resolver before the on-disk assertions below.
unset -f known_failures_file
known_failures_file() {
    case "$1" in
        ritz1|ritz1_selfhosted) echo "$SCRIPT_DIR/regression-known-failures-ritz1.txt" ;;
        *)                      echo "$SCRIPT_DIR/regression-known-failures.txt" ;;
    esac
}

# ---------------------------------------------------------------------------
# Floor (a): every entry in the REAL allowlists names an example that exists.
#
# An example key is its path under examples/ with '/' flattened to '_', which
# is ambiguous to invert (tier5_async_47_lisp could be tier5/async_47_lisp).
# So resolve the same way the harness does: enumerate real directories, derive
# each one's key, and require every listed key to be in that set.
# ---------------------------------------------------------------------------
real_keys=$(cd "$RITZ_ROOT/examples" 2>/dev/null && \
    { ls -d -- */ tier*/*/ 2>/dev/null || true; } | \
    sed 's|/$||' | tr '/' '_' | sort -u)

entries_of() {
    sed 's/#.*//; s/[[:space:]]*$//; /^$/d' "$1"
}

for f in "$(known_failures_file ritz0)" "$(known_failures_file ritz1)"; do
    missing=""
    while IFS= read -r key; do
        [[ -n "$key" ]] || continue
        grep -qxF "$key" <<< "$real_keys" || missing="$missing $key"
    done < <(entries_of "$f")
    check "every entry in $(basename "$f") names an example that exists" \
        "" "$missing"
done

# ---------------------------------------------------------------------------
# Floor (b): the xpass check is WIRED AS A FAILURE at all three call sites.
#
# This is a source-level assertion rather than a behavioural one, and that is
# a deliberate trade-off: exercising the real call sites means compiling the
# corpus with three compilers, which is the ~20-minute suite this self-test
# exists to stay out of. What it pins is precisely the regression that
# happened — the check being present but advisory. If someone downgrades
# report_xpass back to warn(), or adds a fourth stage that only warns, this
# goes red in under a second.
# ---------------------------------------------------------------------------
rs="$SCRIPT_DIR/regression.sh"

check "all three stages call report_xpass" 3 \
    "$(grep -cE '^\s*report_xpass ' "$rs")"

check "no stage still only warns about an allowlisted example that compiles" 0 \
    "$(grep -cE 'warn .*(but COMPILES|allowlist but)' "$rs")"

# Each report_xpass must be followed by a failed++ — printing a failure while
# leaving the counter alone is the same non-gate in a different costume.
check "every report_xpass increments the failure counter" 3 \
    "$(grep -A 1 -E '^\s*report_xpass ' "$rs" | grep -cE 'failed=\$\(\(failed \+ 1\)\)')"

echo
echo "-----------------------------------------------"
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "✓ $TESTS_RUN assertions passed"
    exit 0
fi
echo "✗ $TESTS_FAILED of $TESTS_RUN assertions failed"
exit 1
